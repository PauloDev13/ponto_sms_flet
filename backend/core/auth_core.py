"""Núcleo de autenticação no portal, desacoplado de Flet e da UI.

Este módulo pode ser importado e testado sem flet/pywin32, e será
reutilizado pelo backend web (FASE de migração).

Fluxo:
1. Cria o driver com perfil persistente (cookies de sessão reutilizados).
2. Se já existe sessão ativa (URL_INIT), retorna imediatamente.
3. Caso contrário, preenche credenciais e resolve o reCAPTCHA através do
   CaptchaSolver com clique automático no checkbox "Não sou um robô"
   (checkbox -> API -> manual).
4. Depois que o captcha estiver resolvido (token presente no textarea),
   o login é submetido via fetch() DENTRO da própria página — lendo a
   resposta do servidor sem recarregar a tela (um reload nativo pós-POST
   faz o portal voltar à tela de login e apagar as credenciais). Um único
   POST é enviado.
5. Só depois do servidor confirmar, a URL_INIT é aberta explicitamente
   (a sessão emitida no fetch já está no cookie jar do navegador).
6. O wait de resolução manual é injetável (callback) - no app Flet é a
   barra de progresso; num backend pode ser um sleep ou WebSocket.

Status de retorno:
- ('session_active', url) : já logado via perfil persistente
- ('success', url)        : login realizado
- ('manual_required', url): captcha pendente de resolução manual
- ('failed', motivo)      : falha no login
"""
import logging
import os
import re
import time
from typing import Callable, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from backend.core.browser_session import create_driver
from backend.core.captcha_solver import CaptchaSolver
from backend.core.settings import settings

logger = logging.getLogger(__name__)

# XPaths de elementos do portal
CPF_INPUT_XPATH = "//*[@id='cpf']"
SENHA_INPUT_XPATH = "//*[@id='senha']"
LOGIN_BUTTON_XPATH = "//*[@id='formPonto']/div/div[2]/button"


def _clear_portal_cookies(driver, url_base: str) -> None:
    """[MANTIDO COMO REFERÊNCIA] Remove cookies antigos do domínio do portal.

    O perfil persistente pode conter cookies de sessão antigos
    (PHPSESSID, etc.) que conflitam com o cookie novo emitido pelo
    fetch/login. Múltiplos cookies com o mesmo nome fazem o servidor
    ficar confuso e rejeitar o login (refresh + credenciais apagadas).

    *** DESATIVADO: limpa TODOS os cookies, incluindo sessões válidas.
    Ver _clear_stale_php_sessions para a versão atual. ***
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url_base).hostname or ''
        if not domain:
            return
        for c in driver.get_cookies():
            if domain in c.get('domain', ''):
                driver.delete_cookie(c['name'])
        logger.debug('Cookies antigos do portal removidos (domínio: %s).', domain)
    except Exception as e:
        logger.debug('Falha ao limpar cookies antigos: %s', e)


def _clear_stale_php_sessions(driver, url_base: str) -> None:
    """Remove apenas PHPSESSID duplicados, preservando a sessão válida.

    O perfil persistente pode conter múltiplos cookies PHPSESSID de
    sessões anteriores. Múltiplos cookies com o mesmo nome confundem
    o servidor. Esta função mantém apenas o PHPSESSID mais recente
    (o último da lista), removendo os duplicados.
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url_base).hostname or ''
        if not domain:
            return
        cookies = driver.get_cookies()
        php_sessions = [
            c for c in cookies
            if c.get('name') == 'PHPSESSID' and domain in c.get('domain', '')
        ]
        if len(php_sessions) > 1:
            # Mantém o último (mais recente), remove os anteriores
            for c in php_sessions[:-1]:
                driver.delete_cookie(c['name'])
            logger.debug(
                'PHPSESSID duplicados removidos: %d → 1 (domínio: %s).',
                len(php_sessions), domain)
    except Exception as e:
        logger.debug('Falha ao limpar PHPSESSID duplicados: %s', e)


