"""Teste manual do endpoint POST /api/v1/ponto usando os dados do .env.

Lê as variáveis TEST_PONTO_* do .env (LGPD: o CPF não fica no histórico),
chama o endpoint e salva o ZIP retornado em tests/out/.

Uso:
    python scripts/test_ponto_endpoint.py [--host 127.0.0.1] [--port 8000] [--timeout 600]
"""
import argparse
import io
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
import requests

load_dotenv(ROOT / '.env')


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, '')
    if value == '':
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'sim')


def main() -> int:
    parser = argparse.ArgumentParser(description='Testa o endpoint /api/v1/ponto')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    parser.add_argument('--timeout', default=600, type=int,
                        help='Timeout em segundos (scraping real é lento)')
    args = parser.parse_args()

    cpf = os.getenv('TEST_PONTO_CPF', '').strip()
    unit = os.getenv('TEST_PONTO_UNIT', '').strip()
    month_start = os.getenv('TEST_PONTO_MONTH_START', '').strip()
    year_start = os.getenv('TEST_PONTO_YEAR_START', '').strip()
    month_end = os.getenv('TEST_PONTO_MONTH_END', '').strip()
    year_end = os.getenv('TEST_PONTO_YEAR_END', '').strip()

    missing = [
        name for name, value in {
            'TEST_PONTO_CPF': cpf,
            'TEST_PONTO_UNIT': unit,
            'TEST_PONTO_MONTH_START': month_start,
            'TEST_PONTO_YEAR_START': year_start,
            'TEST_PONTO_MONTH_END': month_end,
            'TEST_PONTO_YEAR_END': year_end,
        }.items() if not value
    ]
    if missing:
        print(f'ERRO: preencha no .env: {", ".join(missing)}')
        return 1

    body = {
        'cpf': cpf,
        'unit': unit,
        'date_start': f'{month_start}/{year_start}',
        'date_end': f'{month_end}/{year_end}',
        'excel': _env_bool('TEST_PONTO_EXCEL', True),
        'pdf': _env_bool('TEST_PONTO_PDF', True),
    }

    url = f'http://{args.host}:{args.port}/api/v1/ponto'
    print(f'POST {url}')
    print(f'  período: {body["date_start"]} a {body["date_end"]} | '
          f'excel={body["excel"]} pdf={body["pdf"]}')

    try:
        response = requests.post(url, json=body, timeout=args.timeout)
    except requests.RequestException as e:
        print(f'ERRO na requisição: {e}')
        return 1

    if response.status_code != 200:
        try:
            payload = response.json()
            print(f'FALHA ({response.status_code}): {payload.get("message", payload)}')
        except ValueError:
            print(f'FALHA ({response.status_code}): resposta não-JSON')
        return 1

    out_dir = ROOT / 'tests' / 'out'
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f'ponto_test_{datetime.now():%Y%m%d_%H%M%S}.zip'
    zip_path.write_bytes(response.content)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = zf.namelist()

    print(f'OK! ZIP salvo em: {zip_path}')
    print(f'Conteúdo ({len(names)} arquivo(s)):')
    for name in names:
        info = zf.getinfo(name)
        print(f'  - {name} ({info.file_size / 1024:.1f} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
