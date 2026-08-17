import tempfile
from pathlib import Path

from pypdf import PdfReader

from backend.core import pdf_service as core_pdf


def get_page_size(reader: PdfReader, page_num: int) -> int:
    # Delega ao backend.core usando um diretório temporário controlado
    with tempfile.TemporaryDirectory(prefix='pdfpage_') as tmp:
        return core_pdf.get_page_size(reader, page_num, Path(tmp))


def divide_pdf_by_size(input_pdf: str, max_size_mb: float, output_prefix: str):
    # Delega a divisão ao backend.core (os arquivos temporários
    # são criados em diretório temporário controlado)
    core_pdf.divide_pdf_by_size(input_pdf, max_size_mb, output_prefix)