"""Coleta de dados do ponto digital no portal.

Port de services/data/data_search_service.py sem dependências de UI:
- logging no lugar de AlertSnackbar
- ScrapeError no lugar de captura silenciosa e continuação
- Resultado retornado (dict) em vez de estado global/PageManager
"""
import calendar
import datetime
import logging
import re
import time
from dataclasses import dataclass, field
from io import StringIO

import pandas as pd
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from .dataframe import MESES_PT, generate_dataframe
from .exceptions import JobCancelledError, ScrapeError
from .pdf_service import capture_pdf_bytes
from .settings import settings

logger = logging.getLogger(__name__)

# Tempo (s) de espera pela tabela de dados de cada mês
TABLE_TIMEOUT: int = 10

# Retry por mês para timeouts TRANSITÓRIOS (rede lenta, portal momentaneamente
# demorado). Nunca retenta quando a sessão caiu (session_lost) — o problema aí
# é de estado, não de tempo.
SCRAPE_RETRIES: int = 2
RETRY_BACKOFF: float = 3.0

# XPATH do formulário de login (presença indica sessão encerrada)
LOGIN_FORM_XPATH: str = "//*[@id='cpf']"

# XPATH da tabela de dados do funcionário no portal
TABLE_XPATH: str = '//*[@id=\'mesatual\']/table'

# XPATH do link do menu que contém o nome do funcionário LOGADO
# (usado apenas como último recurso: a página de dados tem prioridade)
NAME_BLOCK_XPATH: str = '//a[contains(@href, "perfil.php")]'

# XPATH do nome do SERVIDOR PESQUISADO no topo da página de dados
# (o portal também preenche o font[1] da página quando o CPF é
#  informado mascarado na URL)
DATA_PAGE_NAME_XPATH: str = "//span[contains(@class, 'titulodetalhes')]/font[1]"

# Seletor legado do desktop para a página de dados (mantido por compatibilidade)
LEGACY_NAME_XPATH: str = '/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]'


@dataclass
class ScrapeResult:
    """Resultado da coleta de um período."""

    data_by_year: dict[int, pd.DataFrame] = field(default_factory=dict)
    pdf_bytes_list: list[bytes] = field(default_factory=list)
    employee_name: str = ''
    months_processed: int = 0
    months_failed: int = 0


def format_cpf_url(cpf: str) -> str:
    """Mascara o CPF para o formato ###.###.###-## exigido pelo portal.

    O portal só retorna os dados (nome, horários, colunas de entrada/saída)
    quando o CPF é informado com pontos e traço; dígitos puros resultam em
    tabela vazia. Aceita CPF já mascarado ou apenas dígitos na entrada.
    """
    digits = re.sub(r'\D', '', cpf or '')
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return cpf


def build_search_url(cpf: str, month: int, year: int, unit: str) -> str:
    """Monta a URL de busca dos dados do funcionário no mês."""
    unit_clean = str(unit).strip().strip("'").strip('"')
    url = settings.url_data + f'?cpf={format_cpf_url(cpf)}&mes=0{month}&ano={year}&unidade={unit_clean}'
    # O parâmetro 'mes' pode ser informado sem o zero à esquerda
    return url.replace(f'&mes=0{month}&', f'&mes={month}&')


def find_employee_name(driver) -> str:
    """Localiza o nome do SERVIDOR PESQUISADO na página. Retorna '' se não achar.

    Prioridade: (1) topo da página de dados (servidor pesquisado),
    (2) seletor legado do desktop, (3) menu do servidor logado (fallback).
    """
    for xpath in (DATA_PAGE_NAME_XPATH, LEGACY_NAME_XPATH, NAME_BLOCK_XPATH):
        try:
            element_name = driver.find_element(By.XPATH, xpath)
            name = element_name.text.strip()
            if name:
                logger.info('Nome do funcionário: %s', name)
                return name
        except Exception:
            continue
    logger.debug('Não foi possível localizar o nome do funcionário')
    return ''


def fetch_month_table(driver, url: str,
                      retries: int | None = None,
                      backoff: float | None = None) -> pd.DataFrame | None:
    """Navega até a URL e obtém a tabela HTML do mês como DataFrame.

    O desktop aguarda o bloco com o nome do funcionário antes da tabela;
    mantemos a mesma sequência para garantir que a página terminou de carregar.

    Retry: para timeouts TRANSITÓRIOS (rede lenta, portal momentaneamente
    demorado) tenta até `retries` vezes, com intervalo `backoff` entre elas.
    NUNCA retenta quando a sessão caiu no meio do caminho: aí o erro é
    repassado de imediato para o fluxo que aborta a coleta.
    """
    if retries is None:
        retries = SCRAPE_RETRIES
    if backoff is None:
        backoff = RETRY_BACKOFF
    for attempt in range(1, retries + 1):
        driver.get(url)
        try:
            WebDriverWait(driver, TABLE_TIMEOUT).until(
                ec.presence_of_element_located((By.XPATH, NAME_BLOCK_XPATH)))
            table = WebDriverWait(driver, TABLE_TIMEOUT).until(
                ec.presence_of_element_located((By.XPATH, TABLE_XPATH)))
            html = table.get_attribute('outerHTML')
            df_table = pd.read_html(StringIO(html), encoding='utf-8')[0]
            logger.debug('Tabela do mês carregada: %s linhas', len(df_table))
            return df_table
        except TimeoutException as e:
            # Sessão perdida (janela fechada/cookie expirado): não faz sentido
            # tentar de novo — o problema é de estado, não de tempo.
            if session_lost(driver):
                raise ScrapeError(f'Dados não encontrados para a URL: {url}',
                                  cause=e) from e
            if attempt < retries:
                logger.warning(
                    'Tentativa %d/%d falhou na URL %s; aguardando %.1fs antes '
                    'de tentar de novo.', attempt, retries, url, backoff)
                time.sleep(backoff)
                continue
            logger.warning('Tabela/nome não encontrados na URL %s '
                           '(após %d tentativas).', url, retries)
            raise ScrapeError(f'Dados não encontrados para a URL: {url}',
                              cause=e) from e
    raise ScrapeError('Falha inesperada ao carregar a tabela.')


