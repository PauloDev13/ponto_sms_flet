"""Sessão de navegador do backend (janela mantida aberta e minimizada).

O portal usa cookies de sessão que o perfil do Chrome NÃO persiste de
forma confiável entre execuções. Estratégia atual:

- A janela do navegador fica ABERTA após o processamento (park_driver),
  minimizada, preservando a sessão viva no próprio navegador — o próximo
  processamento reaproveita a MESMA janela (get_driver), sem novo login;
- Como redundância, os cookies da sessão também são salvos em disco
  (`~/.ponto_sms_flet/cookies.json`) sempre que a sessão é estabelecida
  ou confirmada (caso o navegador seja encerrado, a janela nova injeta
  os cookies salvos antes de verificar a sessão);
- A detecção de sessão é feita pela presença do formulário de login na
  página interna (URL_INIT): se a janela cair no login, a sessão expirou
  e a janela abre maximizada apenas para o novo login + captcha;
- Ao encerrar o servidor (lifespan), close_driver() fecha a janela de
  fato.
"""
import json
import logging
import os
import threading
from pathlib import Path

from selenium.webdriver.common.by import By

from backend.core.settings import settings
from backend.core.auth_core import authenticate
from backend.core.browser_session import create_driver, default_profile_dir

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_driver = None

# Cookies de sessão salvos entre janelas (perfil não os persiste sozinho)
COOKIES_FILE = Path(default_profile_dir()).parent / 'cookies.json'

# XPATH do formulário de login: presença => sessão encerrada
LOGIN_FORM_XPATH = "//*[@id='cpf']"


def _is_service_context() -> bool:
    """Detecta se está rodando como serviço Windows (Session 0, sem desktop).

    Serviços NSSM rodam na Session 0 que não tem desktop interativo.
    Nesse contexto, o Chrome abre mas a janela é invisível ao usuário.
    """
    if os.name != 'nt':
        return False
    try:
        import subprocess
        result = subprocess.run(
            ['query', 'session'],
            capture_output=True, text=True, timeout=5, errors='replace',
        )
        # Session 0 é a sessão do serviço;*> 0 é interativa
        for line in result.stdout.splitlines():
            if 'Session' in line and ('console' in line.lower() or 'rdp' in line.lower()):
                parts = line.split()
                for part in parts:
                    if part.isdigit() and int(part) > 0:
                        return False
                return True
    except Exception:
        pass
    return False


def _has_login_form(driver) -> bool:
    try:
        return len(driver.find_elements(By.XPATH, LOGIN_FORM_XPATH)) > 0
    except Exception:
        return True


def _session_alive(driver) -> bool:
    """Verifica a sessão navegando para a página INTERNA (URL_INIT).

    Sessão viva: o portal mantém a página interna (sem formulário de
    login). Sessão expirada: o portal redireciona para o login (formulário
    presente). Baseado na presença do formulário (robusto a redirects).
    """
    try:
        driver.get(settings.url_init)
        return not _has_login_form(driver)
    except Exception:
        return False


def _save_cookies(driver) -> None:
    """Persiste os cookies da sessão para reuso na próxima janela."""
    try:
        cookies = driver.get_cookies()
        if not cookies:
            logger.warning('Sem cookies para salvar (sessão não emitida?).')
            return
        COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIES_FILE.write_text(
            json.dumps(cookies, ensure_ascii=False), encoding='utf-8')
        logger.info('Cookies de sessão renovados e salvos (%d) em %s.',
                    len(cookies), COOKIES_FILE)
    except Exception as e:
        logger.warning('Falha ao salvar cookies de sessão: %s', e)


def _load_cookies(driver) -> bool:
    """Injeta os cookies salvos na janela nova (mesma origem do portal).

    Retorna True se injetou cookies e o navegador ficou em URL_INIT
    (chamador pode pular _session_alive — basta checar o formulário
    na página atual).
    """
    if not COOKIES_FILE.exists():
        logger.info('Sem cookies salvos: login será necessário nesta execução.')
        return False
    try:
        cookies = json.loads(COOKIES_FILE.read_text(encoding='utf-8'))
        if not cookies:
            return False
        driver.get(settings.url_init)  # estabelece a origem para add_cookie
        ok = 0
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
                ok += 1
            except Exception as e:
                logger.debug('add_cookie rejeitado (%s): %s',
                             cookie.get('name'), str(e)[:200])
        if ok < len(cookies):
            logger.warning('Cookies de sessão: %d/%d injetados.',
                           ok, len(cookies))
        else:
            logger.info('Cookies de sessão injetados (%d).', ok)
        return True  # navegador em URL_INIT; chamador pode checar o formulário
    except Exception as e:
        logger.warning('Falha ao injetar cookies de sessão: %s', e)
        return False


def _prepare_window(driver, preload_url: str = '') -> None:
    """Pré-carrega a URL da busca (se informada) e minimiza a janela.

    Mantém o frontend em evidência; a janela do backend só é maximizada
    durante o login/captcha.
    """
    if preload_url:
        try:
            driver.get(preload_url)
            logger.debug('Janela pré-carregada na URL da busca.')
        except Exception as e:
            logger.warning('Falha ao pré-carregar a URL da busca: %s', e)
    try:
        driver.minimize_window()
    except Exception as e:
        logger.warning('Falha ao minimizar a janela: %s', e)


def _minimize(driver) -> None:
    try:
        driver.minimize_window()
    except Exception as e:
        logger.warning('Falha ao minimizar a janela: %s', e)


def _maximize(driver) -> None:
    try:
        driver.maximize_window()
    except Exception as e:
        logger.warning('Falha ao maximizar a janela: %s', e)


def _quit(driver) -> None:
    try:
        driver.quit()
    except Exception:
        pass


