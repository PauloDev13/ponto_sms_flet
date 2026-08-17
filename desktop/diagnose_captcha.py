"""Script de diagnóstico do login + reCAPTCHA usando o .env da raiz do projeto.

O que ele faz:
1. Carrega o .env da raiz do projeto (mesmo usado pela aplicação).
2. Abre o Chrome com perfil persistente + stealth (browser_session).
3. Tenta o login e reporta em qual estratégia de captcha o fluxo caiu.

Uso:  python diagnose_captcha.py
"""
import os
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Carrega o .env da raiz do projeto SEM depender do config_env (que depende de flet)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except ImportError:
    print('[AVISO] python-dotenv não instalado; usando variáveis já exportadas.')


def mask(value: str | None, keep: int = 3) -> str:
    """Mascara credenciais para exibição segura no log."""
    if not value:
        return '(vazio)'
    return f'{value[:keep]}...*** (len={len(value)})'


def main() -> int:
    user = os.getenv('USER') or ''
    url_base = os.getenv('URL_BASE') or ''
    url_init = os.getenv('URL_INIT') or ''

    print('=' * 70)
    print('DIAGNÓSTICO DE LOGIN + reCAPTCHA')
    print('=' * 70)
    print(f'  URL_BASE      : {url_base or "(vazio)"}')
    print(f'  URL_INIT      : {url_init or "(vazio)"}')
    print(f'  USER          : {mask(user)}')
    print(f'  PASSWORD      : {mask(os.getenv("PASSWORD"))}')
    print(f'  CAPTCHA_PROVIDER = {os.getenv("CAPTCHA_PROVIDER") or "(não configurado)"}')
    print(f'  CAPTCHA_API_KEY   = {(("configurada") if os.getenv("CAPTCHA_API_KEY") else "(não configurada)")}')
    print('-' * 70)

    if not all([user, url_base, url_init]):
        print('[ERRO] As variáveis USER, URL_BASE e URL_INIT precisam estar no .env.')
        return 2

    from backend.core.browser_session import create_driver
    from backend.core.captcha_solver import CaptchaSolver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    driver = None
    try:
        print('[*] Criando driver com perfil persistente + stealth...')
        driver = create_driver(headless=False, print_to_pdf=False)

        print(f'[*] Navegando para URL_BASE...')
        driver.get(url_base)
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete')

        # --- Verifica se já existe sessão (já logado do perfil persistente) ---
        current_url = driver.current_url
        print(f'[*] URL atual após carregar: {current_url}')
        if url_init in current_url:
            print('[OK] Já existe sessão ativa do perfil persistente (sem precisar logar).')
            return 0

        # --- Localiza campos de login ---
        try:
            cpf_input = WebDriverWait(driver, 20).until(
                ec.presence_of_element_located((By.XPATH, "//*[@id='cpf']")))
            senha_input = WebDriverWait(driver, 20).until(
                ec.presence_of_element_located((By.XPATH, "//*[@id='senha']")))
        except Exception as e:
            print(f'[ERRO] Campos de login não encontrados: {e}')
            return 3

        print('[*] Preenchendo usuário/senha...')
        from backend.core.auth_core import mask_cpf
        cpf_input.clear()
        cpf_input.send_keys(mask_cpf(user))
        senha_input.clear()
        senha_input.send_keys(os.getenv('PASSWORD') or '')

        # --- Detecta e resolve reCAPTCHA ---
        solver = CaptchaSolver(driver=driver, page_url=url_base)

        if not solver.is_present():
            print('[INFO] Nenhum reCAPTCHA v2 (anchor) detectado na página.')
        else:
            print(f'[*] reCAPTCHA detectado. Sitekey: {solver.detect_sitekey() or "(não localizada)"}')

        print('[*] Tentando estratégia do CaptchaSolver...')
        result = solver.solve(submit_xpath="//*[@id='formPonto']/div/div[2]/button")

        print('-' * 70)
        print(f'  Estratégia        : {result.strategy}')
        print(f'  Sucesso           : {result.success}')
        print(f'  Motivo            : {result.reason}')
        print(f'  Desafio aberto    : {result.diagnostics.get("challenge", False)}')
        print(f'  Token obtido      : {"sim" if result.token else "não"}')
        print('-' * 70)

        # --- Aguarda resultado do login ---
        print('[*] Aguardando redirecionamento após login...')
        for attempt in range(6):
            time.sleep(3)
            if url_init in driver.current_url:
                print(f'[OK] Login realizado! URL: {driver.current_url}')
                print(f'[STRATEGY] {result.strategy}')
                return 0
        print(f'[AVISO] Não foi possível confirmar login. URL atual: {driver.current_url}')
        print(f'[STRATEGY] {result.strategy}')
        return 1

    except Exception as e:
        print(f'[ERRO] Exceção no fluxo: {type(e).__name__}: {e}')
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == '__main__':
    import time
    sys.exit(main())
