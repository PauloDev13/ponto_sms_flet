"""Diagnóstico decisivo: captura a resposta RAW do autentica.php no login.

Replica o fluxo atual (preenche credenciais, clica sozinho no checkbox,
aguarda o token, clica ENTRAR UMA vez) mas INTERCEPTA o submit com um
listener via fetch() para ler o que o servidor realmente responde — sem
que o reload da página apague a tela e esconda o motivo.

Uso: python scripts/debug_server_response.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / '.env')

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as ec  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

from services.auth_core import mask_cpf  # noqa: E402
from services.browser_session import create_driver  # noqa: E402
from services.captcha_solver import CaptchaSolver  # noqa: E402

CPF_XPATH = "//*[@id='cpf']"
SENHA_XPATH = "//*[@id='senha']"
BTN_XPATH = "//*[@id='formPonto']/div/div[2]/button"
URL_BASE = os.getenv('URL_BASE')
URL_INIT = os.getenv('URL_INIT')
OUT = Path(tempfile.gettempdir()) / 'autentica_raw_response.txt'

# Instala (uma vez) um listener de submit que faz o POST via fetch e guarda
# a resposta do servidor em window.__diag, sem navegar/reload.
INJECT = r"""
(() => {
  if (window.__diagInstalled) { return; }
  window.__diagInstalled = true;
  window.__diag = {state: 'not-ready', token: null, cpf: null, senha_len: null,
                   status: null, body: '', final_url: location.href, error: null};
  const f = document.getElementById('formPonto');
  if (!f) { window.__diag.state = 'no-form'; return; }
  f.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(f);
    window.__diag.cpf = fd.get('cpf');
    window.__diag.senha_len = ((fd.get('senha') || '') + '').length;
    window.__diag.token = fd.get('g-recaptcha-response') || '';
    window.__diag.state = 'posting';
    fetch('./inc/autentica.php', {
      method: 'POST', body: fd, credentials: 'same-origin', redirect: 'follow',
    })
      .then((r) => { window.__diag.status = r.status; return r.text(); })
      .then((t) => { window.__diag.body = t; window.__diag.state = 'done';
                     window.__diag.final_url = location.href; })
      .catch((err) => { window.__diag.error = String(err); window.__diag.state = 'error'; });
  }, true);
})();
"""


def read_token(driver) -> str:
    try:
        return driver.execute_script(
            "var t=document.querySelector('[name=g-recaptcha-response]');"
            " return t ? (t.value || '') : ''") or ''
    except Exception:
        return ''


def read_diag(driver) -> dict:
    try:
        d = driver.execute_script("return window.__diag;")
        return d or {}
    except Exception as e:
        return {'error': str(e)}


def main() -> int:
    print('== DIAGNÓSTICO DA RESPOSTA DO autentica.php ==')
    print(f'URL_BASE : {URL_BASE}')
    print(f'CPF (mascarado) a enviar: {mask_cpf(os.getenv("USER"))}')
    print(f'SENHA len: {len(os.getenv("PASSWORD") or "")}')
    print('>> Chrome com perfil TEMPORÁRIO (não mexe na janela do servidor)...')

    profile = tempfile.mkdtemp(prefix='ponto_diag_')
    driver = None
    try:
        driver = create_driver(
            headless=False, profile_dir=profile, maximize_window=True)
        driver.get(URL_BASE)
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete')
        print(f'>> URL inicial pós-load: {driver.current_url}')

        if URL_INIT in (driver.current_url or ''):
            print('[OK] Sessão ativa já existia (impossível no perfil novo).')
            return 0

        # Preenche credenciais
        cpf_input = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.XPATH, CPF_XPATH)))
        senha_input = driver.find_element(By.XPATH, SENHA_XPATH)
        cpf_input.clear()
        cpf_input.send_keys(mask_cpf(os.getenv('USER')))
        time.sleep(1)
        senha_input.clear()
        senha_input.send_keys(os.getenv('PASSWORD') or '')
        print('>> Credenciais preenchidas (CPF mascarado).')

        # Instala o interceptador ANTES de qualquer clique
        driver.execute_script(INJECT)

        # Clique automático no checkbox (mesmo caminho da produção)
        solver = CaptchaSolver(driver=driver, page_url=driver.current_url or URL_BASE)
        print(f'>> reCAPTCHA presente: {solver.is_present()}')
        if solver.is_present():
            passed = solver.click_checkbox()
            print(f'>> click_checkbox -> {passed}; challenge_opened -> '
                  f'{solver.challenge_opened()}')

        # Aguarda o token do captcha (até 120s; se abrir imagem, resolver na janela)
        deadline = time.time() + 120
        token = ''
        while time.time() < deadline:
            token = read_token(driver)
            if token:
                break
            time.sleep(1)
        print(f'>> Token captcha: {"SIM (len=%d)" % len(token) if token else "NÃO"}')
        if not token:
            print('   Se um desafio de imagem abriu, resolva-o na janela e rode de novo.')
            return 1

        # Clica ENTRAR (dispara nosso interceptador) — acesso único
        btn = WebDriverWait(driver, 10).until(
            ec.element_to_be_clickable((By.XPATH, BTN_XPATH)))
        btn.click()
        print('>> ENTRAR clicado (submit interceptado por fetch).')

        deadline = time.time() + 30
        while time.time() < deadline:
            d = read_diag(driver)
            if d.get('state') in ('done', 'error', 'no-form'):
                break
            time.sleep(0.5)
        diag = read_diag(driver)

        print('-' * 70)
        print(f'  diag.state     : {diag.get("state")}')
        print(f'  status HTTP    : {diag.get("status")}')
        print(f'  token usado    : {(diag.get("token") or "")[:24]}... (len={len(diag.get("token") or "")})')
        print(f'  cpf enviado    : {diag.get("cpf")}')
        print(f'  senha len      : {diag.get("senha_len")}')
        print(f'  final_url      : {diag.get("final_url")}')
        print(f'  error          : {diag.get("error")}')
        body = diag.get('body') or ''
        OUT.write_text(body, encoding='utf-8', errors='replace')
        print(f'  resposta salva : {OUT} ({len(body)} bytes)')

        # Classificação rápida da resposta
        has_login_form = 'formPonto' in body or 'g-recaptcha' in body
        has_inicio = 'inicio' in body.lower()
        print('  contém formPonto   :', has_login_form)
        print('  contém "inicio"    :', has_inicio)
        for kw in ['inválid', 'incorret', 'senha', 'captcha', 'bloque', 'negado',
                   'não encontrado', 'nao encontrado', 'erro']:
            if kw.lower() in body.lower():
                idx = body.lower().find(kw.lower())
                print(f'  trecho com "{kw}": …{body[max(0,idx-60):idx+80]!r}…')
        print('-' * 70)

        # Às vezes o servidor responde já com a sessão (set-cookie no fetch):
        # navega para a URL_INIT e verifica se logou.
        driver.get(URL_INIT)
        time.sleep(2)
        logged = URL_INIT in (driver.current_url or '') and len(
            driver.find_elements(By.XPATH, CPF_XPATH)) == 0
        print(f'>> Após driver.get(URL_INIT): {driver.current_url}')
        print(f'>> Logado via fetch (sessão preservada): {logged}')
        return 0 if logged else 1
    except Exception as e:
        print(f'[ERRO] {type(e).__name__}: {e}')
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == '__main__':
    sys.exit(main())