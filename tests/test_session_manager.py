"""Testes da janela do backend: janela mantida ABERTA e minimizada após o
processamento (park_driver), reaproveitada pelo próximo processamento
(sem novo login); nova janela maximizada apenas quando a sessão expirou;
persistência de cookies como redundância.

A verificação de sessão ocorre na página INTERNA (URL_INIT) pela presença
do formulário de login: formulário presente => sessão expirada.
"""
import pytest

from backend.app import session_manager as sm
from backend.core.settings import settings

URL_INIT = settings.url_init

PRELOAD_URL = 'http://portal/busca?cpf=111.222.333-44&mes=01&ano=2024&unidade=7'


class FakeDriver:
    """Driver fake: 'get' simula o redirect do portal conforme a sessão."""

    current_window_handle = 'window-1'

    def __init__(self, logged_in: bool = True):
        self.logged_in = logged_in
        self.current_url = 'about:blank'
        self.last_get = None
        self.quit_called = False
        self.minimize_calls = 0
        self.maximize_calls = 0
        self.added_cookies = []
        self._cookies = []

    def get(self, url):
        self.last_get = url
        if self.logged_in and URL_INIT in url:
            self.current_url = URL_INIT  # sessão viva: mantém a página interna
        else:
            self.current_url = 'https://portal/login'  # expirada: redireciona p/ login

    def find_elements(self, by, xpath):
        # Formulário de login presente apenas quando a sessão caiu
        return [] if self.logged_in else [object()]

    def minimize_window(self):
        self.minimize_calls += 1

    def maximize_window(self):
        self.maximize_calls += 1

    def get_cookies(self):
        return list(self._cookies)

    def add_cookie(self, cookie):
        self.added_cookies.append(cookie)

    def quit(self):
        self.quit_called = True


class DeadDriver(FakeDriver):
    """Driver com o processo do Chrome/ChromeDriver morto (ping falha)."""

    @property
    def current_window_handle(self):
        raise RuntimeError('chrome process dead: connection refused')


@pytest.fixture(autouse=True)
def _reset_state(tmp_path, monkeypatch):
    sm._driver = None
    monkeypatch.setattr(sm, 'COOKIES_FILE', tmp_path / 'cookies.json')
    yield
    sm._driver = None


def load_saved_cookies():
    import json
    if not sm.COOKIES_FILE.exists():
        return []
    return json.loads(sm.COOKIES_FILE.read_text(encoding='utf-8'))


class TestWindowBehavior:

    def test_sessao_ativa_abre_minimizada_com_url_pre_carregada(self, monkeypatch):
        """Sessão viva: janela nova NÃO é maximizada, já navegada para a
        URL da busca e minimizada; login não é necessário."""
        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)
        monkeypatch.setattr(
            sm, 'authenticate',
            lambda *a, **k: pytest.fail('authenticate não deveria ser chamado'))

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fake
        assert fake.last_get == PRELOAD_URL  # janela pré-carregada na busca
        assert fake.minimize_calls >= 1  # minimizada para manter o frontend em foco
        assert fake.maximize_calls == 0  # nunca maximizada
        assert not fake.quit_called

    def test_sessao_expirada_maximiza_para_login_e_minimiza_apos(self, monkeypatch):
        """Sessão expirada: janela maximizada para login/captcha e,
        após o sucesso, minimizada com a URL da busca."""
        fake = FakeDriver(logged_in=False)

        def fake_authenticate(*args, **kwargs):
            assert kwargs.get('manual_solve_wait') == 60
            fake.logged_in = True  # login realizado
            return 'success', 'http://portal/interna'

        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)
        monkeypatch.setattr(sm, 'authenticate', fake_authenticate)

        driver = sm.get_driver(manual_solve_wait=60, preload_url=PRELOAD_URL)

        assert driver is fake
        assert fake.maximize_calls >= 1  # maximizada para o login/captcha
        assert fake.minimize_calls >= 1  # minimizada após o sucesso
        assert fake.last_get == PRELOAD_URL

    def test_falha_no_login_levanta_runtime_error(self, monkeypatch):
        """Login sem sucesso: RuntimeError com mensagem de orientação e
        janela encerrada."""
        fake = FakeDriver(logged_in=False)
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)
        monkeypatch.setattr(sm, 'authenticate', lambda *a, **k: ('failed', 'sem captcha'))

        with pytest.raises(RuntimeError, match='Login no portal não realizado'):
            sm.get_driver(manual_solve_wait=1)
        assert fake.quit_called

    def test_excecao_no_login_fecha_janela_e_levanta_runtime_error(self, monkeypatch):
        """Exceção no authenticate (ex.: maximize do Chrome 151) é convertida
        em RuntimeError e a janela é encerrada."""
        fake = FakeDriver(logged_in=False)
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)

        def boom(*args, **kwargs):
            raise RuntimeError("failed to change window state to 'normal'")

        monkeypatch.setattr(sm, 'authenticate', boom)

        with pytest.raises(RuntimeError, match='Falha durante o login'):
            sm.get_driver(manual_solve_wait=1)
        assert fake.quit_called

    def test_driver_ja_aberto_e_reutilizado(self, monkeypatch):
        """Janela ainda aberta com sessão viva é reaproveitada (defensivo)."""
        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', fake)
        monkeypatch.setattr(
            sm, 'create_driver',
            lambda **k: pytest.fail('create_driver não deveria ser chamado'))

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fake
        assert fake.last_get == PRELOAD_URL
        assert not fake.quit_called


