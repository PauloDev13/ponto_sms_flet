"""Diagnóstico ao vivo do login no portal (valores reais + resposta do servidor).

Uso:  python scripts/debug_login_flow.py
Abre o Chrome visível, preenche as credenciais (CPF mascarado), aguarda o
usuário resolver o reCAPTCHA e, quando resolvido, clica em ENTRAR UMA vez.
Imprime os valores enviados, a URL final, o título, se o formulário de login
ainda está presente e um screenshot.

Ao final, escreve o resultado em $TEMP\\debug_login_result.json para leitura.
"""
import json
import os
import sys
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

from backend.core.auth_core import mask_cpf  # noqa: E402
from backend.core.browser_session import create_driver  # noqa: E402

CPF_XPATH = "//*[@id='cpf']"
SENHA_XPATH = "//*[@id='senha']"
LOGIN_BUTTON_XPATH = "//*[@id='formPonto']/div/div[2]/button"
URL_BASE = os.getenv('URL_BASE')
URL_INIT = os.getenv('URL_INIT')
USER = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
RESULT_FILE = Path(os.environ.get('TEMP', '.')) / 'debug_login_result.json'


def probe(driver, label):
    try:
        cpf_val = driver.execute_script(
            "var e=document.getElementById('cpf'); return e ? e.value : '(sem campo cpf)'")
    except Exception as e:
        cpf_val = f'(erro {e})'
    try:
        token = driver.execute_script(
            "var t=document.querySelector('[name=g-recaptcha-response]');"
            " return t ? t.value.slice(0, 20) + '...' : '(sem token)'")
    except Exception as e:
        token = f'(erro {e})'
    print(f'[{label}] URL: {driver.current_url}')
    print(f'[{label}] CPF no campo: {cpf_val!r}')
    print(f'[{label}] reCAPTCHA token: {token}')
    return {'label': label, 'url': driver.current_url, 'cpf': cpf_val,
            'token': token}


def main() -> int:
    result = {'user_masked': mask_cpf(USER), 'url_base': URL_BASE}
    driver = None
    try:
        print('== DIAGNÓSTICO DE LOGIN (fluxo web) ==')
        print(f'URL_BASE : {URL_BASE}')
        print(f'CPF a enviar (mascarado): {mask_cpf(USER)}')
        print(f'SENHA (len): {len(PASSWORD or "")}')
        print('Abrindo Chrome (visível, maximizado)...')

        driver = create_driver(headless=False, maximize_window=True)
        result.update(probe(driver, 'driver criado'))

        print('>> Chamando authenticate() (mesmo caminho do session_manager)...')
        print('>> RESOLVA O reCAPTCHA NA JANELA quando aparecer.')
        from backend.core.auth_core import authenticate
        status, detail = authenticate(
            driver,
            manual_solve_wait=240,
            redirect_timeout=60,
        )
        print(f'>> authenticate retornou: status={status!r} detail={detail!r}')
        result.update({'auth_status': status, 'auth_detail': detail})
        result.update(probe(driver, 'apos authenticate'))

        title = driver.title or ''
        login_still_present = len(
            driver.find_elements(By.XPATH, CPF_XPATH)) > 0
        print(f'>> Título da página: {title}')
        print(f'>> Formulário de login ainda presente: {login_still_present}')
        print(f'>> Chegou na URL_INIT: {URL_INIT in (driver.current_url or "")}')
        result.update({'title': title,
                       'login_still_present': login_still_present,
                       'reached_url_init': URL_INIT in (driver.current_url or '')})

        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text[:800]
            print(f'>> Texto visível na página:\n{body_text}')
            result['body_text'] = body_text
        except Exception:
            pass

        shot = Path(os.environ.get('TEMP', '.')) / 'debug_login_after.png'
        driver.save_screenshot(str(shot))
        result['screenshot'] = str(shot)
        print(f'>> Screenshot salvo em: {shot}')

        return 0 if result.get('reached_url_init') else 1
    except Exception as e:
        print(f'>> ERRO: {type(e).__name__}: {e}')
        result['error'] = f'{type(e).__name__}: {e}'
        return 1
    finally:
        RESULT_FILE.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8')
        print(f'>> Resultado em {RESULT_FILE}')
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == '__main__':
    sys.exit(main())