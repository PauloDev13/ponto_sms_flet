from typing import Dict

import flet as ft
import pandas as pd

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from utils.format_excel_file import define_formats, apply_formatting
from utils.share_model import open_file_excel, create_folder


# FUNÇÃO QUE CRIA O ARQUIVO EXCEL
def generate_excel_file(
        data_dic: Dict[int, pd.DataFrame],
        employee_name: str,
        cpf: str
) -> None:
    # Chama a função local (create_folder) passando o nome do arquivo
    # do Excel e atribui o retorno à variável (path_file_name)
    path_file_name = create_folder(name_file=f'{employee_name} - CPF_{cpf}.xlsx')

    # Usa o método ExcelWriter do (Pandas) para criar o arquivo Excel passando
    #  o caminho completo (path_file_name) e biblioteca xlsxwriter
    with pd.ExcelWriter(path_file_name, engine='xlsxwriter') as writer:
        # Itera sobre o dicionário (data_dic) extraindo o ano (year)
        # e o Dataframe (df_year) com os dados dos meses de cada ano
        for year, df_year in data_dic.items():
            # Usa o método (to_excel) do (Pandas) para criar a planilha com abas para
            #  cada ano, começando na linha índice 0 do Dataframe, sem trazer os índices
            # das linha e o cabeçalho do Dataframe
            df_year.to_excel(
                writer,
                sheet_name=str(year),
                startrow=0,
                index=False,
                header=False
            )
            # Instância um arquivo Excel e atribui à variável (workbook)
            workbook = writer.book

            # Adiciona no arquivo criado as planilhas referente
            # aos anos cada uma em abas individuais
            worksheet = writer.sheets[str(year)]

            try:
                # Chama a função (define_formats) do módulo (utils.format_excel)
                #  passando a planilha do Excel (workbook) que será criada
                # e atribui o resultado à variável (formats). Essa função define
                # diversas formatações para as planilhas
                formats = define_formats(workbook)

                # Chama a função (apply_formatting) do módulo (utils.format_excel),
                # passando as planilhas (worksheet), o Dataframe (df_year) e a
                # variável (formats) definida anteriormente. Essa função aplica
                # as formatações nas planilhas do arquivo Excel.
                apply_formatting(worksheet, df_year, formats)
            except Exception as e:
                AlertSnackbar.show(
                    message='Erro ao gerar a planilha {path_file_name}',
                    icon=ft.icons.ERROR,
                    icon_color=ft.colors.RED
                )
                print(f'Erro ao gerar a planilha {e}')

        open_file_excel(path_file_excel=path_file_name)
