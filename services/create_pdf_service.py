import base64
import datetime
import os
from io import BytesIO

from PyPDF2 import PdfReader, PdfMerger
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar

# Carrega o arquivo .env
load_dotenv()

# Ler a URL base que vai montar a busca dos dados
url_data = os.getenv('URL_DATA')

# Busca no arquivo (.env) o valor ('NAME_FOLDER') e atribui à variável (name_folder)
name_folder = os.getenv('NAME_FOLDER')

if not url_data and not name_folder:
    raise ValueError('O parâmetro (URL_DATA) não está definido no .env')

# Define a variável que vai receber o array de arquivos PDF
array_pdf_files = []


# FUNÇÃO QUE GERA O ARQUIVO PDF
def generate_pdf(*args):
    # Define a variável (name) que vai receber o nome do funcionário
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

        # Enquanto a data inicial for menor que a data final
        while current_date <= end_date:
            # Extrai o mês e o ano da data inicial
            month = current_date.month
            year = current_date.year

            # Atribui a variável (url_search) a URL com os query params
            # da pesquisa e abre no navegador com a url
            url_search = f'{url_data}?cpf={cpf}&mes={month}&ano={year}'
            driver.get(url_search)

            # Verifica se o elemento HTML contém a tag 'span/font[1]'
            WebDriverWait(driver, 5).until(
                ec.presence_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]")
                )
            )
            # Procura e atribui a variável (name) o conteúdo da tag
            # (span/font[1]) que tem no mome do funcionário
            name = driver.find_element(
                By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]"
            ).text

            # Chama a função (save_pdf) passando a url e a instância do navegador
            save_pdf(url_=url_search, driver=driver)

            # Incrementa em um mês a data inicial
            current_date += datetime.timedelta(days=32)

            # Modifica o dia da data inicial para o primeiro dia do mês
            current_date = current_date.replace(day=1)

        # ------------ FIM DO LAÇO WHILE -------------

        # Atribui a variável (output_pdf_path) o caminho e
        # o nome do arquivo PDF que será criado
        output_pdf_path = os.path.join(folder_path, f'{name} - CPF_{cpf}.pdf')
        # Chama a função () passando como argumento o array com os
        # bytes dos arquivos gerados a cadas mês e ano e o caminho
        combine_pdfs(array_pdf_files, output_pdf_path)

        # Retorna verdadeiro se não houver erros
        return True

    except Exception as e:
        # Exibe mensagens de erros na janela e no console
        AlertSnackbar.show('Ocorreu um erro ao gerar o arquivo PDF.')
        print('Erro ao gerar a pdf.', e)

        # Retorna falso se ocorrer erros
        return False


# FUNÇÃO QUE SALVA O ARQUIVO PDF
def save_pdf(url_, driver):
    # Navega para a URL
    driver.get(url_)

    # Captura o PDF da página e formata a saída como página paisagem
    result = driver.execute_cdp_cmd('Page.printToPDF', {
        'landscape': True,
        'paperWidth': 8.27,  # Largura do papel (A4)
        'paperHeight': 11.69,  # Altura do papel (A4)
        'marginTop': 0.5,  # Margem superior
        'marginBottom': 0.5,  # Margem inferior
        'marginLeft': 0.5,  # Margem esquerda
        'marginRight': 0.5,  # Margem direita
        'printBackground': False,  # Imprimir fundos e imagens
        'scale': 0.9,  # Ajusta a escala do conteúdo para caber na página
        'displayHeaderFooter': True,  # Exibir cabeçalho e rodapé
        'headerTemplate': '<span style="font-size: 10px;">Título da Página: <span class="title"></span></span>',
        # Exibe o título da página no cabeçalho
        'footerTemplate': '''
                <div style="font-size:10px; width: 100%; text-align: center;">
                    <span class="date"></span> | URL: <span class="url"></span> | Página <span class="pageNumber"></span> de <span class="totalPages"></span>
                </div>''',  # Exibe data, URL e numeração no rodapé
    })
    # Atribui a variável (pdf_data) o valor da chave (data)
    pdf_data = result['data']
    # Transforma em bytes base64 o conteúdo da chave (data)
    pdf_bytes = base64.b64decode(pdf_data)

    # Armazena os bytes do PDF no array
    array_pdf_files.append(pdf_bytes)


# FUNÇÃO QUE COMBINA OS ARQUIVOS PDF NUM SÓ ARQUIVO
def combine_pdfs(pdf_bytes_list, output_path):
    # Cria uma instância de (PdfMerger) e atribui a variável (pdf_merge)
    pdf_merge = PdfMerger()

    # Executa loop no array onde estão os arquivos PDF
    for pdf_bytes in pdf_bytes_list:
        # Lê os bytes de cada arquivo PDF e atribui à variável (pdf_reader)
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        # Combina os arquivos PDF num só arquivo
        pdf_merge.append(pdf_reader)

    # Salva o arquivo PDF único
    with open(output_path, 'wb') as output_pdf:
        pdf_merge.write(output_pdf)
