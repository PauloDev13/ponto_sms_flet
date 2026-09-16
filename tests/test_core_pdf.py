"""Testes do backend.core.pdf_service (pipelines de PDF com PyMuPDF).

Valida:
- Combinação de múltiplos PDFs em um único arquivo com escala de cinza (DeviceGray).
- Compressão pura em Python via PyMuPDF (sem Ghostscript/subprocess).
- Divisão condicional: fatiamento apenas quando o arquivo ultrapassa o limite (ex: 5MB).
- Nomenclatura padronizada de partes (_part_01.pdf, _part_02.pdf).
- Remoção do arquivo original consolidado apenas quando houver divisão.
"""
from pathlib import Path

import pymupdf
import pytest

from backend.core import pdf_service
from backend.core.pdf_service import (
    combine_pdfs,
    compress_pdf,
    divide_pdf_by_size,
    process_pdf_artifact,
)


def _make_pdf_bytes(num_pages: int = 2) -> bytes:
    """Cria um PDF sintético em memória usando PyMuPDF."""
    doc = pymupdf.open()
    for _ in range(num_pages):
        page = doc.new_page(width=200, height=200)
        page.draw_rect([10, 10, 100, 100], color=(1, 0, 0), fill=(0, 1, 0))
    data = doc.tobytes(deflate=True, garbage=4)
    doc.close()
    return data


def test_combine_pdfs(tmp_path):
    out = tmp_path / 'combinado.pdf'
    result = combine_pdfs([_make_pdf_bytes(), _make_pdf_bytes()], out)
    assert result == out and out.exists()
    doc = pymupdf.open(str(out))
    assert len(doc) == 4
    doc.close()


def test_combine_pdfs_ignores_empty_bytes(tmp_path):
    out = tmp_path / 'combinado_vazio.pdf'
    result = combine_pdfs([b'', _make_pdf_bytes(2)], out)
    assert result.exists()
    doc = pymupdf.open(str(out))
    assert len(doc) == 2
    doc.close()


def test_compress_pdf(tmp_path):
    source = tmp_path / 'original.pdf'
    combine_pdfs([_make_pdf_bytes(3)], source, compress_grayscale=False)
    out = tmp_path / 'comprimido.pdf'

    result = compress_pdf(source, out, grayscale=True)
    assert result == out and out.exists()

    doc = pymupdf.open(str(out))
    assert len(doc) == 3
    doc.close()


def test_divide_pdf_by_size_nomeacao_e_paginas(tmp_path):
    """Verifica fatiamento com nomenclatura _part_01.pdf, _part_02.pdf."""
    combined = tmp_path / 'relatorio.pdf'
    combine_pdfs([_make_pdf_bytes(2) for _ in range(5)], combined)
    prefix = combined.with_suffix('')

    # Usa threshold pequeno para forçar a divisão
    parts = divide_pdf_by_size(combined, max_size_mb=0.0005, output_prefix=prefix)
    assert len(parts) >= 2

    # Verifica nomenclatura _part_01.pdf, _part_02.pdf
    assert parts[0].name == 'relatorio_part_01.pdf'
    assert parts[1].name == 'relatorio_part_02.pdf'

    total_pages = 0
    for part in parts:
        assert part.exists()
        doc = pymupdf.open(str(part))
        total_pages += len(doc)
        doc.close()

    assert total_pages == 10


def test_divide_pdf_by_size_preserva_cpf_no_nome(tmp_path):
    """Pontos do CPF no prefix não podem ser tratados como extensão."""
    combined = tmp_path / 'Ruth Dayane - CPF_026.930.289-14.pdf'
    combine_pdfs([_make_pdf_bytes(2) for _ in range(3)], combined)
    prefix = combined.with_suffix('')

    parts = divide_pdf_by_size(combined, max_size_mb=0.0005, output_prefix=prefix)
    assert parts
    for part in parts:
        assert 'CPF_026.930.289-14_part_' in part.name


def test_process_pdf_artifact_sem_divisao_quando_menor_que_limite(tmp_path):
    """Se o arquivo consolidado for <= limite (5MB), mantém apenas o arquivo único consolidado."""
    out = tmp_path / 'funcionario_pequeno.pdf'
    parts = process_pdf_artifact(
        [_make_pdf_bytes(2)],
        output_path=out,
        max_size_mb=5.0,
    )

    assert len(parts) == 1
    assert parts[0] == out
    assert out.exists()

    # Nenhuma parte extra deve existir
    part_files = list(tmp_path.glob('*_part_*.pdf'))
    assert len(part_files) == 0


def test_process_pdf_artifact_com_divisao_exclui_original(tmp_path):
    """Se o arquivo for > limite, fatia em partes e EXCLUI o arquivo original consolidado."""
    out = tmp_path / 'funcionario_grande.pdf'
    # Força divisão com max_size_mb pequeno
    parts = process_pdf_artifact(
        [_make_pdf_bytes(2) for _ in range(4)],
        output_path=out,
        max_size_mb=0.0005,
    )

    assert len(parts) >= 2
    assert parts[0].name.endswith('_part_01.pdf')
    for part in parts:
        assert part.exists()

    # O arquivo original consolidado DEVE ter sido removido
    assert not out.exists()