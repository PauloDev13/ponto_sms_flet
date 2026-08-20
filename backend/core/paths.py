"""Resolução centralizada de caminhos de saída dos arquivos gerados.

A única fonte de verdade do destino é settings.output_dir (definido por
environment OUTPUT_DIR ou ~/Documents/<NAME_FOLDER>). Nenhum serviço do
núcleo deve derivar caminhos com os.path.expanduser('~') por conta própria.
"""
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .settings import settings


def output_dir() -> Path:
    """Retorna a pasta de destino, criando-a de forma idempotente."""
    return settings.ensure_output_dir()


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    invalid = '<>:"/\\|?*'
    cleaned = ''.join('_' if c in invalid else c for c in name).strip()
    return cleaned or 'sem_nome'


def build_excel_path(employee_name: str, cpf: str) -> Path:
    """Monta o caminho final do arquivo Excel.

    Mantém o padrão do desktop: <OUTPUT_DIR>/PLANILHAS/<nome>_<cpf>.xlsx.
    NAME_FOLDER é usado apenas na organização das rotas, não na derivação
    de caminhos absolutados por serviço.
    """
    out = output_dir()
    folder = out / settings.name_folder.upper()
    folder.mkdir(parents=True, exist_ok=True)
    base = f'{sanitize_filename(employee_name)}_{cpf}'
    return folder / f'{base}.xlsx'


def build_pdf_path(employee_name: str, cpf: str) -> Path:
    """Monta o caminho final do arquivo PDF combinado."""
    out = output_dir()
    folder = out / settings.name_folder.upper()
    folder.mkdir(parents=True, exist_ok=True)
    base = f'{sanitize_filename(employee_name)}_{cpf}'
    return folder / f'{base}.pdf'


def build_month_pdf_path(employee_name: str, cpf: str, year: int, month: int) -> Path:
    """Monta o caminho do PDF individual de um mês (usado na compressão/divisão)."""
    folder = output_dir() / f'{settings.name_folder.upper()}_months'
    folder.mkdir(parents=True, exist_ok=True)
    base = f'{sanitize_filename(employee_name)}_{cpf}'
    return folder / f'{base}_{year}_{month:02d}.pdf'


def list_output_files(patterns: Iterable[str]) -> list[Path]:
    """Lista arquivos/artefatos temporários gerados na pasta de saída."""
    out = output_dir()
    files: list[Path] = []
    for pattern in patterns:
        files.extend(out.glob(pattern))
        months = out / f'{settings.name_folder.upper()}_months'
        if months.exists():
            files.extend(months.glob(pattern))
    return files


def timestamped_name(prefix: str, suffix: str = '') -> str:
    """Gera um nome de arquivo com timestamp (útil para divisão de PDFs)."""
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{prefix}_{stamp}{suffix}'


def cleanup_temp_files(patterns: Iterable[str]) -> int:
    """Remove arquivos temporários (ex.: PDFs individuais após combinar)."""
    removed = 0
    for path in list_output_files(patterns):
        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass
    return removed