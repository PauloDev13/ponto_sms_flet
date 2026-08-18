"""Pré-login no portal: cria a sessão persistente do navegador.

Abre o Chrome visível e tenta o login (reutilizando cookies). Se o
reCAPTCHA aparecer, aguarda a resolução manual na janela por até
--manual-wait segundos e conclui o login automaticamente.

Após rodar com sucesso ('session_active' ou 'success'), o endpoint
/api/v1/ponto passa a reutilizar a sessão sem exigir novo captcha.

Uso:
    python scripts/pre_login.py [--manual-wait 180]
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Garante o working directory na raiz (config_env carrega o .env a partir do CWD)
os.chdir(ROOT)

from backend.core.settings import settings  # noqa: E402 — carrega .env via load_dotenv
from backend.core.auth_core import authenticate  # noqa: E402
from backend.core.browser_session import create_driver  # noqa: E402

STATUS_MESSAGES = {
    'session_active': 'Sessão ativa reutilizada (sem captcha).',
    'success': 'Login realizado com sucesso.',
    'manual_required': 'Captcha não resolvido. Tente novamente e resolva o desafio.',
    'failed': 'Falha no login. Verifique credenciais/URLs no .env.',
}


def _print_captcha_progress(seconds_remaining: int) -> None:
    """Imprime progresso durante a espera pela resolução manual do captcha."""
    if seconds_remaining % 15 == 0 or seconds_remaining <= 10:
        print(f'  Aguardando resolução do captcha... ({seconds_remaining}s restantes)')


def main() -> int:
    parser = argparse.ArgumentParser(description='Pré-login no portal (sessão persistente)')
    parser.add_argument('--manual-wait', default=180, type=int,
                        help='Segundos de espera para resolução manual do captcha')
    parser.add_argument('--redirect-timeout', default=60, type=int,
                        help='Segundos de espera pelo redirecionamento pós-login')
    args = parser.parse_args()

    print('Abrindo o navegador e tentando o login...')
    print('Se o reCAPTCHA aparecer, resolva-o na janela do Chrome.')

    try:
        driver = create_driver(headless=False)
    except Exception as e:
        print(f'Erro ao criar o navegador: {e}')
        return 1

    try:
        status, detail = authenticate(
            driver,
            manual_solve_wait=args.manual_wait,
            redirect_timeout=args.redirect_timeout,
            on_manual_wait=_print_captcha_progress,
        )
    except Exception as e:
        print(f'Erro durante o login: {e}')
        return 1
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f'Status: {status}')
    print(f'Detalhe: {detail}')
    print(STATUS_MESSAGES.get(status, ''))

    return 0 if status in ('session_active', 'success') else 1


if __name__ == '__main__':
    sys.exit(main())
