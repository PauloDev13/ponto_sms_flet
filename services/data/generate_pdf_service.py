import base64
import os
from io import BytesIO
from typing import List

from pypdf import PdfReader, PdfWriter
from selenium.webdriver.chrome import webdriver

# Busca no arquivo (.env) o nome do diretório (NAME_FOLDER)
from config.config_env import NAME_FOLDER

# Importação dos módulos locais
from models.page_manager import PageManager
from models.alert_snackbar import AlertSnackbar
from services.compress_pdf_file import compress_pdf_with_ghostscript
from services.divide_pdf_file import divide_pdf_by_size
from utils.share_model import data_progress_bar

# Define a variável que vai receber o array de arquivos PDF
array_pdf_files: List[bytes] = []


# FUNÇÃO QUE SALVA O ARQUIVO PDF
def save_pdf(url_search: str, driver: webdriver) -> List[bytes]:
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
def combine_pdfs(pdf_bytes_list: List[bytes], output_path: str) -> None:
    page = PageManager.get_page()

    # Cria uma instância de (PdfMerger) e atribui a variável (pdf_merge)
    # pdf_merge = PdfMerger()
    pdf_writer = PdfWriter()

    try:
        # Executa loop no array onde estão os arquivos PDF
        for pdf_bytes in pdf_bytes_list:
            # Lê os bytes de cada arquivo PDF e atribui à variável (pdf_reader)
            pdf_reader = PdfReader(BytesIO(pdf_bytes))

            # Combina os arquivos PDF num só arquivo
            pdf_writer.append(pdf_reader)

        # Salva o arquivo PDF único
        with open(output_path, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)

        # Pega o caminho do diretório onde está o arquivo PDF
        folder_path = os.path.join(os.path.expanduser('~'), 'Documents', NAME_FOLDER)

        # pega o caminho completo onde o arquivo PDF original foi salvo,
        # coloca no final do nome do arquivo o complemento ('_pb')
        output_pdf_path = os.path.join(folder_path, output_path.replace('.pdf', '_pb.pdf'))

        # Remove a barra de progresso que está sendo exibida
        page.overlay.pop()
        page.update()

        # Chama a função que exibe a barra de progresso com outra mensagem
        data_progress_bar('Compactando arquivo PDF. AGUARDE')

        # Chama a função que compacta o arquivo PDF passando o caminho completo
        # do arquivo original e o caminho completo onde o novo arquivo compactado será salvo
        compress_pdf_with_ghostscript(input_pdf=output_path, output_pdf=output_pdf_path)

        # Após a compactação, exclui do diretório o arquivo PDF original
        os.remove(output_path)

        # Remove a barra de progresso que está sendo exibida
        page.overlay.pop()
        page.update()

        # Chama a função que exibe a barra de progresso com outra mensagem
        data_progress_bar('Dividindo arquivo PDF. AGUARDE')

        # Retira a extensão .PDF do arquivo original e atribui
        # somente o nome à variável (output_file_name)
        output_file_name = os.path.splitext(output_path)[0]

        # Chama a função que divide o arquivo PDF se
        # o seu tamanho for maior ou igual a 6.5Mb
        divide_pdf_by_size(output_pdf_path, 6.5, output_file_name)

        # Após a divisão, exclui do diretório o arquivo PDF compactado
        os.remove(output_pdf_path)

        # Limpa o array que contém os arquivos PDF em formato binário.
        pdf_bytes_list.clear()

    except Exception as e:
        AlertSnackbar.show(message='Erro ao combinar PDFs!')
        print('Erro ao combinar PDFs!', e)
