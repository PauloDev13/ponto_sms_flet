"""Testes do backend.core.pdf_service (pipelines de PDF puros).

Não exige Ghostscript: combinacao de PDFs e divisao sao testadas com
bytes sinteticos gerados pelo proprio pypdf.
"""
from io import BytesIO

from pypdf import PdfReader, PdfWriter

from backend.core.pdf_service import combine_pdfs, divide_pdf_by_size


def _make_pdf_bytes(text: str = 'conteudo') -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_blank_page(width=100, height=100)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_combine_pdfs(tmp_path):
    out = tmp_path / 'combinado.pdf'
    result = combine_pdfs([_make_pdf_bytes(), _make_pdf_bytes()], out)
    assert result == out and out.exists()
    reader = PdfReader(str(out))
    assert len(reader.pages) == 4


def test_combine_pdfs_ignores_empty_bytes(tmp_path):
    out = tmp_path / 'combinado_vazio.pdf'
    result = combine_pdfs([b'', _make_pdf_bytes()], out)
    assert result.exists()
    assert len(PdfReader(str(out)).pages) == 2


def test_divide_pdf_by_size(tmp_path):
    combined = tmp_path / 'base.pdf'
    combine_pdfs([_make_pdf_bytes() for _ in range(5)], combined)
    prefix = combined.with_suffix('')
    parts = divide_pdf_by_size(combined, max_size_mb=0.0001, output_prefix=prefix)
    assert len(parts) >= 2
    total_pages = 0
    for part in parts:
        assert part.exists()
        total_pages += len(PdfReader(str(part)).pages)
    assert total_pages == 10


def test_divide_pdf_by_size_preserva_cpf_no_nome(tmp_path):
    """Pontos do CPF no prefix não podem ser tratados como extensão."""
    combined = tmp_path / 'Ruth Dayane - CPF_026.930.289-14_pb.pdf'
    combine_pdfs([_make_pdf_bytes() for _ in range(3)], combined)
    prefix = combined.with_suffix('')
    parts = divide_pdf_by_size(combined, max_size_mb=0.0001, output_prefix=prefix)
    assert parts
    for part in parts:
        assert 'CPF_026.930.289-14_pb_part' in part.name