def _login_form_absent(driver) -> bool:
    """Verifica se o formulário de login NÃO está na página (sessão ativa)."""
    try:
        return len(driver.find_elements(By.XPATH, CPF_INPUT_XPATH)) == 0
    except Exception:
        return False

# Submete o formulário de login via fetch DENTRO da página (mesmo-origin):
# o POST nativo recarrega a tela pós-resposta e, quando o portal rejeita,
# volta à tela de login apagando as credenciais. Com fetch() lemos a
# resposta do servidor sem navegar e só então abrimos a URL_INIT.
_SUBMIT_LOGIN_JS = r"""
(() => {
  if (window.__pontoLogin) { return window.__pontoLogin; }
  const f = document.getElementById('formPonto');
  if (!f) { window.__pontoLogin = {state:'error', error:'form nao encontrado'};
            return window.__pontoLogin; }
  const fd = new FormData(f);
  window.__pontoLogin = {
    state: 'pending', status: null, has_login_form: null, has_inicio: null,
    body_head: '', error: null, token_sent: (fd.get('g-recaptcha-response') || ''),
  };
  fetch('./inc/autentica.php', {
    method: 'POST', body: fd, credentials: 'same-origin', redirect: 'follow',
  })
    .then((r) => { window.__pontoLogin.status = r.status; return r.text(); })
    .then((t) => {
      window.__pontoLogin.body_head = t.slice(0, 3000);
      window.__pontoLogin.has_login_form =
        (t.indexOf('formPonto') !== -1) || (t.indexOf('g-recaptcha') !== -1);
      window.__pontoLogin.has_inicio = (t.toLowerCase().indexOf('inicio') !== -1);
      window.__pontoLogin.state = 'done';
    })
    .catch((e) => {
      window.__pontoLogin.error = String(e);
      window.__pontoLogin.state = 'error';
    });
  return window.__pontoLogin;
})()
"""

_READ_LOGIN_JS = "return window.__pontoLogin || {state: 'not-ready'};"

_LOGIN_ERROR_PATTERNS = [
    r'inválid|incorret|não foi possível|nao foi possivel|tente novamente',
    r'timeout-or-duplicate|invalid-input-response|missing-input-response',
    r'bloque|negado|encerrad|expirou',
]


def mask_cpf(value: Optional[str]) -> str:
    r"""Mascara o CPF (###.###.###-##) conforme exigido pelo portal.

    A página de login NÃO aplica máscara automática no campo (o script
    `$("#cpf").mask(...)` está comentado) e o formulário só submete quando
    o CPF casa com /^\d{3}\.\d{3}\.\d{3}\-\d{2}$/; dígitos puros disparam
    o alerta "CPF inválido" e o submit é bloqueado.
    """
    digits = re.sub(r'\D', '', (value or '').strip())
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return (value or '').strip()


def is_session_active(driver) -> bool:
    """Verifica se o perfil persistente já possui sessão no portal."""
    try:
        current_url = driver.current_url or ''
        return os.getenv('URL_INIT', '') in current_url
    except Exception:
        return False


def _read_recaptcha_token(driver) -> str:
    """Lê o token do reCAPTCHA do textarea na página (vazio = não resolvido).

    Usa querySelector por name (canônico do formulário) com fallback
    para getElementById — cobre variações de render do reCAPTCHA v2.
    """
    try:
        token = driver.execute_script(
            "var t=document.querySelector('[name=g-recaptcha-response]');"
            " if(!t) t=document.getElementById('g-recaptcha-response');"
            " return t ? (t.value||'') : ''")
        return token or ''
    except Exception:
        return ''


