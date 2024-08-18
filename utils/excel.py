import os
import sys
from typing import Dict

import flet as ft
import pandas as pd
from dotenv import load_dotenv

from utils import format_excel

load_dotenv()
file_path = os.getenv('PATH_FILE_BASE')

if not file_path:
    raise ValueError('O caminho para o arquivo do Excel não está definido no .env')


# Cria o arquivo Excel
def generate_excel_file(
        page: ft.Page,
        data_dic: Dict[int, pd.DataFrame],
        employee_name: str,
        cpf: str
):
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

    # Monta uma string concatenando o caminho e nome do arquivo Excel
    file_name = os.path.join(file_path, f'{employee_name} - CPF_{cpf}.xlsx')

    # Usa o método ExcelWriter do Pandas para criar o arquivo
    # Excel usando a biblioteca xlsxwriter
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        # Itera sobre o dicionário (data_dic) extraindo o ano (year)
        # e o Dataframe com os dados dos meses de cada ano
        for year, df_year in data_dic.items():
            # Cria a planilha com abas para cada ano, começando
            # na linha índice 0 do Dataframe, sem trazer os índices
            # das linha e o cabeçalho do Dataframe
            df_year.to_excel(writer, sheet_name=str(year), index=False, startrow=0, header=False)
            workbook = writer.book
            worksheet = writer.sheets[str(year)]

            try:
                # Chama a função (define_formats) do módulo (format_excel)
                #  passando a planilha do Excel (workbook) que será criada
                # e atribui a variável (formats)
                formats = format_excel.define_formats(workbook)

                # Chama a função (apply_formatting) do módulo (format_excel),
                # passando a planilha (worksheet), o Dataframe (df_year) e a
                # variável (formats) definida anteriormente. Essa função aplica
                # as formatações nas planilhas que serão salvas no arquivo Excel.
                format_excel.apply_formatting(worksheet, df_year, formats)
            except Exception as e:
                snack_show(page, f'Erro ao gerar a planilha {file_path}', ft.icons.ERROR, ft.colors.RED)
                print(f'Erro ao gerar a planilha {e}')
                sys.exit(1)
