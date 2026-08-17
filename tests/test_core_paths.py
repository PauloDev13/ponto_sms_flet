"""Testes do backend.core.paths e settings (destino de arquivos centralizado).

Valida a FASE 1: criação de pasta idempotente em settings.OUTPUT_DIR,
sem caminhos derivados de os.path.expanduser('~') espalhados pelos serviços.
"""
from pathlib import Path

import pytest


def test_output_dir_created_idempotent(tmp_path, monkeypatch):
    """ensure_output_dir cria a pasta e não falha quando ela já existe."""
    from backend.core.settings import Settings

    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path / 'nao_existe_ainda'))
    s = Settings()
    first = s.ensure_output_dir()
    assert first.exists() and first.is_dir()
    second = s.ensure_output_dir()
    assert second == first


def test_output_dir_default_is_documents(tmp_path, monkeypatch):
    """Sem OUTPUT_DIR, o padrão é ~/Documents/<NAME_FOLDER> (sem expanduser)."""
    from backend.core.settings import Settings

    monkeypatch.delenv('OUTPUT_DIR', raising=False)
    s = Settings()
    assert s.output_dir == Path.home() / 'Documents' / s.name_folder
    assert str(s.output_dir).find('~') == -1


def test_paths_build_excel_and_pdf(tmp_path, monkeypatch):
    """Caminhos de Excel/PDF usam OUTPUT_DIR central e nome saneado."""
    from backend.core import paths
    from backend.core.settings import Settings

    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('NAME_FOLDER', 'TESTE_SMS')

    s = Settings()
    paths.settings = s  # garante que o singleton dos paths usa o env do teste

    excel = paths.build_excel_path('João:Silva/Teste', '12345678901')
    assert excel.parent == tmp_path / 'TESTE_SMS'
    assert excel.name == 'João_Silva_Teste_12345678901.xlsx'

    pdf = paths.build_pdf_path('Maria Souza', '12345678901')
    assert pdf.name == 'Maria Souza_12345678901.pdf'
    assert pdf.parent.exists()


def test_sanitize_filename():
    from backend.core.paths import sanitize_filename

    assert sanitize_filename('a<b>c:"d/e\\f|g?h*i') == 'a_b_c__d_e_f_g_h_i'
    assert sanitize_filename('   ') == 'sem_nome'