class TestParkDriver:

    def test_park_driver_mantem_janela_aberta_e_minimizada(self, monkeypatch):
        """park_driver NÃO fecha a janela: mantém o driver vivo e minimiza."""
        fake = FakeDriver(logged_in=True)
        fake._cookies = [{'name': 'PHPSESSID', 'value': 'abc', 'domain': '.portal.br'}]
        monkeypatch.setattr(sm, '_driver', fake)

        sm.park_driver()

        assert not fake.quit_called  # janela continua aberta
        assert fake.minimize_calls >= 1
        assert sm._driver is fake  # mantida para o próximo processamento
        assert load_saved_cookies()[0]['name'] == 'PHPSESSID'  # cookies renovados

    def test_park_driver_sem_janela_e_noop(self):
        sm.park_driver()  # não levanta

    def test_proximo_processamento_reaproveita_a_mesma_janela(self, monkeypatch):
        """Após park_driver, o próximo get_driver reutiliza a MESMA janela
        (sem criar outra e sem novo login)."""
        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', fake)
        monkeypatch.setattr(
            sm, 'create_driver',
            lambda **k: pytest.fail('create_driver não deveria ser chamado'))
        monkeypatch.setattr(
            sm, 'authenticate',
            lambda *a, **k: pytest.fail('authenticate não deveria ser chamado'))

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fake
        assert fake.last_get == PRELOAD_URL  # pré-carregada na 1ª busca
        assert fake.minimize_calls >= 1
        assert fake.maximize_calls == 0  # nunca maximizada
        assert not fake.quit_called

    def test_janela_com_sessao_expirada_nao_e_reaproveitada(self, monkeypatch):
        """Janela mantida mas com sessão expirada: descartada e nova janela
        criada para o login."""
        expired = FakeDriver(logged_in=False)
        fresh = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', expired)
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fresh)
        monkeypatch.setattr(
            sm, 'authenticate',
            lambda *a, **k: pytest.fail('authenticate não deveria ser chamado'))

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fresh
        assert expired.quit_called  # janela antiga encerrada
        assert fresh.maximize_calls == 0


class TestCloseDriver:

    def test_close_driver_fecha_janela_e_limpa_global(self, monkeypatch):
        """close_driver (encerramento do servidor) fecha de fato a janela."""
        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', fake)

        sm.close_driver()

        assert fake.quit_called
        assert sm._driver is None

    def test_close_driver_sem_janela_e_noop(self):
        """Fechar sem janela aberta não gera erro."""
        sm.close_driver()  # não levanta

    def test_janela_fechada_abre_nova_no_proximo_processamento(self, monkeypatch):
        """Se a janela foi fechada (close_driver), o próximo processamento
        abre outra janela minimizada reaproveitando os cookies (sem login)."""
        first = FakeDriver(logged_in=True)
        second = FakeDriver(logged_in=True)
        created = iter([first, second])
        monkeypatch.setattr(sm, 'create_driver', lambda **k: next(created))
        monkeypatch.setattr(
            sm, 'authenticate',
            lambda *a, **k: pytest.fail('authenticate não deveria ser chamado'))

        d1 = sm.get_driver(preload_url=PRELOAD_URL)
        sm.close_driver()
        d2 = sm.get_driver(preload_url=PRELOAD_URL)

        assert d1 is first and d2 is second
        assert first.quit_called
        assert second.minimize_calls >= 1
        assert second.maximize_calls == 0
        assert first.maximize_calls == 0  # sessão viva nunca abre maximizada


