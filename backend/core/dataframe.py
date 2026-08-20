"""Construção dos DataFrames mensais/anuais do ponto digital.

Port da lógica de services/data/generate_df_service.py + utils/format_col_dataframe.py
+ utils/additional_night.py, sem nenhuma dependência de UI (Flet).

Convenções herdadas do desktop:
- Linhas com 'Férias' em ENTRADA → colunas de saída/horas viram '---'
- Colunas 'Unnamed:*' são removidas
- Linhas com 'MOTIVO:' em DATA ENTRADA são removidas
- Colunas HT/HJ/ST/ADN (1, '') calculadas por linha
- Coluna EDITAR é removida
- Cada ano ganha bloco: linha de identificação, cabeçalho das colunas,
  dados do(s) mês(es) e linha 'TOTAIS'
"""
from datetime import datetime, timedelta, time

import pandas as pd

# MESES_PT['JANEIRO'] = 1 ... usado no lugar de calendar com locale pt_BR
MESES_PT = {
    'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5,
    'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10,
    'NOVEMBRO': 11, 'DEZEMBRO': 12,
}

COLUNAS_BASE = [
    'DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
    'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'EDITAR',
    'HT', 'HJ', 'ST', 'ADN',
]


def format_validation_date(date: str) -> bool:
    """True se a string está no formato 'dd/MM/yyyy'."""
    if not isinstance(date, str):
        return False
    try:
        datetime.strptime(date, '%d/%m/%Y')
        return True
    except ValueError:
        return False


def str_to_date(date_str):  # noqa: ANN201 - retorno pode ser date | None
    """Converte 'dd/MM/yyyy' (com ou sem sufixo '- Dia da semana') para date.

    Aceita dia/mês sem zero à esquerda (ex.: '1/1/2023 - Domingo'),
    formato real usado pelo portal.
    """
    if not isinstance(date_str, str):
        return None
    date_str = date_str.split('-')[0].strip()
    try:
        day, month, year = (int(part) for part in date_str.split('/'))
        return datetime(year, month, day).date()
    except (ValueError, TypeError):
        return None


def format_validation(hour_str: str) -> bool:
    """True se a string está no formato 'HH:mm:ss'."""
    if not isinstance(hour_str, str):
        return False
    try:
        datetime.strptime(hour_str, '%H:%M:%S')
        return True
    except ValueError:
        return False


def str_to_time(hour_str: str):  # noqa: ANN201 - retorno pode ser time | None
    try:
        return datetime.strptime(hour_str, '%H:%M:%S').time()
    except ValueError:
        return None


def additional_night_calculation(start_dt, start_hs, end_dt, end_hs) -> bool | None:  # noqa: ANN001
    """True se o período trabalhado intercepta o intervalo de 22h às 05h.

    Exige os quatro valores (entrada e saída, data e hora); linhas com
    dados parciais (ex.: '---') retornam None sem calcular.
    """
    if not (start_dt and start_hs and end_dt and end_hs):
        return None
    entry_date = datetime.combine(start_dt, start_hs)
    exit_date = datetime.combine(end_dt, end_hs)

    # Se a saída é no dia seguinte e a hora de saída é menor que a de entrada,
    # ajustamos a data de saída
    if exit_date < entry_date:
        exit_date += timedelta(days=1)

    # Período noturno (das 22:00 às 05:00 do dia seguinte)
    start_night_work = entry_date.replace(hour=22, minute=0, second=0)
    end_night_work = exit_date.replace(hour=5, minute=0, second=0) + timedelta(days=1)

    return entry_date < end_night_work and exit_date > start_night_work


def columns_update(row: pd.Series) -> pd.Series:
    """Calcula HT/HJ/ST/ADN para uma linha do dataframe mensal."""
    hour_worked = str_to_time(row['TRABALHADA']) if format_validation(row['TRABALHADA']) else None
    hour_justified = str_to_time(row['HORA JUSTIFICADA']) if format_validation(row['HORA JUSTIFICADA']) else None

    ht_value = 1 if hour_worked and hour_worked >= str_to_time('12:00:00') else ''
    hj_value = 1 if hour_justified and hour_justified >= str_to_time('12:00:00') else ''

    tn_night_work_start = str_to_time(row['ENTRADA']) if format_validation(row['ENTRADA']) else None
    tn_night_work_end = str_to_time(row['SAÍDA']) if format_validation(row['SAÍDA']) else None

    start_date = str_to_date(row['DATA ENTRADA'])
    end_date = str_to_date(row['DATA SAÍDA'])

    tn_night_work = 1 if additional_night_calculation(
        start_dt=start_date, start_hs=tn_night_work_start,
        end_dt=end_date, end_hs=tn_night_work_end,
    ) else ''

    st_value = 1 if row['STATUS'] == 'APROVADO' else ''

    return pd.Series({'HT': ht_value, 'HJ': hj_value, 'ST': st_value, 'ADN': tn_night_work})