def _finish_login(driver, url_init: str, redirect_timeout: int, via: str,
                  max_retries: int = 3) -> Tuple[str, str]:
    """Conclui o login: aguarda o redirect e garante a URL_INIT aberta.

    Após o fetch de login bem-sucedido, a sessão está no cookie jar.
    Navega para URL_INIT e valida a presença da sessão (ausência do
    formulário de login). Aguarda no máximo 2s por redirect nativo
    (caso API tenha submetido via POST) e então navega explicitamente.
    """
    # 1) Aguarda redirect rápido (caso o servidor redirecione naturalmente)
    try:
        WebDriverWait(driver, min(redirect_timeout, 2)).until(
            ec.url_contains(url_init))
        if _login_form_absent(driver):
            return 'success', driver.current_url or ''
    except Exception:
        pass

    # 2) Navega explicitamente para URL_INIT e valida
    for attempt in range(max_retries):
        try:
            if url_init not in (driver.current_url or ''):
                driver.get(url_init)
            pause = 0.5 if attempt == 0 else 1.0 + attempt
            time.sleep(pause)
            if _login_form_absent(driver):
                return 'success', driver.current_url or ''
            logger.debug(
                '_finish_login tentativa %d: formulário de login ainda '
                'presente em %s.', attempt + 1, driver.current_url)
        except Exception as e:
            logger.debug('_finish_login tentativa %d exceção: %s', attempt + 1, e)
        time.sleep(0.5)

    return 'failed', (f'Login ({via}) não concluído: sessão não confirmada '
                      f'após {max_retries} tentativas em {url_init}')


def _submit_login_via_fetch(driver) -> Optional[dict]:
    """Dispara o login via fetch() dentro da página (UMA única vez).

    Retorna o estado da submissão ou None se o script não pôde executar.
    """
    try:
        state = driver.execute_script(_SUBMIT_LOGIN_JS)
        return state if isinstance(state, dict) else {}
    except Exception:
        return None


def _read_login_submission(driver) -> dict:
    """Lê o estado da submissão por fetch (pending/done/error)."""
    try:
        state = driver.execute_script(_READ_LOGIN_JS)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _detect_login_error(body_head: str) -> Optional[str]:
    """Procura indícios de rejeição na resposta do autentica.php."""
    lower = (body_head or '').lower()
    for pattern in _LOGIN_ERROR_PATTERNS:
        if re.search(pattern, lower):
            return f'Portal rejeitou o login ({pattern!r}). Verifique credenciais/captcha'
    return None


def _submit_native_fallback(driver, url_init: str, submit_timeout: int,
                            redirect_timeout: int) -> Tuple[str, str]:
    """Falha de segurança: submite nativo (botão) e aguarda o redirect."""
    try:
        button = WebDriverWait(driver, submit_timeout).until(
            ec.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH)))
        button.click()
        WebDriverWait(driver, redirect_timeout).until(ec.url_contains(url_init))
        return 'success', driver.current_url or ''
    except Exception:
        return _finish_login(driver, url_init, redirect_timeout, 'fallback nativo')


