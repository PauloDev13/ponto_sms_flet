import datetime
import os
from typing import Dict, Union

import flet as ft
from selenium.webdriver.chrome import webdriver

# Busca no arquivo (.env) o valor da URL base e o nome do diretório (NAME_FOLDER)
from config.config_env import NAME_FOLDER

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from utils.share_model import format_cpf

from backend.core.scraper import scrape_months
from services.data.generate_excel_file import generate_excel_file
from services.data.generate_pdf_service import combine_pdfs


# FUNÇÃO QUE INICIA O SCRAPING DA PÁGINA HTML E CHAMA
# AS FUNÇÕES QUE CRIAM OS ARQUIVOS PDF E EXCEL
def search_data(dict_search_data: Dict[str, Union[ft.Control, int, webdriver]]) -> bool | None:
    # Cria o dicionário (dict_fields) com parte dos dados
    # enviados como argumento no dicionário (dict_search_data)
    dict_fields: Dict = {
        k: v for k, v in dict_search_data.items() if k in [
            'checkbox_excel_field',
            'checkbox_pdf_field',
        ]
    }

    # Desempacota os controles (checkbox) armazenados no dicionário (dict_fields)
    checkbox_excel_field, checkbox_pdf_field = dict_fields.values()

    # Cria o dicionário (dict_values) com parte dos dados
    # enviados como argumento no dicionário (dict_search_data)
    dict_values: Dict = {
        k: v for k, v in dict_search_data.items() if k in [
            'cpf_field',
            'unit_field',
            'month_start',
            'year_start',
            'month_end',
            'year_end',
            'driver'
        ]
    }

    # Desempacota os valores armazenados no dicionário (dict_values)
    cpf_field, unit_field, month_start, year_start, month_end, year_end, driver = dict_values.values()

    try:
        # Atribui variáveis para receber o conjunto de dados (dicionário)
        # e as datas do intervalo a ser pesquisado
        cpf = format_cpf(cpf_field)
        unit = unit_field.value
        start_date = datetime.date(year_start, month_start, 1)
        end_date = datetime.date(year_end, month_end, 1)

        # Coleta os dados do período (scraping) delegando ao backend.core
        result = scrape_months(
            driver,
            cpf=cpf,
            unit=unit,
            start_date=start_date,
            end_date=end_date,
            want_excel=checkbox_excel_field.value,
            want_pdf=checkbox_pdf_field.value,
        )

        employee_name = result.employee_name

        # Se algum mês falhou durante a coleta, informa ao usuário
        if result.months_failed:
            AlertSnackbar.show(
                message=f'{result.months_failed} mês(es) não processado(s). '
                        'Verifique os dados e tente novamente.')

        # Se a (checkbox) gerar planilhas está MARCADA
        if checkbox_excel_field.value:
            # Chama a função que cria o arquivo Excel (planilhas)
            generate_excel_file(
                data_dic=result.data_by_year,
                employee_name=employee_name,
                cpf=cpf
            )

        if checkbox_pdf_field.value:
            # Monta a caminho do diretório que será criado e atribui à variável (folder_path).
            # O caminho é: C:/users/<user do windows>/Documents/PLANILHAS_SMS
            folder_path = os.path.join(os.path.expanduser('~'), 'Documents', NAME_FOLDER)

            # Atribui a variável (output_pdf_path) o caminho e o nome do arquivo PDF que será criado
            output_pdf_path = os.path.join(folder_path, f'{employee_name} - CPF_{cpf}.pdf')

            # Chama a função que combina todos os PDFs gerados num só arquivo
            combine_pdfs(pdf_bytes_list=result.pdf_bytes_list, output_path=output_pdf_path)

        # Retorna uma tupla com valores (string, bool)
        return True

    # Se ocorrerem erros, exibe mensagem
    except Exception as e_:
        AlertSnackbar.show(
            message='Erro ao gerar arquivos!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao gerar arquivos!: {e_}')

        # e retorna None
        return None