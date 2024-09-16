import calendar
import datetime
import locale
import os
from io import StringIO
from typing import Dict, Union, List

import flet as ft
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Busca no arquivo (.env) o valor da URL base e o nome do diretório (NAME_FOLDER)
from config.config_env import NAME_FOLDER
from config.config_env import URL_DATA

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from services.data.generate_df_service import generate_dataframe
from services.data.generate_excel_file import generate_excel_file
from services.data.generate_pdf_service import save_pdf, combine_pdfs
from utils.share_model import format_cpf

# Define a localização como português do Brasil (pt_BR)
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')


# FUNÇÃO QUE INICIA O SCRAPING DA PÁGINA HTML E CHAMA
# AS FUNÇÕES QUE CRIAM OS ARQUIVOS PDF E EXCEL
def search_data(dict_search_data: Dict[str, Union[ft.Control, int, webdriver]]) -> bool | None:
    # Define a variável que vai receber o nome do funcionário pesquisado
    employee_name: str = ''

    # Define o array (pdf_byte_list) que vai receber a lista
    # com as páginas dos arquivos PDF que serão gerados
    pdf_byte_list: List[bytes] = []

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
        data_by_year: Dict[int, pd.DataFrame] = {}
        current_date = datetime.date(year_start, month_start, 1)
        end_date = datetime.date(year_end, month_end, 1)
        unit = unit_field.value


        # Enquanto a data inicial for menor que a data final,
        # são atribuídos as variáveis 'month' e 'year' os valores
        # do mês e ano extraídos das datas informadas
        while current_date <= end_date:
            month = current_date.month
            year = current_date.year

            # Usa a biblioteca 'calendar' para extrair o nome do mês e
            # a biblioteca 'locale' para tradução do nome para português
            month_name = calendar.month_name[month].upper()

            # Monta e atribui a variável (url_search) a URL com
            # os query params da pesquisa e abre no navegador
            if month < 10:
                # url_search = f'{URL_DATA}?cpf={cpf}&mes=0{month}&ano={year}'
                url_search = f'{URL_DATA}?cpf={cpf}&mes=0{month}&ano={year}&unidade={unit}'
            else:
                # url_search = f'{URL_DATA}?cpf={cpf}&mes={month}&ano={year}'
                url_search = f'{URL_DATA}?cpf={cpf}&mes={month}&ano={year}&unidade={unit}'

            driver.get(url_search)

            try:
                # Verifica se o elemento HTML contém a tag 'span/font[1]'
                WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located(
                        (By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]")
                    )
                )
                # Procura e atribui a variável 'employee_name' o conteúdo da tag 'span/font[1]'
                employee_name = driver.find_element(
                    By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]"
                ).text

                # Verifica se o elemento HTML contém uma tag table
                table = WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.XPATH, "//*[@id='mesatual']/table"))
                )

                # Utiliza a biblioteca BeautifulSoup para pegar o HTML da table
                # e atribui o resultado à variável 'soup' como uma string
                soup_table = BeautifulSoup(table.get_attribute("outerHTML"), 'html.parser')

                # Utiliza a biblioteca Pandas para montar DataFrame com todos os dados
                # da primeira table encontrada no HTML
                df_table = pd.read_html(StringIO(str(soup_table)))[0]

                # Se as opções (gerar planilha) e (gerar arquivo PDF) estão MARCADAS
                if checkbox_excel_field.value and checkbox_pdf_field.value:
                    # Chama a função que monta o Dataframe que vai gerar o arquivo Excel
                    generate_dataframe(
                        df_table=df_table,
                        data_by_year=data_by_year,
                        employee_name=employee_name,
                        month_name=month_name,
                        year=year,
                        cpf=cpf,
                    )

                    # Chama a função que monta a estrutura do arquivo PDF
                    pdf_byte_list: List[bytes] = save_pdf(
                        url_search=url_search,
                        driver=driver,
                    )

                # Se a opção (gerar planilha) está MARCADA
                # e (gerar arquivo PDF) está DESMARCADA
                if checkbox_excel_field.value and not checkbox_pdf_field.value:
                    # Chama a função que monta o Dataframe que vai gerar o arquivo Excel
                    generate_dataframe(
                        df_table=df_table,
                        data_by_year=data_by_year,
                        employee_name=employee_name,
                        month_name=month_name,
                        year=year,
                        cpf=cpf,
                    )

                # Se a opção (gerar arquivo PDF) está MARCADA
                #  e (gerar planilha) está DEMARCADA
                if checkbox_pdf_field.value and not checkbox_excel_field.value:
                    # Chama a função que monta a estrutura do arquivo PDF
                    pdf_byte_list: List[bytes] = save_pdf(
                        url_search=url_search,
                        driver=driver,
                    )

            # Se ocorrer erro durante o processo de coleta e montagem de dados no DataFrame,
            # exibe mensagem de erro, espera 2 segundos e fecha a mensagem
            except TimeoutException as e_:
                AlertSnackbar.show(
                    message=f'Problemas ao carregar dados para {month}/{year}')

                print(f'Erro ao carregar dados: {e_}')

            # Incrementa em um mês a data inicial
            current_date += datetime.timedelta(days=32)

            # Modifica o dia da data inicial para o primeiro dia do mês
            current_date = current_date.replace(day=1)

        # ------------ FIM DO LAÇO WHILE -------------

        # Define a variável (path_file_name) com o valor vazio
        path_file_name: str = ''

        # Se a (checkbox) gerar planilhas está MARCADA
        if checkbox_excel_field.value:
            # Chama a função que cria o arquivo Excel (planilhas)
            # atribuindo ao seu retorno à variável (path_file_name)
            generate_excel_file(
                data_dic=data_by_year,
                employee_name=employee_name,
                cpf=cpf
            )

        if checkbox_pdf_field.value:
            # Monta a caminho do diretório que será criado e atribui à variável (folder_path).
            # O caminho é: C:/users/<user do windows>/Documents/PLANILHAS_SMS
            folder_path = os.path.join(os.path.expanduser('~'), 'Documents', NAME_FOLDER)

            # Atribui a variável (output_pdf_path) o caminho e o nome do arquivo PDF que será criado
            output_pdf_path = os.path.join(folder_path, f'{employee_name} - CPF_{cpf}.pdf')

            combine_pdfs(pdf_bytes_list=pdf_byte_list, output_path=output_pdf_path)

        # Retorna uma tupla com valores (string, bool)
        return True

    # Se ocorrerem erros, exibe mensagem
    except Exception as e_:
        AlertSnackbar.show(
            message='Erro ao gerar arquivo!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao gerar arquivo: {e_}')

        # e retorna None
        return None
