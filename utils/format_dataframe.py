import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
file_path = os.getenv('PATH_FILE_BASE')


# Função para verificar se a string está no formato correto ('00:00:00')
def format_validation(hour_str) -> bool:
    try:
        datetime.strptime(hour_str, '%H:%M:%S')
        return True
    except ValueError:
        return False


# Função para converter string para datetime.time
def str_to_time(hour_str):
    try:
        return datetime.strptime(hour_str, '%H:%M:%S').time()
    except ValueError:
        return None


# Atualiza as colunas 'HT', 'HJ', 'ST' se nas colunas 'TRABALHADA' e
# 'HORA JUSTIFICADA' os valores forem iguais ou maiores que '12:00:00'.
# Na coluna 'STATUS' se o valor for igual a 'APROVADO'
def columns_update(row):
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

        # Se os horários de entrada e saída forem diferentes de None e
        # o horário de entrada for maior ou igual a '18:00:00' e
        # o horário de saída for maior ou igual a '05:00:00', retorna 1,
        # se não, retorna string vazia ('')
        if format_validation(row['ENTRADA']):
            tn_night_work_start = str_to_time(row['ENTRADA'])
        else:
            tn_night_work_start = None

        if format_validation(row['SAÍDA']):
            tn_night_work_end = str_to_time(row['SAÍDA'])
        else:
            tn_night_work_end = None

        tn_night_work = 1 if (
                (tn_night_work_start and tn_night_work_end)
                and (tn_night_work_start >= str_to_time('18:00:00')
                     and tn_night_work_end >= str_to_time('05:00:00'))

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
        print(f"Erro: {e}")
