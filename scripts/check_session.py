"""Verifica rapidamente se a sessão persistente no portal está ativa.

Uso:
    python -u scripts/check_session.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Garante o working directory na raiz (config_env carrega o .env a partir do CWD)
os.chdir(ROOT)

from backend.core.auth_core import is_session_active  # noqa: E402
from backend.core.browser_session import create_driver  # noqa: E402
from backend.core.settings import settings  # noqa: E402


def main() -> int:
    driver = create_driver(headless=True)
    try:
        driver.get(settings.url_base)
        url = driver.current_url or ''
        active = is_session_active(driver)
        print(f'current_url: {url}')
        print(f'sessao_ativa: {active}')
        return 0 if active else 1
    finally:
        driver.quit()


if __name__ == '__main__':
    sys.exit(main())
