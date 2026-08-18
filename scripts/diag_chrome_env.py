# -*- coding: utf-8 -*-
"""Diagnóstico do Chrome no ambiente de trabalho (rodar NA maquina que falha)."""
import json
import os
import subprocess
import tempfile
import sys
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO))

print('=' * 70)
print('1) VERSAO DO CHROME (binario instalado)')
print('=' * 70)
cands = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]
for c in cands:
    if os.path.exists(c):
        try:
            v = subprocess.run([c, '--version'], capture_output=True, text=True, timeout=10)
            print(f'{c}  ->  {v.stdout.strip() or v.stderr.strip()}')
        except Exception as e:
            print(f'{c}  ->  erro: {e}')

print()
print('=' * 70)
print('2) VERSAO DO CHROMEDRIVER gerenciada pelo Selenium Manager')
print('=' * 70)
try:
    from selenium import __version__
    print('selenium:', __version__)
except Exception as e:
    print('selenium import erro:', e)
from selenium.webdriver.common.selenium_manager import SeleniumManager
sm = SeleniumManager()
try:
    cache = Path.home() / '.cache' / 'selenium' / 'chromedriver'
    for f in sorted(cache.rglob('chromedriver.exe'), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
        out = subprocess.run([str(f), '--version'], capture_output=True, text=True, timeout=10)
        print(f, '->', (out.stdout or out.stderr).strip())
except Exception as e:
    print('driver cache scan erro:', e)

print()
print('=' * 70)
print('3) PROCESSOS CHROME/EDGE ATIVOS (quantos e se usam nosso perfil)')
print('=' * 70)
ps = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe' } | "
     "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
    capture_output=True, text=True, timeout=30, errors='replace')
if ps.returncode == 0:
    data = json.loads(ps.stdout or '[]')
    if isinstance(data, dict):
        data = [data]
    print('total chrome/edge:', len(data))
    ours = [p for p in data if 'ponto_sms_flet' in (p.get('CommandLine') or '').lower()]
    print('processos com nosso perfil:', len(ours))
    for p in ours[:20]:
        print('  PID', p.get('ProcessId'), (p.get('CommandLine') or '')[:180])
else:
    print('query falhou:', ps.stderr[:300])

print()
print('=' * 70)
print('4) POLITICAS DE GRUPO DO CHROME/EDGE (bloqueios corporativos)')
print('=' * 70)
keyranges = [
    r'HKLM:\SOFTWARE\Policies\Google\Chrome',
    r'HKCU:\SOFTWARE\Policies\Google\Chrome',
    r'HKLM:\SOFTWARE\Policies\Microsoft\Edge',
    r'HKCU:\SOFTWARE\Policies\Microsoft\Edge',
]
import winreg  # noqa: E402
interesting = ['RemoteDebuggingAllowed', 'DeveloperToolsAvailability', 'HeadlessMode',
               'BruteForceProtectionEnabled', 'LaunchBugCheck', 'DisableChromeApps',
               'PasswordManagerEnabled', 'ProxyMode', 'BlockThirdPartyCookies']
for key in keyranges:
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE if 'HKLM' in key else winreg.HKEY_CURRENT_USER,
                           key.split(':', 1)[1])
    except Exception:
        continue
    print(f'[politicas] {key}')
    try:
        i = 0
        while True:
            name, value, _ = winreg.EnumValue(k, i)
            if name in interesting or 'debug' in name.lower() or 'devtools' in name.lower():
                print(f'   {name} = {value}')
            i += 1
    except OSError:
        pass

print()
print('=' * 70)
print('5) TESTE MINIMO: Janela Chrome com perfil NOVO descartavel, log verbose')
print('=' * 70)
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service  # noqa: E402
from backend.core.browser_session import build_chrome_options  # noqa: E402

tmp = tempfile.mkdtemp(prefix='chromeprobe_')
opts = build_chrome_options(profile_dir=tmp, headless=False)
opts.add_argument('--enable-logging=stderr')
srv = Service(service_args=['--verbose', f'--log-path={Path(tmp) / "cd.log"}'])
try:
    drv = webdriver.Chrome(options=opts, service=srv)
    drv.get('data:,ok')
    print('OK driver conectou. title=', repr(drv.title))
    drv.quit()
    print('perfil tmp:', tmp)
except Exception as e:
    print('FALHOU ao conectar driver:')
    print(str(e)[:1000])
    log = Path(tmp) / 'cd.log'
    if log.exists():
        lines = [ln.strip() for ln in log.read_text(encoding='utf-8', errors='replace').splitlines()]
        print('--- chromedriver verbose (linhas nao-histograma) ---')
        for ln in lines:
            if ln and 'Histogram' not in ln and not ln.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')) \
               and '------O' not in ln and '-O' not in ln and '...' not in ln:
                print(ln[:250])
    print('perfil tmp:', tmp)
print()
print('Diagnostico concluido.')