def get_driver(manual_solve_wait: int = 300, preload_url: str = '') -> object:
    """Abre/obtém uma janela pronta para processar, refazendo o login se preciso.

    - Janela já aberta (mantida pelo park_driver após o processamento)
      com sessão ativa: reutiliza a MESMA janela, já navegada para
      preload_url (ex.: primeira busca do job) e minimizada — o frontend
      permanece em evidência e nenhum login é necessário.
    - Sessão expirada: a janela antiga é encerrada e uma nova abre
      maximizada para login + captcha; após o sucesso, minimizada e
      pré-carregada.
    - Driver stale (pre_login.py rodou externamente): detecta o driver
      morto, fecha, cria um novo e recarrega os cookies do disco — sem
      precisar reiniciar o serviço.
    - O chamador deve manter a janela ao concluir com park_driver().
    """
    global _driver

    with _lock:
        # 1) Reaproveita a janela mantida aberta pelo processamento anterior
        if _driver is not None:
            try:
                if _session_alive(_driver):
                    _save_cookies(_driver)
                    _prepare_window(_driver, preload_url)
                    logger.info('Janela do backend reutilizada (sessão ativa).')
                    return _driver
            except Exception:
                pass
            # Driver stale ou sessão expirada — fecha e tenta recarregar
            # cookies do disco (pre_login.py pode ter renovado a sessão)
            logger.info('Driver stale/sessão expirada; recarregando cookies do disco...')
            _quit(_driver)
            _driver = None

        # 2) Abre uma NOVA janela, já maximizada (evita flicker minimize→maximize),
        #    e injeta a sessão salva.
        try:
            driver = create_driver(
                headless=False,
                print_to_pdf=False,
                maximize_window=True,
                start_minimized=False,
            )
        except Exception as e:
            logger.error('Não foi possível abrir o navegador: %s', e)
            raise RuntimeError('Não foi possível abrir o navegador do portal.') from e

        _loaded = _load_cookies(driver)

        # 3) Sessão ativa? Se _load_cookies injetou cookies, o navegador
        #    já está em URL_INIT — checa o formulário SEM navegar de novo
        #    (evita o "shake" de carregar a mesma página duas vezes).
        session_ok = False
        if _loaded:
            session_ok = not _has_login_form(driver)
        else:
            session_ok = _session_alive(driver)

        if session_ok:
            _driver = driver
            _save_cookies(driver)
            _prepare_window(driver, preload_url)
            logger.info('Sessão do navegador reutilizada (janela minimizada).')
            return driver

        # 4) Sessão expirada: maximiza para o login + resolução do captcha
        logger.info('Sessão expirada: abrindo janela para novo login/captcha.')

        # Em contexto de serviço (Session 0), o Chrome abre mas a janela é
        # invisível ao usuário. Nesse caso, não adianta tentar login manual — o usuário
        # precisa rodar pre_login.py interativamente.
        if _is_service_context():
            _quit(driver)
            raise RuntimeError(
                'SESSÃO DO PORTAL EXPIRADA. '
                'O serviço está rodando sem desktop interativo (Session 0) '
                'e a janela do Chrome é invisível neste contexto.\n\n'
                'Para renovar a sessão:\n'
                '1. Conecte-se à VM via RDP\n'
                '2. Abra um PowerShell como o mesmo usuário do serviço\n'
                '3. Execute: cd C:\\Apps\\ponto_sms_flet && '
                '.\\.venv\\Scripts\\python.exe scripts\\pre_login.py --manual-wait 180\n'
                '4. Resolva o captcha na janela do Chrome\n'
                '5. O serviço detectará automaticamente a nova sessão '
                'no próximo job (não é necessário reiniciar o serviço).'
            )

        _maximize(driver)
        try:
            status, detail = authenticate(
                driver=driver, manual_solve_wait=manual_solve_wait)
        except Exception as e:
            logger.error('Erro durante o login (%s); encerrando a janela.', e)
            _quit(driver)
            raise RuntimeError(
                f'Falha durante o login no portal: {e}') from e

        if status not in ('session_active', 'success'):
            logger.error('Login falhou (status=%s): %s', status, detail)
            _quit(driver)
            raise RuntimeError(
                f'Login no portal não realizado (status: {status}): {detail} '
                'Resolva o captcha na janela do navegador e tente novamente.')

        # A sessão já foi confirmada pelo response do fetch (sem formulário
        # de login na resposta). Não navega para URL_INIT — economiza uma
        # ida e volta e vai direto para a URL de pesquisa (preload_url).
        _driver = driver
        _save_cookies(driver)
        _prepare_window(driver, preload_url)
        logger.info('Sessão do navegador renovada (status: %s).', status)
        return driver


def park_driver() -> None:
    """Mantém a janela do navegador ABERTA e minimizada ao fim do processamento.

    Chamado ao concluir (ou falhar) a geração dos arquivos; a próxima
    chamada de get_driver reaproveita a MESMA janela e, com a sessão
    ainda viva no navegador, dispensa novo login/captcha. Renova os
    cookies em disco como redundância (caso o navegador precise ser
    recriado).
    """
    global _driver
    with _lock:
        if _driver is None:
            return
        _save_cookies(_driver)
        _minimize(_driver)
        logger.info('Janela do navegador do backend mantida aberta (minimizada).')


def close_driver() -> None:
    """Fecha de fato a janela do navegador (usado no encerramento do servidor).

    No fluxo normal de processamento, a janela NÃO é fechada: use
    park_driver() para mantê-la aberta e reaproveitar a sessão.
    """
    global _driver
    with _lock:
        if _driver is None:
            return
        _quit(_driver)
        _driver = None
        logger.info('Janela do navegador do backend fechada.')