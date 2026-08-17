"""Testes do backend.core.pdf_service (pipelines de PDF puros).

Não exige Ghostscript: combinacao de PDFs e divisao sao testadas com
bytes sinteticos gerados pelo proprio pypdf. A compressão é testada com
o binário/expressão do Ghostscript mockados.
"""
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from backend.core import pdf_service
from backend.core.exceptions import FileGenerationError
from backend.core.pdf_service import (
    combine_pdfs,
    compress_pdf_with_ghostscript,
    divide_pdf_by_size,
)


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


def _fake_gs_run(input_pdf, output_pdf):
    """Emula o Ghostscript copiando o PDF de entrada para a saída."""
    from pathlib import Path
    Path(input_pdf).read_bytes()
    Path(output_pdf).write_bytes(Path(input_pdf).read_bytes())


class FakeResult:
    def __init__(self, returncode, stderr=''):
        self.returncode = returncode
        self.stderr = stderr


class TestCompressPdfWithGhostscript:

    def test_compress_ok_chama_subprocess_e_gera_saida(self, tmp_path, monkeypatch):
        """Com o binário disponível, o subprocess é chamado e a saída existe."""
        source = tmp_path / 'base.pdf'
        combine_pdfs([_make_pdf_bytes() for _ in range(2)], source)
        out = tmp_path / 'comprimido_pb.pdf'

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            _fake_gs_run(cmd[-1], cmd[-2].split('=', 1)[1])
            return FakeResult(0)

        monkeypatch.setattr(pdf_service.subprocess, 'run', fake_run)
        monkeypatch.setattr(pdf_service, 'find_ghostscript', lambda: 'gswin64c.exe')

        result = compress_pdf_with_ghostscript(source, out)

        assert result == out and out.exists()
        assert len(PdfReader(str(out)).pages) == 4
        assert '-dPDFSETTINGS=/screen' in calls[0]

    def test_compress_sem_ghostscript_levanta_filegeneration(self, tmp_path, monkeypatch):
        """Binário ausente: erro tipado orientando a instalação."""
        source = tmp_path / 'base.pdf'
        combine_pdfs([_make_pdf_bytes()], source)
        monkeypatch.setattr(pdf_service, 'find_ghostscript', lambda: None)

        with pytest.raises(FileGenerationError, match='Ghostscript não encontrado'):
            compress_pdf_with_ghostscript(source, tmp_path / 'x_pb.pdf')

    def test_compress_gs_falhou_levanta_filegeneration(self, tmp_path, monkeypatch):
        """Ghostscript com returncode != 0: erro tipado com o stderr."""
        source = tmp_path / 'base.pdf'
        combine_pdfs([_make_pdf_bytes()], source)
        monkeypatch.setattr(pdf_service, 'find_ghostscript', lambda: 'gswin64c.exe')
        monkeypatch.setattr(
            pdf_service.subprocess, 'run',
            lambda *a, **k: FakeResult(1, 'GS falhou aqui'))

        with pytest.raises(FileGenerationError, match='GS falhou aqui'):
            compress_pdf_with_ghostscript(source, tmp_path / 'x_pb.pdf')

    def test_process_pdf_artifact_fallback_sem_gs(self, tmp_path, monkeypatch):
        """Sem Ghostscript, process_pdf_artifact mantém o PDF combinado."""
        monkeypatch.setattr(pdf_service, 'find_ghostscript', lambda: None)
        out = tmp_path / 'concat.pdf'

        parts = pdf_service.process_pdf_artifact(
            [_make_pdf_bytes() for _ in range(2)], out, max_size_mb=6.5)

        assert parts and parts[0].exists()
        assert len(PdfReader(str(parts[0])).pages) == 4