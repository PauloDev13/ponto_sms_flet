import pandas as pd

from backend.core.dataframe import generate_dataframe
from backend.core.excel_service import generate_excel_file


def _build_data_dic():
    data_by_year = {}
    df = pd.DataFrame([
        {'DATA ENTRADA': '05/01/2025', 'ENTRADA': '08:00:00', 'DATA SAÍDA': '05/01/2025',
         'SAÍDA': '17:00:00', 'TRABALHADA': '08:30:00', 'HORA JUSTIFICADA': '00:00:00',
         'STATUS': 'APROVADO', 'EDITAR': ''},
    ])
    generate_dataframe(df, data_by_year, '123', 'JANEIRO', 2025, 'FULANO')
    return data_by_year


def test_generate_excel_file(tmp_path):
    out = tmp_path / 'planilha' / 'FULANO_123.xlsx'
    data_dic = _build_data_dic()
    result = generate_excel_file(data_dic, 'FULANO', '123', out)
    assert result.exists() and result == out

    with pd.ExcelFile(result) as xl:
        assert '2025' in xl.sheet_names
        df = pd.read_excel(result, sheet_name='2025', header=None)
        assert 'PONTO DIGITAL' in str(df.iloc[0, 0])
        assert 'TOTAIS' in str(df.iloc[-1, 0])


def test_generate_excel_with_password(tmp_path):
    out = tmp_path / 'protegido.xlsx'
    data_dic = _build_data_dic()
    generate_excel_file(data_dic, 'FULANO', '123', out, password='s3nha')
    assert out.exists()