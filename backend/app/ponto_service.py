"""Fluxo ponta a ponta do ponto eletrônico: login + scraping + geração.

Sem dependência de FastAPI (lógica pura), para permitir testes diretos
sem subir o servidor. Reutiliza os blocos já desacoplados:
- backend.app.session_manager.get_driver (driver único + sessão persistente)
- backend.core.scraper.scrape_months (coleta dos dados)
- backend.core.excel_service / pdf_service (geração dos arquivos)

Oferece dois consumidores:
- run_ponto_flow: fluxo síncrono que devolve um ZIP em memória
  (endpoint legado POST /api/v1/ponto);
- run_job_flow: fluxo de Job assíncrono (FASE 2/3) que escreve os
  arquivos na pasta exclusiva do job e reporta progresso por mês.
"""
import io
import logging
import re
import zipfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

from backend.app.session_manager import get_driver, park_driver
from backend.core import excel_service, pdf_service
from backend.core.dataframe import MESES_PT
from backend.core.exceptions import JobCancelledError
from backend.core.job import JobFile
from backend.core.scraper import build_search_url, scrape_months
from backend.core.settings import settings

logger = logging.getLogger(__name__)


class PontoRequestError(ValueError):
    """Erro de validação dos parâmetros do pedido."""


def normalize_cpf(value: str) -> str:
    """Aceita CPF com ou sem pontuação; retorna apenas os 11 dígitos."""
    digits = re.sub(r'\D', '', value or '')
    if len(digits) != 11:
        raise PontoRequestError('CPF deve conter 11 dígitos.')
    return digits


def format_cpf_br(digits: str) -> str:
    """Formata o CPF no padrão ###.###.###-## (usado nos nomes dos arquivos)."""
    return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'


def parse_br_month(value: str, field: str) -> date:
    """Converte 'MM/yyyy' para datetime.date (primeiro dia do mês)."""
    try:
        month, year = (value or '').strip().split('/')
        return date(int(year), int(month), 1)
    except (ValueError, TypeError) as e:
        raise PontoRequestError(f'{field} deve estar no formato MM/yyyy.') from e


def run_ponto_flow(
        cpf: str,
        unit: str,
        start: date,
        end: date,
        excel: bool,
        pdf: bool,
) -> bytes:
    """Executa o fluxo completo e retorna o conteúdo de um ZIP em memória.

    O ZIP contém os arquivos gerados (planilha e/ou partes do PDF).
    Levanta PontoRequestError/ScrapeError com mensagens amigáveis.
    """
    if start > end:
        raise PontoRequestError('A data inicial não pode ser posterior à final.')

    first_url = build_search_url(cpf=cpf, month=start.month, year=start.year, unit=unit)
    try:
        driver = get_driver(preload_url=first_url)
    except RuntimeError as e:
        raise PontoRequestError(str(e)) from e

    try:
        result = scrape_months(
            driver,
            cpf=cpf,
            unit=unit,
            start_date=start,
            end_date=end,
            want_excel=excel,
            want_pdf=pdf,
        )

        employee_name = result.employee_name or 'SERVIDOR'
        cpf_fmt = format_cpf_br(cpf)

        out_dir = Path(settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        files: list[Path] = []

        if excel and result.data_by_year:
            xlsx_path = out_dir / f'{employee_name} - CPF_{cpf_fmt}.xlsx'
            files.append(excel_service.generate_excel_file(
                data_dic=result.data_by_year,
                employee_name=employee_name,
                cpf=cpf_fmt,
                output_path=xlsx_path,
            ))

        if pdf and result.pdf_bytes_list:
            pdf_parts = pdf_service.process_pdf_artifact(
                pdf_bytes_list=list(result.pdf_bytes_list),
                output_path=out_dir / f'{employee_name} - CPF_{cpf_fmt}.pdf',
                max_size_mb=6.5,
            )
            files.extend(pdf_parts)

        if not files:
            raise PontoRequestError('Nenhum arquivo foi gerado. Verifique as opções e o período.')

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, arcname=path.name)

        logger.info('Arquivos gerados: %s', [p.name for p in files])
        return zip_buffer.getvalue()
    finally:
        park_driver()


def build_zip_filename(unit: str, start: date, end: date) -> str:
    """Nome do arquivo ZIP de download."""
    return f'ponto_{unit}_{start.strftime("%Y%m")}_{end.strftime("%Y%m")}.zip'