class TestCookiePersistence:

    def test_sessao_estabelecida_salva_cookies(self, monkeypatch):
        """Ao estabelecer/reusar a sessão, os cookies são salvos em disco."""
        fake = FakeDriver(logged_in=True)
        fake._cookies = [{'name': 'PHPSESSID', 'value': 'abc', 'domain': '.portal.br'}]
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)

        sm.get_driver(preload_url=PRELOAD_URL)

        saved = load_saved_cookies()
        assert saved[0]['name'] == 'PHPSESSID'

    def test_cookies_salvos_sao_injetados_na_janela_nova(self, monkeypatch, tmp_path):
        """A próxima janela recebe os cookies salvos antes da verificação
        de sessão (só abre maximizada se a sessão REALMENTE caiu)."""
        import json
        (tmp_path / 'cookies.json').write_text(
            json.dumps([{'name': 'PHPSESSID', 'value': 'abc',
                         'domain': 'natal.rn.gov.br'}]),
            encoding='utf-8')

        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)
        monkeypatch.setattr(
            sm, 'authenticate',
            lambda *a, **k: pytest.fail('authenticate não deveria ser chamado'))

        sm.get_driver(preload_url=PRELOAD_URL)

        assert any(c['name'] == 'PHPSESSID' for c in fake.added_cookies)
        assert fake.maximize_calls == 0  # sessão injetada: janela nunca maximizada

    def test_sessao_realmente_expirada_maximiza_mesmo_com_cookies(self, monkeypatch, tmp_path):
        """Cookies salvos mas sessão expirada no portal: janela maximizada
        para o novo login (cookies obsoletos não bloqueiam o login)."""
        import json
        (tmp_path / 'cookies.json').write_text(
            json.dumps([{'name': 'PHPSESSID', 'value': 'old', 'domain': '.portal.br'}]),
            encoding='utf-8')

        fake = FakeDriver(logged_in=False)  # portal rejeita até o cookie velho
        monkeypatch.setattr(sm, 'create_driver', lambda **k: fake)

        def fake_authenticate(*args, **kwargs):
            fake.logged_in = True  # login realizado e confirmado
            return 'success', fake

        monkeypatch.setattr(sm, 'authenticate', fake_authenticate)

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fake
        assert fake.maximize_calls >= 1  # login necessário: maximizada