def df_total_row(columns) -> pd.DataFrame:  # noqa: ANN001
    """Dataframe com a linha onde será impresso 'TOTAIS'."""
    totals_row = ['TOTAIS'] + [''] * (len(columns) - 1)
    return pd.DataFrame([totals_row], columns=columns)


def generate_dataframe(
        df_table: pd.DataFrame,
        data_by_year: dict[int, pd.DataFrame],
        cpf: str,
        month_name: str,
        year: int,
        employee_name: str,
) -> None:
    """Transforma o dataframe do mês e o acumula em data_by_year[year]."""
    # Linhas de férias: preenche as colunas derivadas com '---'
    in_ferias = df_table['ENTRADA'].str.contains('Férias', na=False)
    if in_ferias.any():
        derivadas = [c for c in ['DATA SAÍDA', 'SAÍDA', 'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS']
                     if c in df_table.columns]
        if derivadas:
            df_table.loc[in_ferias, derivadas] = '---'

    # Remove colunas com cabeçalho 'Unnamed:*' (mesmo critério do desktop)
    df_table = df_table.loc[:, ~df_table.columns.str.contains('^Unnamed')]

    # Remove linhas com 'MOTIVO:' na coluna 'DATA ENTRADA'
    df_table = df_table[~df_table['DATA ENTRADA'].str.contains('MOTIVO:', na=False)]

    # Cria as colunas HT/HJ/ST/ADN
    new_columns = {
        'HT': [''] * df_table.shape[0],
        'HJ': [''] * df_table.shape[0],
        'ST': [''] * df_table.shape[0],
        'ADN': [''] * df_table.shape[0],
    }
    for col_name, col_value in new_columns.items():
        df_table[col_name] = col_value

    df_table[['HT', 'HJ', 'ST', 'ADN']] = df_table.apply(columns_update, axis=1)

    # Remove a coluna EDITAR
    if 'EDITAR' in df_table.columns:
        del df_table['EDITAR']

    columns = df_table.columns

    # Seleciona linhas relevantes (com horas, aprovadas ou justificativas)
    df_result = df_table[
        (df_table['TRABALHADA'] != '---')
        | (df_table['HORA JUSTIFICADA'] != '---')
        | (df_table['STATUS'] == 'APROVADO')
        | (df_table['DATA ENTRADA'] == 'JUSTIFICATIVA')
        ]

    columns_to_check = [
        'DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
        'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'HT', 'HJ', 'ST', 'ADN']

    all_empty: bool = (
        df_result[columns_to_check].isna().all(axis=1)
        | (df_result[columns_to_check] == '').all(axis=1))

    message_row = (
        [f'SERVIDOR EM GOZO DE FÉRIAS NO MÊS {month_name}/{year}'] +
        [''] * (len(df_result.columns) - 1))
    empty_row = [''] * len(columns)

    if all_empty.all():
        df_with_message = pd.concat([pd.DataFrame(
            [empty_row, message_row], columns=columns), df_result], ignore_index=True)
    else:
        df_with_message = df_result

    header_message = f'PONTO DIGITAL - {employee_name} - CPF: {cpf} - {month_name}/{year}'
    df_employee_row = pd.DataFrame([
        [header_message] + [''] * (len(columns) - 1),
        list(columns),
    ], columns=columns)
    df_totals_row = df_total_row(columns)

    if year not in data_by_year:
        data_by_year[year] = pd.concat([
            df_employee_row,
            df_with_message,
            df_totals_row
        ], ignore_index=True)
    else:
        data_by_year[year] = pd.concat([
            data_by_year[year],
            df_employee_row,
            df_with_message,
            df_totals_row
        ], ignore_index=True)


def empty_year_dataframe() -> dict[int, pd.DataFrame]:
    """Retorna um dicionário vazio de anos para acumular dataframes."""
    return {}