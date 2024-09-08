import base64
import os
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from selenium.webdriver.chrome import webdriver


# Define a variável que vai receber o array de arquivos PDF
array_pdf_files = []


# FUNÇÃO QUE SALVA O ARQUIVO PDF
def save_pdf(url_search: str, driver: webdriver):
    # Navega para a URL
    driver.get(url_search)

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
        'scale': 0.8,  # Ajusta a escala do conteúdo para caber na página
        'displayHeaderFooter': True,  # Exibir cabeçalho e rodapé
        'headerTemplate': '<span style="font-size: 10px;">Título da Página: <span class="title"></span></span>',
        # Exibe o título da página no cabeçalho
        'footerTemplate': '''
                <div style="font-size:10px; width: 100%; text-align: center;">
                    <span class="date"></span> | URL: <span class="url"></span> | 
                    Página <span class="pageNumber"></span> de <span class="totalPages"></span>
                </div>''',  # Exibe data, URL e numeração no rodapé
    })
    # Atribui a variável (pdf_data) o valor da chave (data)
    pdf_data = result['data']
    # Transforma em bytes base64 o conteúdo da chave (data)
    pdf_bytes = base64.b64decode(pdf_data)

    # Armazena os bytes do PDF no array
    array_pdf_files.append(pdf_bytes)

    return array_pdf_files


# FUNÇÃO QUE COMBINA OS ARQUIVOS PDF NUM SÓ ARQUIVO
def combine_pdfs(pdf_bytes_list, output_path):
    # Cria uma instância de (PdfMerger) e atribui a variável (pdf_merge)
    # pdf_merge = PdfMerger()
    pdf_writer = PdfWriter()

    # Executa loop no array onde estão os arquivos PDF
    for pdf_bytes in pdf_bytes_list:
        # Lê os bytes de cada arquivo PDF e atribui à variável (pdf_reader)
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        # Combina os arquivos PDF num só arquivo
        pdf_writer.append(pdf_reader)

    # Salva o arquivo PDF único
    with open(output_path, 'wb') as output_pdf:
        pdf_writer.write(output_pdf)

