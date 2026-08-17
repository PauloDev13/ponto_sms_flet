"""Diagnóstico: descobre onde o nome do funcionário aparece nas páginas de dados.

Abre a página de busca de um mês (cpf/unidade do .env) e imprime o texto
encontrado para vários seletores candidatos, além do HTML do bloco do nome.

Uso:
    python -u scripts/debug_nome.py [--port 8765]
"""
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / '.env')

from backend.app.session_manager import get_driver  # noqa: E402
from backend.core.scraper import build_search_url  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402


CANDIDATES = [
    '/html/body/div[2]/div/div[2]/div[2]/div[4]/div/span/font[1]',
    '//*[@id="foto"]',
    '//*[@id="foto"]//span',
    '//span[contains(@id, "_nome")]',
    '//div[contains(@class, "foto")]//font',
]


def main() -> int:
    cpf = re_only_digits(os.getenv('TEST_PONTO_CPF', ''))
    unit = os.getenv('TEST_PONTO_UNIT', '').strip()
    if not cpf or not unit:
        print('ERRO: preencha TEST_PONTO_CPF e TEST_PONTO_UNIT no .env')
        return 1

    driver = get_driver()
    url = build_search_url(cpf=cpf, month=1, year=2023, unit=unit)
    print(f'URL: {url}')
    driver.get(url)

    for xpath in CANDIDATES:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            texts = [el.text.strip() for el in elements if el.text.strip()]
            print(f'[{xpath}] -> {texts if texts else "(sem texto)"}')
        except Exception as e:
            print(f'[{xpath}] -> ERRO: {e}')

    # HTML do bloco pai do font[1] (estrutura real da página)
    try:
        node = driver.find_element(By.XPATH, CANDIDATES[0])
        parent = node.find_element(By.XPATH, '..')
        html = parent.get_attribute('outerHTML')
        print('=== HTML do bloco pai do nome (primeiros 1500 chars) ===')
        print(html[:1500])

        # Sobe mais um nível (header da página)
        try:
            grandparent = node.find_element(By.XPATH, '../../..')
            print('=== HTML do bloco acima (2000 chars) ===')
            print(grandparent.get_attribute('outerHTML')[:2000])
        except Exception:
            pass
    except Exception as e:
        print(f'Bloco pai não localizado: {e}')

    # Salva o HTML completo para análise local
    html_path = ROOT / '_page_source.html'
    html_path.write_text(driver.page_source, encoding='utf-8', errors='ignore')
    print(f'=== page_source salvo em {html_path} ===')

    # Verifica a página interna inicial (pode conter o nome)
    print('=== Navegando para URL_INIT ===')
    from config.config_env import URL_INIT  # noqa: E402
    driver.get(URL_INIT)
    print(f'URL atual: {driver.current_url}')

    for tag, attr in [('font', ''), ('span', ''), ('a', '')]:
        try:
            elements = driver.find_elements(By.TAG_NAME, tag)
            texts = [el.text.strip() for el in elements if el.text.strip() and len(el.text.strip()) > 5]
            if texts:
                print(f'<{tag}> textos: {texts[:20]}')
        except Exception as e:
            print(f'<{tag}> ERRO: {e}')

    html_path2 = ROOT / '_page_source_init.html'
    html_path2.write_text(driver.page_source, encoding='utf-8', errors='ignore')
    print(f'=== page_source (inicio) salvo em {html_path2} ===')

    driver.quit()
    return 0


import re  # noqa: E402


def re_only_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


if __name__ == '__main__':
    sys.exit(main())