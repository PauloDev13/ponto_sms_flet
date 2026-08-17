from pathlib import Path
from typing import List

from selenium.webdriver.chrome import webdriver

# Importação dos módulos locais
from desktop.models.page_manager import PageManager
from desktop.models.alert_snackbar import AlertSnackbar

from backend.core import pdf_service as core_pdf

# Define a variável que vai receber o array de arquivos PDF
array_pdf_files: List[bytes] = []


# FUNÇÃO QUE SALVA O ARQUIVO PDF
def save_pdf(url_search: str, driver: webdriver) -> List[bytes]:
    # Navega para a URL, captura o PDF da página (via CDP)
    # e armazena os bytes no array (delegação ao backend.core)
    pdf_bytes = core_pdf.capture_pdf_bytes(driver, url_search)

    array_pdf_files.append(pdf_bytes)

    return array_pdf_files


# FUNÇÃO QUE COMBINA OS ARQUIVOS PDF NUM SÓ ARQUIVO
def combine_pdfs(pdf_bytes_list: List[bytes], output_path: str) -> None:
    page = PageManager.get_page()

    try:
        # Delega ao backend.core a combinação, compactação
        # e divisão do arquivo PDF
        parts = core_pdf.process_pdf_artifact(
            pdf_bytes_list=pdf_bytes_list,
            output_path=output_path,
            max_size_mb=6.5,
        )

        # Remove a barra de progresso que está sendo exibida
        page.overlay.pop()
        page.update()

        # Exclui os arquivos intermediários (original combinado e compactado),
        # mantendo apenas as partes geradas como entregáveis
        combined = Path(output_path)
        candidates = [combined, combined.with_name(combined.stem + '_pb.pdf')]
        parts_names = {str(p) for p in parts}

        for candidate in candidates:
            if candidate.exists() and str(candidate) not in parts_names:
                candidate.unlink()

        # Limpa o array que contém os arquivos PDF em formato binário.
        pdf_bytes_list.clear()

    except Exception as e:
        AlertSnackbar.show(message='Erro ao combinar PDFs!')
        print('Erro ao combinar PDFs!', e)
