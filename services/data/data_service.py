import flet as ft
import calendar
import datetime
import locale
import os
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from utils.excel import generate_excel_file
from services.data.dataframe_service import create_dataframe

# Carrega o arquivo .env
load_dotenv()

# Define a localização como português do Brasil (pt_BR)
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Ler a URL base que vai montar a busca dos dados
url_data = os.getenv('URL_DATA')

if not url_data:
    raise ValueError('O parâmetro (URL_DATA) não está definido no .env')


def search_data(*args):
    # Define a variável que vai receber o nome do funcionário pesquisado
    employee_name: str = ''

    # Desempacota os argumentos passados em (*args)
    checkbox_excel_field, cpf, month_start, year_start, month_end, year_end, driver = args
    # (cpf, month_start, year_start, month_end,
    #  year_end, cpf_field, start_date_field, driver,
    #  end_date_field, checkbox_excel_field, checkbox_pdf_field) = args


    try:
        # Atribui variáveis para receber o conjunto de dados (dicionário)
        # e as datas do intervalo a ser pesquisado
        data_by_year: dict[int, pd.DataFrame] = {}
        current_date = datetime.date(year_start, month_start, 1)
        end_date = datetime.date(year_end, month_end, 1)

        # Enquanto a data inicial for menor que a data final,
        # são atribuídos as variáveis 'month' e 'year' os valores
        # do mês e ano extraídos das datas informadas
        while current_date <= end_date:
            month = current_date.month
            year = current_date.year

            # Usa a biblioteca 'calendar' para extrair o nome do mês e
            # a biblioteca 'locale' para tradução em português
            month_name = calendar.month_name[month].upper()

            # Monta e atribui a variável 'table' a URL com os query params
            # da pesquisa e abre no navegador
            url_search = f'{url_data}?cpf={cpf}&mes={month}&ano={year}'
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

                TODO: 'ENTRA O CÓDIGO PARA MONTAR O ARRAY QUE VAI GERAR O ARQUIVO PDF'

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

                # TODO: 'ENTRA O CÓDIGO PARA MONTAR O DATA FRAME QUE VAI GERAR O ARQUIVO EXCEL'
                # if checkbox_excel_field:
                #     create_dataframe(
                #         df_table=df_table,
                #         data_by_year=data_by_year,
                #         employee_name=employee_name,
                #         month_name=month_name,
                #         year=year,
                #         cpf=cpf,
                #     )

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

        # Chama a função que cria e salva o arquivo Excel
        # atribuindo seu resultado à variável (path_file_name)
        path_file_name = generate_excel_file(
            data_dic=data_by_year,
            employee_name=employee_name,
            cpf=cpf
        )

        return path_file_name

    # Se ocorrerem erros, exibe mensagem
    except Exception as e_:
        AlertSnackbar.show(
            message='Erro ao gerar arquivo!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao gerar arquivo: {e_}')

        return None
