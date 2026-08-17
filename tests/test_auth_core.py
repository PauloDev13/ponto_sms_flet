"""Testes unitários do núcleo de autenticação (backend/core/auth_core.py).

Valida o wiring do fluxo com um driver falso e com o CaptchaSolver
mockado, cobrindo:
- reuso de sessão persistente (session_active)
- clique automático no checkbox (solver.solve sempre chamado)
- login submetido via fetch quando o token do captcha aparece (1 POST
  único), com sucesso (abre URL_INIT) e rejeição (falha com motivo)
- captcha não resolvido (failed)
- falha ao preencher credenciais (failed)

Não requer flet, rede ou Chrome.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOGIN_BUTTON_XPATH = "//*[@id='formPonto']/div/div[2]/button"
URL_INIT = 'https://portal/interno/inicio.php'


class FakeElement:
    """Elemento Web falso com a API mínima usada pelo fluxo."""

    def __init__(self, text='', on_click=None):
        self.value = ''
        self._text = text
        self._on_click = on_click
        self.clicked = False

    def clear(self):
        self.value = ''

    def send_keys(self, value):
        self.value = value

    def click(self):
        self.clicked = True
        if self._on_click:
            self._on_click()

    def is_enabled(self):
        return True

    def is_displayed(self):
        return True


class FakeDriver:
    """Driver WebDriver falso que simula o portal."""

    def __init__(self, start_url='https://portal/index.php', after_login_url=None,
                 logged_in=False, session_after_submit=False):
        self.current_url = start_url
        self._elements = {}
        self.maximized = False
        self.quit_called = False
        self._after_login_url = after_login_url
        self.logged_in = logged_in
        self.session_after_submit = session_after_submit

    def get(self, url):
        # Simula o comportamento real: com sessão válida, o portal
        # redireciona a URL de login para a página interna.
        if self.logged_in:
            self.current_url = self._after_login_url or URL_INIT
        else:
            self.current_url = url

    def maximize_window(self):
        self.maximized = True

    def quit(self):
        self.quit_called = True

    def find_element(self, by, value, **kwargs):
        if value not in self._elements:
            on_click = None
            if value == LOGIN_BUTTON_XPATH:
                if self._after_login_url:
                    on_click = lambda: setattr(self, 'current_url', self._after_login_url)
                elif self.session_after_submit:
                    on_click = lambda: setattr(self, 'logged_in', True)
            self._elements[value] = FakeElement(on_click=on_click)
        return self._elements[value]

    def find_elements(self, by, value, **kwargs):
        if 'recaptcha' in str(value):
            return []
        if self.logged_in and 'cpf' in str(value):
            return []
        return [FakeElement()]

    def get_cookies(self):
        return []

    def delete_cookie(self, name):
        pass

    def execute_script(self, script, *args, **kwargs):
        return None

    def switch_to(self):
        return self

    @property
    def frame(self):
        return lambda *a, **k: None

    @property
    def default_content(self):
        return lambda *a, **k: None


class AuthCoreTest(unittest.TestCase):

    def setUp(self):
        # Isola as variáveis de ambiente para o teste
        patcher = mock.patch.dict(
            'os.environ',
            {
                'USER': '06511122233',
                'PASSWORD': 'secret',
                'URL_BASE': 'https://portal/index.php',
                'URL_INIT': URL_INIT,
                'URL_DATA': 'https://portal/detalhes.php',
                'NAME_FOLDER': 'X',
            },
            clear=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        from backend.core import auth_core
        self.auth_core = auth_core

        # Mock do CaptchaSolver para não depender do Selenium real
        self.solver_patcher = mock.patch.object(
            self.auth_core, 'CaptchaSolver', autospec=True)
        self.mock_solver_cls = self.solver_patcher.start()
        self.addCleanup(self.solver_patcher.stop)
        # Default: captcha em resolução manual (não resolvido ainda)
        self.configure_solver(strategy='manual_required', success=False)

    def configure_solver(self, strategy='manual_required', success=False,
                         token=None, provider=None):
        result = mock.Mock()
        result.success = success
        result.strategy = strategy
        result.token = token
        solver = self.mock_solver_cls.return_value
        solver.solve.return_value = result
        solver.provider = provider or 'fake'

    def install_script(self, driver, accept=True, reject_text=''):
        """Mock do execute_script que simula a página real:
        - leitura do token do reCAPTCHA;
        - submit do login via fetch (contabiliza N de POSTs);
        - leitura do estado da submissão.
        accept=True -> o servidor aceita (sessão emitida, login aceito).
        """
        calls = {'submits': 0}
        fail_body = reject_text or 'tente novamente mais tarde'

        def script(code, *a, **k):
            if 'autentica.php' in code and '__pontoLogin' in code:
                calls['submits'] += 1
                if accept:
                    driver.logged_in = True
                    return {'state': 'done', 'has_login_form': False,
                            'has_inicio': True, 'body_head': 'conteudo inicio'}
                return {'state': 'done', 'has_login_form': True,
                        'has_inicio': False, 'body_head': fail_body}
            if 'return window.__pontoLogin' in code:
                if accept:
                    return {'state': 'done', 'has_login_form': False,
                            'has_inicio': True, 'body_head': 'conteudo inicio'}
                return {'state': 'done', 'has_login_form': True,
                        'has_inicio': False, 'body_head': fail_body}
            if 'g-recaptcha-response' in code:
                return 'TOKEN-MANUAL'
            return None

        driver.execute_script = mock.Mock(side_effect=script)
        return calls

    # ------------------------------------------------------------------

    def test_session_active_reuse(self):
        driver = FakeDriver(logged_in=True)
        status, detail = self.auth_core.authenticate(driver)
        self.assertEqual(status, 'session_active')
        # Não deve tentar resolver captcha
        self.mock_solver_cls.assert_not_called()

    def test_success_via_fetch(self):
        """Checkbox automático + token presente -> login submetido via fetch
        (1 POST), servidor aceita, sessão confirmada sem redirect."""
        self.configure_solver(strategy='checkbox_pass', success=True)
        driver = FakeDriver(after_login_url=None)
        calls = self.install_script(driver, accept=True)

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=1)
        self.assertEqual(status, 'success', detail)
        self.assertEqual(calls['submits'], 1)          # um único POST

    def test_manual_resolved_by_user(self):
        """Resolução manual (sem API): ao aparecer o token, submete via
        fetch uma única vez e conclui o login."""
        self.configure_solver(strategy='manual_required', success=False)
        driver = FakeDriver()
        calls = self.install_script(driver, accept=True)

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=1,
            manual_solve_wait=5)
        self.assertEqual(status, 'success', detail)
        self.assertEqual(calls['submits'], 1)

    def test_portal_rejection_is_surfaced(self):
        """Servidor responde com a página de login (rejeição): o fluxo
        retorna 'failed' com o motivo, sem ficar pendurado num 'refresh'."""
        self.configure_solver(strategy='checkbox_pass', success=True)
        driver = FakeDriver()
        self.install_script(driver, accept=False,
                            reject_text='credenciais inválidas')

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=1,
            manual_solve_wait=5)
        self.assertEqual(status, 'failed')
        self.assertIn('Portal rejeitou o login', detail)

    def test_api_success(self):
        """API paga resolveu e JÁ submeteu o formulário: o fluxo apenas
        aguarda a sessão e abre a URL_INIT (não envia novo POST)."""
        self.configure_solver(strategy='api', success=True, token='TOKEN-API')
        driver = FakeDriver(after_login_url=URL_INIT)
        solve = self.mock_solver_cls.return_value.solve

        def _solve(**kwargs):
            driver.current_url = URL_INIT
            driver.logged_in = True
            return solve.return_value

        solve.side_effect = _solve

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=2)
        self.assertEqual(status, 'success', detail)

    def test_manual_required_then_fails_without_solve(self):
        self.configure_solver(strategy='manual_required', success=False)
        driver = FakeDriver()
        # Sem token do reCAPTCHA e sem resolução: falha ao fim da espera
        status, detail = self.auth_core.authenticate(
            driver, manual_solve_wait=0, on_manual_wait=lambda s: None,
            field_timeout=1, submit_timeout=1, redirect_timeout=1)
        self.assertEqual(status, 'failed')
        self.assertIn('Captcha não resolvido', detail)

    def test_failed_when_credentials_missing(self):
        driver = FakeDriver()
        # presence_of_element_located usa find_element (singular) no selenium 4.47
        driver.find_element = mock.Mock(
            side_effect=Exception('no such element: cpf'))
        status, detail = self.auth_core.authenticate(driver, field_timeout=1)
        self.assertEqual(status, 'failed')
        self.mock_solver_cls.assert_not_called()

    def test_maximize_exception_does_not_break_login(self):
        """Chrome >= 151 lança erro ao maximizar janela já maximizada;
        isso não pode impedir o fluxo de login."""
        self.configure_solver(strategy='checkbox_pass', success=True)
        driver = FakeDriver()
        driver.maximize_window = mock.Mock(
            side_effect=Exception(
                "unknown error: failed to change window state to 'normal', "
                "current state is 'maximized'"))
        self.install_script(driver, accept=True)

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=1)
        self.assertEqual(status, 'success')

    # ------------------------------------------------------------------
    # CPF mascarado: o portal rejeita dígitos puros no login (regex
    # /^\d{3}\.\d{3}\.\d{3}\-\d{2}$/) com alerta "CPF inválido".
    # ------------------------------------------------------------------

    def test_mask_cpf_formats_11_digits(self):
        self.assertEqual(self.auth_core.mask_cpf('06511122233'), '065.111.222-33')

    def test_mask_cpf_keeps_already_masked(self):
        self.assertEqual(self.auth_core.mask_cpf('065.111.222-33'), '065.111.222-33')

    def test_mask_cpf_keeps_non_cpf_values(self):
        self.assertEqual(self.auth_core.mask_cpf(''), '')
        self.assertEqual(self.auth_core.mask_cpf('abc'), 'abc')
        self.assertEqual(self.auth_core.mask_cpf('1234'), '1234')

    def test_login_sends_masked_cpf(self):
        """O CPF digitado no portal deve ir MASCARADO (###.###.###-##)."""
        from backend.core.auth_core import CPF_INPUT_XPATH
        self.configure_solver(strategy='checkbox_pass', success=True)
        driver = FakeDriver()
        self.install_script(driver, accept=True)

        status, detail = self.auth_core.authenticate(
            driver, field_timeout=1, submit_timeout=1, redirect_timeout=1)
        self.assertEqual(status, 'success')
        self.assertEqual(driver._elements[CPF_INPUT_XPATH].value, '065.111.222-33')


if __name__ == '__main__':
    unittest.main(verbosity=2)