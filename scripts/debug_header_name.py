"""Diagnóstico: localiza o nome do SERVIDOR PESQUISADO na página de dados.

O nome do servidor logado (menu) difere do servidor cujos dados são
buscados; o portal mostra o nome correto no topo da página de scraping.
Este script faz login, navega até a página de dados do CPF do .env
(TEST_PONTO_CPF) e lista todos os elementos com texto, além de salvar
o HTML completo para análise.
"""
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By  # noqa: E402

from backend.core.scraper import build_search_url  # noqa: E402
from backend.core.auth_core import login_service  # noqa: E402


def _read_env(key: str) -> str:
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return ''


def main() -> int:
    cpf = _read_env('TEST_PONTO_CPF')
    unit = _read_env('TEST_PONTO_UNIT')
    month = int(_read_env('TEST_PONTO_MONTH_START'))
    year = int(_read_env('TEST_PONTO_YEAR_START'))

    print('Login no portal... (resolva o captcha na janela do Chrome se abrir)')
    status, driver = login_service(headless=False, manual_solve_wait=180)
    if driver is None or status not in ('session_active', 'success'):
        print(f'Login falhou: {status}')
        return 1

    url = build_search_url(cpf=cpf, month=month, year=year, unit=unit)
    print('URL:', url)
    driver.get(url)

    html_path = ROOT / '_page_source2.html'
    html_path.write_text(driver.page_source, encoding='utf-8', errors='ignore')
    print(f'HTML salvo em {html_path}')

    print('=== Elementos com texto na página (filtrado) ===')
    for tag in ('font', 'span', 'strong', 'b', 'h1', 'h2', 'h3', 'td', 'th', 'a'):
        try:
            elements = driver.find_elements(By.TAG_NAME, tag)
            for el in elements:
                text = el.text.strip()
                if text and len(text) > 3:
                    print(f'[{tag}] {text[:120]!r}')
        except Exception as e:
            print(f'[{tag}] ERRO: {e}')

    driver.quit()
    return 0


if __name__ == '__main__':
    sys.exit(main())
