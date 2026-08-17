"""Teste manual do endpoint /api/v1/ponto com os dados do .env.

Lê TEST_PONTO_* do .env, chama a API local, salva o ZIP e extrai os
arquivos gerados em teste_arquivos/ para inspeção.

Uso:
    python -u scripts/test_endpoint.py
"""
import io
import os
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'teste_arquivos'


def _read_env(key: str) -> str:
    value = os.getenv(key, '')
    if value:
        return value
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
    start = f"{_read_env('TEST_PONTO_MONTH_START')}/{_read_env('TEST_PONTO_YEAR_START')}"
    end = f"{_read_env('TEST_PONTO_MONTH_END')}/{_read_env('TEST_PONTO_YEAR_END')}"
    excel = _read_env('TEST_PONTO_EXCEL').lower() in ('true', '1', 'yes')
    pdf = _read_env('TEST_PONTO_PDF').lower() in ('true', '1', 'yes')

    payload = {
        'cpf': cpf,
        'unit': unit,
        'date_start': start,
        'date_end': end,
        'excel': excel,
        'pdf': pdf,
    }
    print(f'POST /api/v1/ponto  cpf=***{cpf[-4:]} unit={unit} '
          f'{start} -> {end} excel={excel} pdf={pdf}')
    print('Aguardando login/captcha... (resolva na janela do Chrome se abrir)')

    resp = requests.post('http://127.0.0.1:8000/api/v1/ponto', json=payload, timeout=1800)
    print(f'HTTP {resp.status_code}')

    if resp.status_code != 200:
        print(resp.text)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUT_DIR / 'resposta.zip'
    zip_path.write_bytes(resp.content)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(OUT_DIR)
    print(f'Arquivos extraídos em: {OUT_DIR}')
    for p in sorted(OUT_DIR.iterdir()):
        if p.name != 'resposta.zip':
            print(f'  - {p.name}  ({p.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