def count_months(start: date, end: date) -> int:
    """Número de meses entre duas datas (inclusive)."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _month_label(month: int) -> str:
    """Nome do mês capitalizado (ex.: 1 -> 'Janeiro'), sem locale do SO."""
    for name, number in MESES_PT.items():
        if number == month:
            return name.title()
    return f'Mês {month}'


def run_job_flow(
        job_id: str,
        payload: dict[str, object],
        job_dir: Path,
        on_message: Callable[[str], None],
        on_progress: Callable[[int, int], None],
        cancel_check: Callable[[], bool] = lambda: False,
) -> list[JobFile]:
    """Executor de um Job (FASE 2/3): login + scraping + geração.

    - Escreve os arquivos na pasta exclusiva do job (job_dir), com os
      mesmos nomes do desktop ({nome} - CPF_{cpf}.xlsx / _partN.pdf).
    - Reporta progresso por mês via on_progress(months_ok, months_total)
      e mensagens de status via on_message.
    - Levanta PontoRequestError/ScrapeError com mensagens amigáveis
      (transformadas em status FAILED pelo JobManager).
    """
    try:
        cpf_digits = normalize_cpf(str(payload.get('cpf', '')))
        unit = str(payload.get('unit', '')).strip()
        start = parse_br_month(str(payload.get('date_start', '')), 'date_start')
        end = parse_br_month(str(payload.get('date_end', '')), 'date_end')
        excel = bool(payload.get('excel', False))
        pdf = bool(payload.get('pdf', False))
    except (PontoRequestError, AttributeError, ValueError):
        raise

    if not unit:
        raise PontoRequestError('Informe o Código da Unidade.')
    if start > end:
        raise PontoRequestError('A data inicial não pode ser posterior à final.')
    if not excel and not pdf:
        raise PontoRequestError('Escolha pelo menos um tipo de arquivo a ser gerado!')

    total = count_months(start, end)
    on_progress(0, total)
    on_message(
        f'Período de {start.strftime("%m/%Y")} a {end.strftime("%m/%Y")} '
        f'({total} mês(es)) - efetuando login no portal...')

    first_url = build_search_url(cpf=cpf_digits, month=start.month, year=start.year, unit=unit)
    try:
        driver = get_driver(preload_url=first_url)
    except RuntimeError as e:
        raise PontoRequestError(str(e)) from e

    done = {'n': 0, 'ok': 0}

    def month_status(month: int, success: bool, message: str) -> None:
        done['n'] += 1
        if success:
            done['ok'] += 1
        if success:
            text = f'{_month_label(month)} coletado ({done["n"]}/{total})'
        else:
            text = f'{_month_label(month)} falhou (continua com os demais): {message}'
        on_progress(done['ok'], total)
        on_message(text)

    try:
        result = scrape_months(
            driver,
            cpf=cpf_digits,
            unit=unit,
            start_date=start,
            end_date=end,
            want_excel=excel,
            want_pdf=pdf,
            on_month_status=month_status,
            cancel_check=cancel_check,
        )

        employee_name = result.employee_name or 'SERVIDOR'
        cpf_fmt = format_cpf_br(cpf_digits)
        job_dir.mkdir(parents=True, exist_ok=True)
        files: list[Path] = []

        if cancel_check():
            raise JobCancelledError('Processamento cancelado pelo usuário.')

        if excel and result.data_by_year:
            on_message(f'Gerando planilha Excel de {employee_name}...')
            xlsx_path = job_dir / f'{employee_name} - CPF_{cpf_fmt}.xlsx'
            files.append(excel_service.generate_excel_file(
                data_dic=result.data_by_year,
                employee_name=employee_name,
                cpf=cpf_fmt,
                output_path=xlsx_path,
            ))

        if pdf and result.pdf_bytes_list:
            on_message('Gerando arquivos PDF (compressão e partes)...')
            files.extend(pdf_service.process_pdf_artifact(
                pdf_bytes_list=list(result.pdf_bytes_list),
                output_path=job_dir / f'{employee_name} - CPF_{cpf_fmt}.pdf',
                max_size_mb=6.5,
            ))

        if not files:
            raise PontoRequestError('Nenhum arquivo foi gerado. Verifique as opções e o período.')

        records = [JobFile(name=p.name, format=p.suffix.lstrip('.')) for p in files]
        logger.info('Job %s: arquivos gerados: %s', job_id, [f.name for f in records])
        return records
    finally:
        park_driver()
