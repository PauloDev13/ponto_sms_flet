from typing import Dict

import pandas as pd

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from utils.format_col_dataframe import columns_update


# FUNÇÃO QUE CRIA TODA A ESTRUTURA DO DATAFRAME QUE VAI GERAR O ARQUIVO EXCEL
def generate_dataframe(
        df_table: pd.DataFrame,
        data_by_year: Dict[int, pd.DataFrame],
        cpf: str,
        month_name: str,
        year: int,
        employee_name: str,
) -> None:
    try:
        # Atualiza o dataframe (df_table) substituindo o conteúdo das colunas
        # DATA SAÍDA, SAÍDA, TRABALHADA, HORA JUSTIFICADA e STATUS para uma string '---'
        # nas linhas onde a coluna DATA ENTRADA tem as palavra 'Férias'
        df_table.loc[
            df_table['ENTRADA'].str.contains('Férias'),
            ['DATA SAÍDA', 'SAÍDA', 'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS']
        ] = '---'

        # Filtrar as linhas onde 'DATA ENTRADA' é igual 'AFASTAMENTO'
        # df_filtered_removal = df_table[df_table['DATA ENTRADA'] == 'AFASTAMENTO']

        #  Remover duplicatas na coluna 'ENTRADA' dentro do subconjunto
        # df_filtered_removal = df_filtered_removal.drop_duplicates(subset='ENTRADA')

        # Filtrar as linhas onde 'DATA ENTRADA' não é 'AFASTAMENTO'
        # df_filtered_without_removal = df_table[df_table['DATA ENTRADA'] != 'AFASTAMENTO']

        # Combina o DataFrame sem duplicatas com o restante dos dados originais
        # df_table = pd.concat([df_filtered_without_removal, df_filtered_removal])

        # Reset o índice se necessário (opcional)
        # df_table = df_table.reset_index(drop=True)

        # Verifica quais colunas têm cabeçalho cujo nome não começam com "Unnamed".
        # Usa essa informação para selecionar e manter apenas essas colunas no DataFrame.
        # Colunas "Unnamed" aparecem quando o (Pandas) encontra
        # uma ou mais colunas sem nome de cabeçalho ou quando colunas extras geradas
        # por acidente durante o processo de leitura ou gravação dos dados
        df_table = df_table.loc[:, ~df_table.columns.str.contains('^Unnamed')]

        # Cria um dicionário com as colunas que serão criadas.
        # O conteúdo de todas é vazio e terão o mesmo número
        # de linhas do Dataframe
        new_columns = {
            'HT': [''] * df_table.shape[0],
            'HJ': [''] * df_table.shape[0],
            'ST': [''] * df_table.shape[0],
            'ADN': [''] * df_table.shape[0],
        }

        # Loop para criar as colunas no Dataframe
        for col_name, col_value in new_columns.items():
            df_table[col_name] = col_value

        # Após criadas, as colunas vão receber os valore 1 ou vazio ('').
        # É aplicado no Dataframe (df_table) a função (columns_update) que
        # retorna uma 'Series' com esses valores setados
        df_table[['HT', 'HJ', 'ST', 'ADN']] = df_table.apply(columns_update, axis=1)

        # Remove do dataframe (df_table) a coluna (EDITAR)
        del df_table['EDITAR']

        # Atribui a variável 'columns' o array com os nomes das colunas
        # do DataFrame (df_table)
        columns = df_table.columns

        # Finaliza a limpeza dos dados no Dataframe (df_table)
        # com os seguintes critérios:
        # 1 - São selecionadas as colunas TRABALHADA e HORA JUSTIFICADA que forem diferentes de '---'
        # 2 - ou as colunas STATUS igual 'APROVADO' e DATA ENTRADA igual a 'JUSTIFICATIVA'
        df_result = df_table[
            (df_table['TRABALHADA'] != '---')
            | (df_table['HORA JUSTIFICADA'] != '---')
            | (df_table['STATUS'] == 'APROVADO')
            | (df_table['DATA ENTRADA'] == 'JUSTIFICATIVA')
            ]

        # Array de string com as colunas do Dataframe(df_table) que serão verificadas
        columns_to_check = [
            'DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
            'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'HT', 'HJ', 'ST', 'ADN']

        # Verifica onde todas as colunas do dataframe estão vazias
        all_empty: bool = (
                df_result[columns_to_check].isna().all(axis=1)
                | (df_result[columns_to_check] == '').all(axis=1))

        # Cria uma nova linha com mensagem de alerta,
        # escrita na primeira célula da coluna para os
        # meses em que o servidor gozou férias.
        message_row = (
                [f'SERVIDOR EM GOZO DE FÉRIAS NO MÊS {month_name}/{year}'] +
                [''] * (len(df_result.columns) - 1))

        # cria linha vazia
        empty_row = [''] * len(columns)

        # Se a variável 'all_empty' retornar verdadeiro
        if all_empty.all():
            # cria Dataframe (df_with_message) com a mensagem de alerta
            # concatenando com o Dataframe (df_result)
            df_with_message = pd.concat([pd.DataFrame(
                [empty_row, message_row], columns=columns), df_result], ignore_index=True)
        else:
            # Se não, atribui ao Dataframe (df_with_message) o Dataframe (df_result) original.
            df_with_message = df_result

        # Se o ano não existir no dicionário 'data_by_year',
        # adiciona o ano e processa dos dados para cada ano
        if year not in data_by_year:
            # Define a mensagem inicial
            header_message_1 = f'PONTO DIGITAL - {employee_name} - CPF: {cpf} - {month_name}/{year}'

            # Atualiza o DataFrame (data_by_year[year]) inserindo
            # das linhas de identificação e cabeçalho
            data_by_year[year] = pd.DataFrame([
                [header_message_1] + [''] * (len(columns) - 1),  # Primeira linha com identificação
                list(columns),  # Segunda linha com o nome das colunas
            ], columns=columns)

            # Atribui à variável (df_totals_row) o retorno da função local (df_total_row)
            # que cria Dataframe com a linha onde será impresso 'TOTAIS'
            df_totals_row = df_total_row(columns)

            # Atualiza o Dataframe (data_by_year) mesclando com o Dataframe (df_with_message)
            data_by_year[year] = pd.concat([
                data_by_year[year],  # Dataframe vazio, com linhas de identificação e cabeçalho
                df_with_message,  # Dataframe com os dados dos meses
                df_totals_row  # Dataframe com a linha 'TOTAIS'
            ], ignore_index=True)
        else:
            # Define mensagem de identificação exibida
            # acima das colunas de cada mês
            header_message_2 = f'PONTO DIGITAL - {employee_name} - CPF: {cpf} - {month_name}/{year}'

            # Cria Dataframe(df_employee_row) para exibir informações de cada mês
            df_employee_row = pd.DataFrame([
                [header_message_2] + [''] * (len(columns) - 1),  # Linha com identificação
                list(columns),  # Linha com os nomes das colunas (cabeçalho)
            ], columns=columns)

            # Atribui à variável (df_totals_row) o retorno da função local (df_total_row)
            # que cria Dataframe com a linha onde será impresso 'TOTAIS'
            df_totals_row = df_total_row(columns)

            # Atualiza o Dataframe (data_by_year) mesclando os Dataframes
            # (df_employee_row, df_with_message e df_line_empty). Observar
            # que a sequência como os Dataframes são concatenados influência
            # na visualização das informações.
            data_by_year[year] = pd.concat([
                data_by_year[year],  # Dataframe vazio
                df_employee_row,  # Insere as linhas de identificação e as colunas do cabeçalho
                df_with_message,  # Insere as linhas com os dados propriamente ditos
                df_totals_row],  # Insere a linha de totais
                ignore_index=True
            )

    except Exception as e:
        AlertSnackbar.show('Ocorreu um erro inesperado. Tente novamente.')
        print('Erro inesperado', e)


# FUNÇÃO LOCAL QUE RETORNA UM DATAFRAME COM A LINHA DE TOTAIS
def df_total_row(columns: any) -> pd.DataFrame:
    # Linha com a string 'TOTAIS' na primeira célula e
    # vazia nas demais (array ['TOTAIS'], [''], [''], ['']...
    totals_row = ['TOTAIS'] + [''] * (len(columns) - 1)

    # Cria Dataframe com a linha onde será impresso 'TOTAIS'
    df_totals = pd.DataFrame([totals_row], columns=columns)

    return df_totals
