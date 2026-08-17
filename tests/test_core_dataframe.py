import datetime

import pandas as pd

from backend.core.dataframe import (
    MESES_PT,
    generate_dataframe,
    str_to_date,
)


def _build_month_table():
    base = pd.DataFrame([
        {'DATA ENTRADA': '05/01/2025', 'ENTRADA': '08:00:00', 'DATA SAIDA': '05/01/2025',
         'SAIDA': '17:00:00', 'TRABALHADA': '08:30:00', 'HORA JUSTIFICADA': '00:00:00',
         'STATUS': 'APROVADO', 'EDITAR': ''},
        {'DATA ENTRADA': 'JUSTIFICATIVA', 'ENTRADA': None, 'DATA SAIDA': '06/01/2025',
         'SAIDA': None, 'TRABALHADA': '---', 'HORA JUSTIFICADA': '14:30:00',
         'STATUS': 'APROVADO', 'EDITAR': ''},
        {'DATA ENTRADA': 'Férias', 'ENTRADA': 'Férias', 'DATA SAIDA': None,
         'SAIDA': None, 'TRABALHADA': None, 'HORA JUSTIFICADA': None,
         'STATUS': None, 'EDITAR': ''},
    ])
    base.columns = ['DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
                    'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'EDITAR'] if False else \
        ['DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
         'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'EDITAR']
    return base


def test_meses_pt_has_twelve_months():
    assert len(MESES_PT) == 12
    assert MESES_PT['JANEIRO'] == 1
    assert MESES_PT['DEZEMBRO'] == 12


def test_generate_dataframe_accumulates_years():
    data_by_year = {}
    df = _build_month_table()
    generate_dataframe(df, data_by_year, cpf='123', month_name='JANEIRO',
                       year=2025, employee_name='FULANO')
    assert 2025 in data_by_year
    frame = data_by_year[2025]
    assert 'EDITAR' not in frame.columns
    assert 'HT' in frame.columns and 'ADN' in frame.columns
    # Primeira linha: identificacao do servidor
    assert 'PONTO DIGITAL' in str(frame.iloc[0, 0])
    # Ultima linha: totais
    assert 'TOTAIS' in str(frame.iloc[-1, 0])


def test_generate_dataframe_two_months_one_year(tmp_path):
    data_by_year = {}
    df1 = _build_month_table()
    df2 = _build_month_table()
    df2['ENTRADA'] = '09:00:00'
    generate_dataframe(df1, data_by_year, '123', 'JANEIRO', 2025, 'FULANO')
    generate_dataframe(df2, data_by_year, '123', 'FEVEREIRO', 2025, 'FULANO')
    frame = data_by_year[2025]
    assert frame['DATA ENTRADA'].astype(str).str.contains('JANEIRO').sum() > 0


def test_str_to_date_formatos_do_portal():
    """Datas com sufixo do dia da semana e sem zero à esquerda."""
    assert str_to_date('01/1/2023 - Domingo') == datetime.date(2023, 1, 1)
    assert str_to_date('10/01/2023 - Terça') == datetime.date(2023, 1, 10)
    assert str_to_date('05/01/2025') == datetime.date(2025, 1, 5)
    assert str_to_date('---') is None
    assert str_to_date(None) is None


def test_generate_dataframe_linha_parcial_sem_crash():
    """Linha com entrada preenchida e saída '---' não pode quebrar o ADN."""
    data_by_year = {}
    df = pd.DataFrame([
        {'DATA ENTRADA': '01/1/2023 - Domingo', 'ENTRADA': '06:39:00',
         'DATA SAÍDA': '01/1/2023 - Domingo', 'SAÍDA': '---',
         'TRABALHADA': '---', 'HORA JUSTIFICADA': '---',
         'STATUS': '---', 'EDITAR': ''},
    ])
    df.columns = ['DATA ENTRADA', 'ENTRADA', 'DATA SAÍDA', 'SAÍDA',
                  'TRABALHADA', 'HORA JUSTIFICADA', 'STATUS', 'EDITAR']
    generate_dataframe(df, data_by_year, '123', 'JANEIRO', 2023, 'FULANO')
    frame = data_by_year[2023]
    assert 'ADN' in frame.columns
    assert 'TOTAIS' in str(frame.iloc[-1, 0])