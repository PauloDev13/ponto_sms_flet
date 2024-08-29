import os
import sys
from typing import Dict

import flet as ft
import pandas as pd
from dotenv import load_dotenv

from utils import format_excel

load_dotenv()
name_folder = os.getenv('NAME_FOLDER')

if not name_folder:
    raise ValueError('O caminho para o arquivo do Excel não está definido no .env')


def create_folder(name_file: str):
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

    try:
        folder_path = os.path.join(os.path.expanduser('~'), 'Documents', name_folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        path_file_excel = os.path.join(folder_path, name_file)

        return path_file_excel

    except Exception as e:
        snack_show(
            message=f'Erro ao criar o arquivo {name_file}',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )

        print(f'Erro ao criar o arquivo {name_file} - {e}')


# FUNÇÃO QUE CRIA O ARQUIVO EXCEL
def generate_excel_file(
        data_dic: Dict[int, pd.DataFrame],
        employee_name: str,
        cpf: str
) -> str:
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

    # Monta uma string concatenando o caminho e nome do arquivo Excel
    path_file_name = create_folder(name_file=f'{employee_name} - CPF_{cpf}.xlsx')
    # file_name = os.path.join(file_path, f'{employee_name} - CPF_{cpf}.xlsx')

    # Usa o método ExcelWriter do Pandas para criar o arquivo
    # Excel usando a biblioteca xlsxwriter
    with pd.ExcelWriter(path_file_name, engine='xlsxwriter') as writer:
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
                snack_show(
                    message='Erro ao gerar a planilha {path_file_name}',
                    icon=ft.icons.ERROR,
                    icon_color=ft.colors.RED
                )
                print(f'Erro ao gerar a planilha {e}')

    return path_file_name
