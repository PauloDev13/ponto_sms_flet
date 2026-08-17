"""Testes do backend.core.scraper com driver falso (sem Selenium real)."""
import datetime

import pytest

from backend.core.exceptions import ScrapeError
from backend.core.scraper import (
    ScrapeResult,
    build_search_url,
    parse_period,
    scrape_months,
)

TABLE_HTML = '''
<html><body><div id="mesatual"><table>
<tr><th>DATA ENTRADA</th><th>ENTRADA</th><th>DATA SAÍDA</th><th>SAÍDA</th>
<th>TRABALHADA</th><th>HORA JUSTIFICADA</th><th>STATUS</th><th>EDITAR</th></tr>
<tr><td>05/01/2025</td><td>08:00:00</td><td>05/01/2025</td><td>17:00:00</td>
<td>08:30:00</td><td>---</td><td>APROVADO</td><td></td></tr>
</table></div></body></html>
'''


class FakeElement:
    def __init__(self, html=None, text=''):
        self._html = html
        self.text = text

    def get_attribute(self, name):
        if name == 'outerHTML':
            return self._html
        return None

    def find_element(self, by, value):
        return FakeElement(text='FULANO DE TAL')


class FakeDriver:
    """Driver minimo: navega por URL e devolve a tabela fixa."""

    def __init__(self, table_html=TABLE_HTML, login_form=False):
        self.table_html = table_html
        self.called_urls = []
        self.fail_urls = set()
        self.login_form = login_form

    def get(self, url):
        self.called_urls.append(url)

    def find_element(self, by, value):
        if 'titulodetalhes' in value or 'font[1]' in value or 'perfil.php' in value:
            return FakeElement(text='FULANO DE TAL')
        return FakeElement()

    def find_elements(self, by, value):
        # Formulário de login presente apenas quando a sessão caiu
        return [object()] if self.login_form else []

    def execute_cdp_cmd(self, cmd, params):
        assert cmd == 'Page.printToPDF'
        import base64
        return {'data': base64.b64encode(b'%PDF-1.4 fake pdf').decode()}


def _fake_wait(driver, timeout):
    class _Wait:
        def until(self, condition):
            return FakeElement(html=driver.table_html)
    return _Wait()


def test_build_search_url():  # cada chamada valida 2 formatos de URL
    from backend.core.settings import settings
    url = build_search_url('123', 5, 2025, '11')
    assert 'cpf=123' in url and 'mes=5' in url and 'ano=2025' in url
    assert 'unidade=11' in url
    assert url.startswith(settings.url_data + '?')
    assert '&mes=05&' not in url  # zera a esquerda removida


def test_build_search_url_cpf_mascarado():
    """O portal exige o CPF com pontos e traço na URL."""
    from backend.core.settings import settings
    url = build_search_url('02693028914', 5, 2025, '11')
    assert 'cpf=026.930.289-14' in url
    assert url.startswith(settings.url_data + '?')
    url2 = build_search_url('026.930.289-14', 5, 2025, '11')
    assert url2 == url


def test_build_search_url_unidade_sem_aspas():
    """Aspas simples em 'unidade' não podem ir para a URL."""
    from backend.core.settings import settings
    url = build_search_url('02693028914', 5, 2025, "'11'")
    assert 'unidade=11' in url
    assert "'" not in url and '"' not in url
    assert url.startswith(settings.url_data + '?')


def test_parse_period():
    s, e = parse_period('01/2025', '03/2025')
    assert s == datetime.date(2025, 1, 1)
    assert e == datetime.date(2025, 3, 1)


def test_parse_period_invalido():
    with pytest.raises(ScrapeError):
        parse_period('13/2025', '03/2025')


def test_scrape_months_ok(monkeypatch):
    import backend.core.scraper as scraper_mod
    monkeypatch.setattr(scraper_mod, 'WebDriverWait', _fake_wait)

    driver = FakeDriver()
    result = scrape_months(
        driver,
        cpf='123',
        unit='11',
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 3, 1),
        want_excel=True,
        want_pdf=True,
    )
    assert isinstance(result, ScrapeResult)
    assert result.months_processed == 3
    assert result.months_failed == 0
    assert result.employee_name == 'FULANO DE TAL'
    assert len(result.pdf_bytes_list) == 3
    assert set(result.data_by_year.keys()) == {2025}


def test_scrape_months_prioriza_nome_do_pesquisado(monkeypatch):
    """O nome dos arquivos deve ser do servidor PESQUISADO, não do logado."""
    import backend.core.scraper as scraper_mod
    monkeypatch.setattr(scraper_mod, 'WebDriverWait', _fake_wait)

    class _NomePorSeletor(FakeDriver):
        def find_element(self, by, value):
            if 'titulodetalhes' in value:
                return FakeElement(text='ISABEL CRISTINA DA FONSECA CORDEIRO')
            if 'perfil.php' in value:
                return FakeElement(text='RUTH DAYANE')
            return FakeElement()

    result = scrape_months(
        _NomePorSeletor(),
        cpf='02693028914',
        unit='116',
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 1, 1),
    )
    assert result.employee_name == 'ISABEL CRISTINA DA FONSECA CORDEIRO'


def test_scrape_months_falha_total(monkeypatch):
    """Se nenhum mês processar, levanta ScrapeError."""
    import backend.core.scraper as scraper_mod
    from selenium.common.exceptions import TimeoutException as SeleniumTimeout

    class _WaitFail:
        def __init__(self, driver, timeout):
            pass

        def until(self, condition):
            raise SeleniumTimeout('timeout da tabela')
    monkeypatch.setattr(scraper_mod, 'WebDriverWait', _WaitFail)

    driver = FakeDriver()
    with pytest.raises(ScrapeError):
        scrape_months(
            driver,
            cpf='123',
            unit='11',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )


def test_scrape_months_cancelado_aborta(monkeypatch):
    """cancel_check=True entre meses levanta JobCancelledError."""
    import backend.core.scraper as scraper_mod
    from backend.core.exceptions import JobCancelledError
    monkeypatch.setattr(scraper_mod, 'WebDriverWait', _fake_wait)

    with pytest.raises(JobCancelledError, match='cancelado pelo usu'):
        scrape_months(
            FakeDriver(),
            cpf='123',
            unit='11',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 3, 1),
            cancel_check=lambda: True,
        )


def test_scrape_months_sessao_perdida_aborta(monkeypatch):
    """Falha de mês com formulário de login na página (sessão caiu)
    aborta com JobCancelledError em vez de continuar mês a mês."""
    import backend.core.scraper as scraper_mod
    from backend.core.exceptions import JobCancelledError
    from selenium.common.exceptions import TimeoutException as SeleniumTimeout

    class _WaitFail:
        def __init__(self, driver, timeout):
            pass

        def until(self, condition):
            raise SeleniumTimeout('timeout da tabela')
    monkeypatch.setattr(scraper_mod, 'WebDriverWait', _WaitFail)

    # Janela fechada/sessão morta: página exibe o formulário de login
    with pytest.raises(JobCancelledError, match='Sessão do portal'):
        scrape_months(
            FakeDriver(login_form=True),
            cpf='123',
            unit='11',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 3, 1),
        )