import base64
import datetime
import os
from io import BytesIO

from PyPDF2 import PdfReader, PdfMerger
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Carrega o arquivo .env
load_dotenv()

# Ler a URL base que vai montar a busca dos dados
url_data = os.getenv('URL_DATA')

# Busca no arquivo (.env) o valor ('NAME_FOLDER') e atribui à variável (name_folder)
name_folder = os.getenv('NAME_FOLDER')

if not url_data and not name_folder:
    raise ValueError('O parâmetro (URL_DATA) não está definido no .env')

array_pdf_files = []


def generate_pdf(*args):
    # Define a variável (name) que vai receber o nome do
    # servidor cujo os dados estão sendo extraídos
    name: str = ''

    # Monta a caminho do diretório que será criado e atribui à variável (folder_path).
    # O caminho é: C:/users/<user do windows>/Documents/PLANILHAS_SMS
    folder_path = os.path.join(os.path.expanduser('~'), 'Documents', name_folder)

    # Desempacota os argumentos passados em (*args)
    cpf, month_start, year_start, month_end, year_end, driver = args

    try:
        # Atribui variáveis para receber o conjunto de dados (dicionário)
        # e as datas do intervalo a ser pesquisado
        current_date = datetime.date(year_start, month_start, 1)
        end_date = datetime.date(year_end, month_end, 1)

        while current_date <= end_date:
            month = current_date.month
            year = current_date.year

            # Monta e atribui a variável 'table' a URL com os query params
            # da pesquisa e abre no navegador
            url_search = f'{url_data}?cpf={cpf}&mes={month}&ano={year}'
            driver.get(url_search)

            # Verifica se o elemento HTML contém a tag 'span/font[1]'
            WebDriverWait(driver, 5).until(
                ec.presence_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]")
                )
            )
            # Procura e atribui a variável 'employee_name' o conteúdo da tag 'span/font[1]'
            name = driver.find_element(
                By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]"
            ).text

            save_pdf(url_=url_search, driver=driver)

            # Incrementa em um mês a data inicial
            current_date += datetime.timedelta(days=32)

            # Modifica o dia da data inicial para o primeiro dia do mês
            current_date = current_date.replace(day=1)

        # ------------ FIM DO LAÇO WHILE -------------

        output_pdf_path = os.path.join(folder_path, f'{name} - CPF_{cpf}.pdf')
        combine_pdfs(array_pdf_files, output_pdf_path)

        return True

    except Exception as e:
        print('Erro ao gerar a pdf.', e)
        return False


def save_pdf(url_, driver):
    # Navega para a URL
    driver.get(url_)

    # Captura o PDF da página
    result = driver.execute_cdp_cmd('Page.printToPDF', {'landscape': True})
    pdf_data = result['data']
    pdf_bytes = base64.b64decode(pdf_data)

    # Armazena os bytes do PDF no array
    array_pdf_files.append(pdf_bytes)


def combine_pdfs(pdf_bytes_list, output_path):
    pdf_merge = PdfMerger()

    for pdf_bytes in pdf_bytes_list:
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        pdf_merge.append(pdf_reader)

    with open(output_path, 'wb') as output_pdf:
        pdf_merge.write(output_pdf)