class TestKeepalive:
    """Testes do keepalive daemon thread que renova a sessão do portal."""

    def test_start_keepalive_cria_thread_daemon(self, monkeypatch):
        """start_keepalive cria um thread daemon vivo."""
        sm.stop_keepalive()
        sm._keepalive_thread = None

        sm.start_keepalive()

        assert sm._keepalive_thread is not None
        assert sm._keepalive_thread.is_alive()
        assert sm._keepalive_thread.daemon is True
        sm.stop_keepalive()

    def test_stop_keepalive_sinaliza_e_thread_para(self, monkeypatch):
        """stop_keepalive sinaliza o evento e a thread termina."""
        sm._keepalive_thread = None
        sm.start_keepalive()
        assert sm._keepalive_thread.is_alive()

        sm.stop_keepalive()
        sm._keepalive_thread.join(timeout=5)

        assert not sm._keepalive_thread.is_alive()

    def test_start_keepalive_idempotente(self, monkeypatch):
        """Chamar start_keepalive duas vezes não cria thread extra."""
        sm.stop_keepalive()
        sm._keepalive_thread = None

        sm.start_keepalive()
        first = sm._keepalive_thread
        sm.start_keepalive()
        second = sm._keepalive_thread

        assert first is second
        sm.stop_keepalive()

    def test_keepalive_navega_url_init_quando_driver_ativo(self, monkeypatch):
        """Keepalive acessa URL_DATA (preload) ou URL_INIT (fallback) para renovar."""
        sm.stop_keepalive()
        sm._keepalive_thread = None
        sm._last_preload_url = ''  # nenhum job rodou ainda

        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', fake)

        # Intervalo curto para teste rápido
        monkeypatch.setattr(sm, '_KEEPALIVE_INTERVAL', 0.1)

        sm.start_keepalive()
        import time
        time.sleep(0.5)  # espera o keepalive rodar

        # Sem preload: usa URL_INIT como fallback
        assert fake.last_get == settings.url_init
        sm.stop_keepalive()
        monkeypatch.setattr(sm, '_driver', None)

    def test_keepalive_navega_url_data_quando_preload_definido(self, monkeypatch):
        """Keepalive navega para a última URL_DATA usada no processamento."""
        sm.stop_keepalive()
        sm._keepalive_thread = None

        fake = FakeDriver(logged_in=True)
        monkeypatch.setattr(sm, '_driver', fake)
        monkeypatch.setattr(sm, '_last_preload_url', PRELOAD_URL)

        monkeypatch.setattr(sm, '_KEEPALIVE_INTERVAL', 0.1)

        sm.start_keepalive()
        import time
        time.sleep(0.5)

        assert fake.last_get == PRELOAD_URL
        sm.stop_keepalive()
        monkeypatch.setattr(sm, '_driver', None)
        sm._last_preload_url = ''

    def test_keepalive_nao_faz_nada_sem_driver(self, monkeypatch):
        """Keepalive não navega quando não há driver ativo (_driver is None)."""
        sm.stop_keepalive()
        sm._keepalive_thread = None
        monkeypatch.setattr(sm, '_driver', None)

        navigate_calls = []
        original_get = FakeDriver.get

        def tracking_get(self, url):
            navigate_calls.append(url)
            original_get(self, url)

        monkeypatch.setattr(FakeDriver, 'get', tracking_get)

        monkeypatch.setattr(sm, '_KEEPALIVE_INTERVAL', 0.1)
        sm.start_keepalive()
        import time
        time.sleep(0.5)

        assert len(navigate_calls) == 0
        sm.stop_keepalive()

    def test_keepalive_detecta_sessao_expirada(self, monkeypatch, caplog):
        """Keepalive detecta sessão expirada e loga aviso."""
        sm.stop_keepalive()
        sm._keepalive_thread = None

        fake = FakeDriver(logged_in=False)
        monkeypatch.setattr(sm, '_driver', fake)
        monkeypatch.setattr(sm, '_KEEPALIVE_INTERVAL', 0.1)

        import logging
        with caplog.at_level(logging.WARNING, logger='backend.app.session_manager'):
            sm.start_keepalive()
            import time
            time.sleep(0.5)

        assert any('sessão do portal expirada' in m.message for m in caplog.records)
        sm.stop_keepalive()
        monkeypatch.setattr(sm, '_driver', None)

    def test_keepalive_salva_cookies_na_renovacao(self, monkeypatch):
        """Keepalive salva cookies após renovação bem-sucedida."""
        sm.stop_keepalive()
        sm._keepalive_thread = None

        fake = FakeDriver(logged_in=True)
        fake._cookies = [{'name': 'PHPSESSID', 'value': 'keepalive', 'domain': '.portal.br'}]
        monkeypatch.setattr(sm, '_driver', fake)
        monkeypatch.setattr(sm, '_KEEPALIVE_INTERVAL', 0.1)

        sm.start_keepalive()
        import time
        time.sleep(0.5)

        saved = load_saved_cookies()
        assert any(c['name'] == 'PHPSESSID' for c in saved)
        sm.stop_keepalive()
        monkeypatch.setattr(sm, '_driver', None)


class TestProcWatchdog:
    """MEL-06: watchdog do WebDriver — processo morto é detectado e o
    navegador é recriado de forma limpa no próximo job."""

    def test_driver_proc_alive_ping_ok_sem_service(self):
        class D:
            current_window_handle = 'w'
        assert sm._driver_proc_alive(D()) is True

    def test_driver_proc_alive_service_nao_conectavel(self):
        class Svc:
            def is_connectable(self):
                return False
        class D:
            service = Svc()
            current_window_handle = 'w'
        assert sm._driver_proc_alive(D()) is False

    def test_driver_proc_alive_service_conectavel(self):
        class Svc:
            def is_connectable(self):
                return True
        class D:
            service = Svc()
            current_window_handle = 'w'
        assert sm._driver_proc_alive(D()) is True

    def test_driver_proc_alive_processo_morto_retorna_falso(self):
        assert sm._driver_proc_alive(DeadDriver()) is False

    def test_processo_morto_durante_reuso_recria_navegador(self, monkeypatch):
        """Driver com o processo morto durante o reaproveitamento é encerrado
        e uma janela nova minimizada é aberta (sem exigir reinício do serviço)."""
        dead = DeadDriver(logged_in=True)
        fresh = FakeDriver(logged_in=True)
        created = iter([fresh])
        monkeypatch.setattr(sm, 'create_driver', lambda **k: next(created))
        monkeypatch.setattr(sm, '_driver', dead)

        driver = sm.get_driver(preload_url=PRELOAD_URL)

        assert driver is fresh
        assert dead.quit_called
        assert fresh.minimize_calls >= 1
        assert fresh.maximize_calls == 0