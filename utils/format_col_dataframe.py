from datetime import datetime

import pandas as pd

# Importações dos módulos locais
from utils.additional_night import additional_night_calculation


# Função para verificar se a string está no formato ('dd/MM/yyyy').
# Se estiver, retorna TRUE, se não, Retorna FALSE
def format_validation_date(date: str) -> bool:
    try:
        datetime.strptime(date, '%d/%m/%Y')
        return True
    except ValueError:
        return False


# Função para converter string para datetime.date NO FORMATO ('dd/MM/yyyy')
def str_to_date(date: str):
    try:
        return datetime.strptime(date, '%d/%m/%Y').date()
    except ValueError:
        return None


# Função para verificar se a string está no formato ('HH:mm:ss').
# Se estiver, retorna TRUE, se não, Retorna FALSE
def format_validation(hour_str: str) -> bool:
    try:
        datetime.strptime(hour_str, '%H:%M:%S')
        return True
    except ValueError:
        return False


# Função para converter string para datetime.time NO FORMATO ('HH:mm:ss')
def str_to_time(hour_str):
    try:
        return datetime.strptime(hour_str, '%H:%M:%S').time()
    except ValueError:
        return None


# Atualiza as colunas ('HT', 'HJ', 'ST') se nas colunas 'TRABALHADA' e
# 'HORA JUSTIFICADA' os valores forem iguais ou maiores que '12:00:00'.
# Na coluna 'STATUS' se o valor for igual a 'APROVADO'
def columns_update(row) -> pd.Series:
    try:
        # Se os dados da coluna 'TRABALHADA' estiver no formado '00:00:00',
        # faz a conversão para datetime.time. Se não, retorna None
        if format_validation(row['TRABALHADA']):
            hour_worked = str_to_time(row['TRABALHADA'])
        else:
            hour_worked = None

        # Se a HORA TRABALHADA não for None e for maior ou igual a '12:00:00',
        # retorna 1, se não, retorna uma string vazia ('')
        ht_value = 1 if hour_worked and hour_worked >= str_to_time('12:00:00') else ''

        # Se os dados da coluna 'HORA JUSTIFICADA' estiver no formado '00:00:00',
        # faz a conversão para datetime.time. Se não, retorna None
        if format_validation(row['HORA JUSTIFICADA']):
            hour_justified = str_to_time(row['HORA JUSTIFICADA'])
        else:
            hour_justified = None

        # Se a HORA JUSTIFICADA não for None e for maior ou igual a '12:00:00',
        # retorna 1, se não, retorna uma string vazia ('')
        hj_value = 1 if hour_justified and hour_justified >= str_to_time('12:00:00') else ''

        # Se os dados da coluna ('ENTRADA') estiver no formato time ('HH:mm:ss'),
        # retorna a hora de entrada formatada em time, se não, retorna None
        if format_validation(row['ENTRADA']):
            tn_night_work_start = str_to_time(row['ENTRADA'])
        else:
            tn_night_work_start = None

        # Se os dados da coluna ('SAÍDA') estiver no formato time ('HH:mm:ss'),
        # retorna a hora de saída formatada em time, se não, retorna None
        if format_validation(row['SAÍDA']):
            tn_night_work_end = str_to_time(row['SAÍDA'])
        else:
            tn_night_work_end = None

        # Se os (10) primeiros caracteres da coluna ('DATA ENTRADA') estiver no formadto
        #  (dd/MM/yyyy), retorna a data de entrada no formato (dd/MM/yyyy), se não, retorna None
        if format_validation_date(date=row['DATA ENTRADA'][:10]):
            start_date = str_to_date(date=row['DATA ENTRADA'][:10])
        else:
            start_date = None

        # Se os (10) primeiros caracteres da coluna ('DATA SAÍDA') estiver no formadto
        # (dd/MM/yyyy), retorna a data de entrada no formato (dd/MM/yyyy), se não, retorna None
        if format_validation_date(date=row['DATA SAÍDA'][:10]):
            end_date = str_to_date(date=row['DATA SAÍDA'][:10])
        else:
            end_date = None

        # se a função (additional_night_calculation) que verifica se o período
        # trabalhado contém o intervalo das 22 às 05 horas para efeito de cálculo
        # do adicional noturno retornar TRUE, insere o número (1) na ADN da planilha,
        # se não, insere uma string vazia ('')
        tn_night_work = 1 if additional_night_calculation(
            start_dt=start_date,
            end_dt=end_date,
            start_hs=tn_night_work_start,
            end_hs=tn_night_work_end,

        ) else ''

        # Se os dados na coluna 'STATUS' for igual à string 'APROVADO',
        # retorna 1, se não, retorna uma string vazia ('')
        st_value = 1 if row['STATUS'] == 'APROVADO' else ''

        # Monta a (Series) com as colunas e os valores que passaram na validação
        return pd.Series({
            'HT': ht_value,
            'HJ': hj_value,
            'ST': st_value,
            'ADN': tn_night_work
        })
    except Exception as e:
        print(f"Erro ao formatar colunas do dataframe: {e}")