def authenticate(
        driver,
        user: Optional[str] = None,
        password: Optional[str] = None,
        url_base: Optional[str] = None,
        url_init: Optional[str] = None,
        manual_solve_wait: int = 30,
        on_manual_wait: Optional[Callable[[int], None]] = None,
        field_timeout: int = 20,
        submit_timeout: int = 10,
        redirect_timeout: int = 25,
) -> Tuple[str, str]:
    """Executa o login no portal e retorna (status, detalhe)."""
    user = user or settings.user
    password = password or settings.password
    url_base = url_base or settings.url_base
    url_init = url_init or settings.url_init
    wait_fn = on_manual_wait or (lambda seconds: time.sleep(seconds))

    driver.get(url_base)
    try:
        driver.maximize_window()
    except Exception:
        # Janela já pode estar maximizada (Chrome >= 151 lança erro quando o
        # estado atual já é 'maximized'); o maximizar é apenas conveniência.
        pass

    # Remove PHPSESSID duplicados do portal (preserva sessão válida).
    # Antes: _clear_portal_cookies apagava TODOS os cookies, matando a sessão.
    # Atual: só remove duplicados para evitar confusão no servidor.
    _clear_stale_php_sessions(driver, url_base)

    # 1) Reuso de sessão do perfil persistente
    if is_session_active(driver):
        return 'session_active', driver.current_url or ''

    # 2) Preenche credenciais
    try:
        WebDriverWait(driver, field_timeout).until(
            ec.presence_of_element_located((By.XPATH, CPF_INPUT_XPATH)))
        WebDriverWait(driver, field_timeout).until(
            ec.presence_of_element_located((By.XPATH, SENHA_INPUT_XPATH)))
    except Exception as e:
        return 'failed', f'Campos de login não encontrados: {e}'

    cpf_input = driver.find_element(By.XPATH, CPF_INPUT_XPATH)
    senha_input = driver.find_element(By.XPATH, SENHA_INPUT_XPATH)
    cpf_input.clear()
    # O portal espera o CPF mascarado (###.###.###-##); digite já formatado
    # para não esbarrar na validação client-side do formulário de login.
    cpf_input.send_keys(mask_cpf(user))
    time.sleep(1)
    senha_input.clear()
    senha_input.send_keys(password)

    # 3) Resolve o reCAPTCHA. Fluxo em camadas (CaptchaSolver):
    #    - clique automático no checkbox "Não sou um robô" (quando presente);
    #    - se abrir desafio de imagem, API paga (se configurada);
    #    - senão, resolução manual pelo usuário na janela maximizada.
    solver = CaptchaSolver(driver=driver, page_url=driver.current_url or url_base)
    result = solver.solve(submit_xpath=LOGIN_BUTTON_XPATH)

    # API paga resolveu e já submeteu o formulário
    if result.success and result.strategy == 'api' and result.token:
        logger.info('Captcha resolvido via API (%s).', solver.provider)
        return _finish_login(driver, url_init, redirect_timeout, 'API')

    # checkbox_pass / manual_required: espera o token do captcha e submete
    # o login via fetch() (um único POST, sem reload nativo da tela).
    deadline = time.time() + manual_solve_wait
    submitted_at: Optional[float] = None
    while time.time() < deadline:
        if is_session_active(driver):
            return 'session_active', driver.current_url or ''

        if submitted_at is None:
            token = _read_recaptcha_token(driver)
            if not token:
                time.sleep(0.3)
                continue
            state = _submit_login_via_fetch(driver)
            if state is None:
                return _submit_native_fallback(
                    driver, url_init, submit_timeout, redirect_timeout)
            submitted_at = time.time()
            logger.info('Captcha resolvido; login submetido via fetch (1x).')
            time.sleep(0.1)
            continue

        state = _read_login_submission(driver)
        if state.get('state') == 'done':
            if not state.get('has_login_form'):
                logger.info('Portal aceitou o login; sessão estabelecida.')
                return 'success', driver.current_url or ''
            reason = _detect_login_error(state.get('body_head') or '') or (
                'Portal não aceitou o login (respondeu com a página de login).')
            return 'failed', reason
        if state.get('state') == 'error':
            return 'failed', f'Falha ao submeter o login: {state.get("error")}'
        time.sleep(0.2)

    if submitted_at:
        return 'failed', 'Login submetido, mas o portal não confirmou a sessão.'
    return 'failed', 'Captcha não resolvido no tempo limite.'


def login_service(
        user: Optional[str] = None,
        password: Optional[str] = None,
        url_base: Optional[str] = None,
        url_init: Optional[str] = None,
        manual_solve_wait: int = 30,
        on_manual_wait: Optional[Callable[[int], None]] = None,
        headless: bool = False,
        field_timeout: int = 20,
        submit_timeout: int = 10,
        redirect_timeout: int = 25,
) -> Tuple[str, object]:
    """Cria o driver e executa o login (versão sem dependência de Flet).

    Retorna (status, driver_or_none).
    """
    try:
        driver = create_driver(headless=headless, print_to_pdf=False)
    except Exception as e:
        return 'failed', None

    try:
        status, detail = authenticate(
            driver=driver,
            user=user,
            password=password,
            url_base=url_base,
            url_init=url_init,
            manual_solve_wait=manual_solve_wait,
            on_manual_wait=on_manual_wait,
            field_timeout=field_timeout,
            submit_timeout=submit_timeout,
            redirect_timeout=redirect_timeout,
        )
        return status, driver
    except Exception as e:
        print(f'Erro no login: {e}')
        return 'failed', None
