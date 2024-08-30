import os
from typing import Dict

import flet as ft
import pandas as pd
from dotenv import load_dotenv

# Importações dos módulos locais
from utils.format_excel import define_formats, apply_formatting

load_dotenv()

# Busca no arquivo (.env) o valor ('NAME_FOLDER') e atribui à variável (name_folder)
name_folder = os.getenv('NAME_FOLDER')

if not name_folder:
    raise ValueError('O caminho para o arquivo do Excel não está definido no .env')


# FUNÇÃO LOCAL PARA CRIAR O DIRETÓRIO ONDE SERÃO
# SALVOS OS ARQUIVOS DO EXCEL QUE SERÃO GERADOS
def create_folder(name_file: str):
    # Importa a função (snack_show) do módulo (controls.components) para exibir mensagens
    from controls.components import snack_show

    try:
        # Monta a caminho do diretório que será criado e atribui à variável (folder_path).
        # O caminho é: C:/users/<user do windows>/Documents/PLANILHAS_SMS
        folder_path = os.path.join(os.path.expanduser('~'), 'Documents', name_folder)

        # Se o diretório não existir, será criado
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Monta o caminho completo para salvar o arquivo Excel.
        # C:/users/<user_do_windows>/Documents/PLANILHAS_SMS/<nome_arquivo.xlsx>
        # e atribui à variável (path_file_excel)
        path_file_excel = os.path.join(folder_path, name_file)

        # Retorna o caminho completo do diretório com o nome do arquivo
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
    # Importa a função (snack_show) do módulo (controls) para exibir mensagens
    from controls.components import snack_show

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
                snack_show(
                    message='Erro ao gerar a planilha {path_file_name}',
                    icon=ft.icons.ERROR,
                    icon_color=ft.colors.RED
                )
                print(f'Erro ao gerar a planilha {e}')

    # Retorna o caminho completo onde o arquivo será salvo
    return path_file_name
