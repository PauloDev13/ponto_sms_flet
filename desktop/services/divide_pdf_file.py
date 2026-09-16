from pathlib import Path

from backend.core import pdf_service as core_pdf


def divide_pdf_by_size(input_pdf: str, max_size_mb: float, output_prefix: str):
    core_pdf.divide_pdf_by_size(input_pdf, max_size_mb, output_prefix)