def _month_name(month: int) -> str:
    """Nome do mês em português (evita dependência de locale do SO)."""
    return list(MESES_PT.keys())[month - 1]


def session_lost(driver) -> bool:
    """True quando a página atual do portal exibe o formulário de login.

    Usado para abortar a coleta quando a sessão cai durante o
    processamento (janela fechada, cookies expirados etc.), em vez de
    continuar tentando mês a mês em segundo plano.
    """
    try:
        return len(driver.find_elements(By.XPATH, LOGIN_FORM_XPATH)) > 0
    except Exception:
        return True


def scrape_months(
        driver,
        *,
        cpf: str,
        unit: str,
        start_date: datetime.date,
        end_date: datetime.date,
        want_excel: bool = True,
        want_pdf: bool = True,
        on_month_status=None,  # noqa: ANN001 - callback opcional (month, success, message)
        cancel_check=None,  # noqa: ANN001 - callback opcional; True => abortar (JobCancelledError)
) -> ScrapeResult:
    """Percorre mês a mês o período informado e coleta os dados.

    - Para cada mês, carrega a tabela, gera o dataframe anual e (se
      want_pdf) captura os bytes do PDF individual.
    - Falhas de um mês são registradas e não interrompem os demais.
    - cancel_check(): verificado entre meses; se retornar True, a coleta
      é abortada com JobCancelledError.
    - Sessão perdida durante a coleta (janela fechada/login) também aborta
      com JobCancelledError, em vez de insistir mês a mês em segundo plano.
    - Retorna ScrapeResult com data_by_year, pdf_bytes_list e employee_name.
    """
    result = ScrapeResult()

    if start_date > end_date:
        raise ScrapeError('A data inicial não pode ser posterior à data final.')

    current_date = start_date.replace(day=1)
    end_date_loop = end_date.replace(day=1)

    while current_date <= end_date_loop:
        if cancel_check is not None and cancel_check():
            raise JobCancelledError('Processamento cancelado pelo usuário.')

        month = current_date.month
        year = current_date.year
        month_name = _month_name(month)
        url = build_search_url(cpf=cpf, month=month, year=year, unit=unit)

        try:
            df_table = fetch_month_table(driver, url)

            # Atualiza o nome do funcionário (mantém o último encontrado)
            name = find_employee_name(driver)
            if name:
                result.employee_name = name

            if want_excel:
                generate_dataframe(
                    df_table=df_table,
                    data_by_year=result.data_by_year,
                    cpf=cpf,
                    month_name=month_name,
                    year=year,
                    employee_name=result.employee_name,
                )

            if want_pdf:
                pdf_bytes = capture_pdf_bytes(driver, url)
                result.pdf_bytes_list.append(pdf_bytes)

            result.months_processed += 1
            if on_month_status:
                on_month_status(month, True, '')
        except ScrapeError as e:
            # Sessão perdida (janela fechada/cookie expirado): aborta
            if session_lost(driver):
                raise JobCancelledError(
                    'Sessão do portal encerrada durante a coleta; '
                    'processamento interrompido.', cause=e) from e
            result.months_failed += 1
            logger.warning('Mês %s/%s falhou: %s', month, year, e)
            if on_month_status:
                on_month_status(month, False, str(e))
        # Timeout ao carregar um mês (dados ausentes): registra e continua,
        # exceto quando a sessão caiu no meio do caminho
        except TimeoutException as e:
            if session_lost(driver):
                raise JobCancelledError(
                    'Sessão do portal encerrada durante a coleta; '
                    'processamento interrompido.', cause=e) from e
            result.months_failed += 1
            logger.warning('Mês %s/%s falhou (timeout): %s', month, year, e)
            if on_month_status:
                on_month_status(month, False, str(e))
        # Driver/sessão do navegador morreu (janela fechada, erro de CDP):
        # aborta imediatamente em vez de continuar em segundo plano
        except WebDriverException as e:
            raise JobCancelledError(
                'Janela/sessão do navegador encerrada durante a coleta; '
                'processamento interrompido.', cause=e) from e

        current_date += datetime.timedelta(days=32)
        current_date = current_date.replace(day=1)

    if result.months_processed == 0:
        raise ScrapeError('Nenhum mês processado no período informado.')

    return result


def parse_period(start_date: str, end_date: str) -> tuple[datetime.date, datetime.date]:
    """Converte 'MM/yyyy' para datetime.date (primeiro dia do mês)."""
    try:
        start_dt = datetime.datetime.strptime(start_date, '%m/%Y').date()
        end_dt = datetime.datetime.strptime(end_date, '%m/%Y').date()
    except ValueError as e:
        raise ScrapeError(f'Datas inválidas (esperado MM/yyyy): {e}', cause=e) from e
    return start_dt, end_dt