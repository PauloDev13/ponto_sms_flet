# -*- coding: utf-8 -*-
"""Diagnostico aprofundado: isola qual flag do Chrome causa o crash.
Roda NA VM que falha.
"""
import os
import subprocess
import tempfile
import time
from pathlib import Path

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

# Flags que build_chrome_options adiciona SEMPRE (estabilidade)
STABILITY_FLAGS = [
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--disable-extensions',
    '--disable-notifications',
    '--lang=pt-BR',
    '--remote-debugging-port=0',
]

# Flags que build_chrome_options adiciona em modo NORMAL (nao headless)
NORMAL_FLAGS = [
    '--window-size=1280,900',
    '--disable-blink-features=AutomationControlled',
]

# Flags que Selenium ChromeDriver adiciona AUTOMATICAMENTE
CHROMEDRIVER_AUTO_FLAGS = [
    '--disable-background-networking',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-extensions',
    '--disable-hang-monitor',
    '--disable-ipc-flooding-protection',
    '--disable-popup-blocking',
    '--disable-prompt-on-repost',
    '--disable-sync',
    '--disable-domain-reliability',
    '--metrics-recording-only',
    '--no-first-run',
]

# Stealth flags do projeto
STEALTH_FLAGS = [
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
]


def test_chrome(label: str, extra_flags: list[str], timeout: float = 5.0) -> dict:
    """Lanca Chrome com flags extras e observa se sobrevive."""
    tmp = tempfile.mkdtemp(prefix=f'diag_{label}_')
    cmd = [CHROME, f'--user-data-dir={tmp}'] + extra_flags + ['about:blank']
    stderr_file = os.path.join(tmp, 'stderr.txt')
    result = {'label': label, 'cmd': ' '.join(cmd[:8]) + '...', 'alive': False, 'exit': None, 'stderr_tail': ''}
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=open(stderr_file, 'w', encoding='utf-8', errors='replace'),
        )
        time.sleep(timeout)
        poll = p.poll()
        if poll is None:
            result['alive'] = True
            subprocess.run(['taskkill', '/PID', str(p.pid), '/F', '/T'],
                           capture_output=True, timeout=15)
        else:
            result['exit'] = poll
            try:
                txt = Path(stderr_file).read_text(encoding='utf-8', errors='replace')
                lines = txt.strip().splitlines()
                result['stderr_tail'] = '\n'.join(lines[-5:])
            except Exception:
                pass
    except Exception as e:
        result['stderr_tail'] = str(e)
    return result


def main():
    print('=' * 70)
    print('DIAGNOSTICO DE FLAGS - Qual flag mata o Chrome?')
    print('=' * 70)

    tests = [
        # Grupo 0: Baseline
        ('00_baseline', [], 'Chrome puro, sem nenhuma flag'),

        # Grupo 1: Flags de estabilidade individualmente
        ('01_no_sandbox', ['--no-sandbox'], ''),
        ('02_disable_gpu', ['--disable-gpu'], ''),
        ('03_disable_dev_shm', ['--disable-dev-shm-usage'], ''),
        ('04_disable_ext', ['--disable-extensions'], ''),
        ('05_remote_port', ['--remote-debugging-port=0'], ''),
        ('06_lang', ['--lang=pt-BR'], ''),

        # Grupo 2: Estabilidade combinada
        ('07_stability_all', STABILITY_FLAGS, 'Todas as stability flags'),

        # Grupo 3: ChromeDriver auto flags individualmente
        ('08_bg_networking', ['--disable-background-networking'], ''),
        ('09_bg_timer', ['--disable-background-timer-throttling'], ''),
        ('10_bg_occluded', ['--disable-backgrounding-occluded-windows'], ''),
        ('11_component_update', ['--disable-component-update'], ''),
        ('12_default_apps', ['--disable-default-apps'], ''),
        ('13_hang_monitor', ['--disable-hang-monitor'], ''),
        ('14_ipc_flood', ['--disable-ipc-flooding-protection'], ''),
        ('15_popup_block', ['--disable-popup-blocking'], ''),
        ('16_no_first_run', ['--no-first-run'], ''),
        ('17_metrics_only', ['--metrics-recording-only'], ''),

        # Grupo 4: Estabilidade + ChromeDriver auto
        ('18_stability_chromedriver', STABILITY_FLAGS + CHROMEDRIVER_AUTO_FLAGS, ''),

        # Grupo 5: Estabilidade + stealth
        ('19_stability_stealth', STABILITY_FLAGS + STEALTH_FLAGS, ''),

        # Grupo 6: Estabilidade + ChromeDriver + stealth (o que o projeto usa)
        ('20_full_project', STABILITY_FLAGS + CHROMEDRIVER_AUTO_FLAGS + STEALTH_FLAGS, 'Config completa do projeto'),

        # Grupo 7: Só o que SOBREVIVEU no diag anterior
        ('21_debug_port_9225', [
            '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--enable-automation', '--remote-debugging-port=9225',
            '--disable-extensions',
        ], 'O que sobreviveu antes'),

        # Grupo 8: Testes de isolamento (porta fixa vs --enable-automation)
        ('22_port9225_only', [
            '--remote-debugging-port=9225',
        ], 'Só porta fixa, sem mais nada'),
        ('23_port9225_no_sandbox', [
            '--no-sandbox', '--remote-debugging-port=9225',
        ], 'Porta fixa + no-sandbox'),
        ('24_enable_automation_only', [
            '--enable-automation',
        ], 'Só enable-automation, sem porta fixa'),
        ('25_stability_port9225', [
            '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--remote-debugging-port=9225',
        ], 'Estabilidade + porta fixa (SEM enable-automation)'),
        ('26_stability_port9225_ext', [
            '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--disable-extensions', '--remote-debugging-port=9225',
        ], 'Estabilidade + ext + porta fixa'),
    ]

    results = []
    for label, flags, desc in tests:
        desc_str = f'  ({desc})' if desc else ''
        print(f'\n--- {label}{desc_str}')
        r = test_chrome(label, flags)
        status = 'VIVO' if r['alive'] else f'MORREU (exit={r["exit"]})'
        print(f'  {status}')
        if not r['alive'] and r['stderr_tail']:
            for ln in r['stderr_tail'].splitlines():
                print(f'    {ln[:200]}')
        results.append(r)

    print('\n' + '=' * 70)
    print('RESUMO')
    print('=' * 70)
    for r in results:
        status = 'VIVO' if r['alive'] else 'MORREU'
        print(f'  {r["label"]:30s} {status}')

    # Identificar a flag maldita
    alive_baseline = any(r['alive'] for r in results if r['label'] == '00_baseline')
    if alive_baseline:
        print('\nO Chrome SEM nenhuma flag SOBREVIVE. O problema e uma flag especifica.')
        print('Compare os grupos VIVOS vs MORRADOS para isolar a flag.')
    else:
        print('\nO Chrome SEM nenhuma flag MORRE. Problema NAO e flag - e ambiente.')
        print('Verifique: antivirus, sandbox do Windows, permissoes de execucao.')

    print('\nDiagnostico concluido.')


if __name__ == '__main__':
    main()
