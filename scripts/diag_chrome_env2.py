# -*- coding: utf-8 -*-
"""FASE 2 - convergir o motivo do Chrome morrer em ~0,1s na maquina remota.
Roda NA maquina que falha. ISOLA as variaveis: flags de automacao, EDR, versao.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO))

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

print('=' * 70)
print('1) VERSAO DO CHROME real (via VersionInfo, nao executa o binario)')
print('=' * 70)
try:
    vi = Path(CHROME).stat()
    md = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         f"(Get-Item '{CHROME}').VersionInfo | Select-Object FileVersion,ProductVersion,ProductName | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=15)
    print(md.stdout.strip())
    if md.stderr.strip():
        print('ERR:', md.stderr[:200])
except Exception as e:
    print('erro:', e)

print()
print('=' * 70)
print('2) AGENTES DE SEGURANCA / EDR presentes')
print('=' * 70)
agents = ['MsMpEng', 'MsMpEngCP', 'mpcmdrun', 'SenseNdr', 'SentinelAgent',
          'CrowdStrike', 'CSAgent', 'csfalconservice', 'CiscoAMP', 'ampc',
          'TaniumClient', 'SymantecEndpoint', 'sep', 'SophosAgent', 'EndpointSecurity']
found = []
for name in agents:
    try:
        r = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {name}.exe'],
                           capture_output=True, text=True, timeout=15)
        if name.lower() in r.stdout.lower():
            found.append(name)
    except Exception:
        pass
print('agent. de EDR detectados:', found if found else 'NENHUM conhecido')
try:
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        'Get-MpComputerStatus | Select-Object AntivirusEnabled,AntivirusSignatureLastUpdated,RealTimeProtectionEnabled | ConvertTo-Json -Compress'],
                       capture_output=True, text=True, timeout=30)
    if r.returncode == 0 and r.stdout.strip():
        mp = json.loads(r.stdout)
        print('Windows Defender:', mp if isinstance(mp, dict) else 'indisponivel')
    else:
        print('Windows Defender: indisponivel (sem cmdlet Defender?)')
except Exception as e:
    print('defender scan erro:', e)

print()
print('=' * 70)
print('3) TESTE HEADLESS (sem janela) - se passar, EDR mira janela/estado')
print('=' * 70)
from selenium import webdriver  # noqa: E402
from backend.core.browser_session import build_chrome_options  # noqa: E402
try:
    tmp = tempfile.mkdtemp(prefix='chromeprobe_h_')
    opts = build_chrome_options(profile_dir=tmp, headless=True)
    drv = webdriver.Chrome(options=opts)
    drv.get('data:,ok')
    print('HEADLESS OK: conectou. title:', repr(drv.title))
    drv.quit()
except Exception as e:
    print('HEADLESS FALHOU:', str(e)[:300])

print()
print('=' * 70)
print('4) TESTE MANUAL: chrome.exe com perfil novo, flags do chromedriver')
print('    Observa se o processo SOBREVIVE 5s e coleta stderr.')
print('=' * 70)
testes = {
    'A_sem_flags': [],
    'B_flags_automacao': [
        '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--enable-automation', '--remote-debugging-port=9225', '--disable-extensions'],
    'C_flags_estabilidade': [
        '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
}
for nome, flags in testes.items():
    tmp = tempfile.mkdtemp(prefix=f'chromeprobe_{nome}_')
    stderr_file = tmp + '_stderr.txt'
    cmd = [CHROME, '--user-data-dir=' + tmp] + flags + ['about:blank']
    print(f'--- {nome}')
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=open(stderr_file, 'w', encoding='utf-8', errors='replace'))
        time.sleep(5)
        poll = p.poll()
        if poll is None:
            print('  SOBREVIVEU 5s (processo vivo, PID', p.pid, ') -> killing')
            subprocess.run(['taskkill', '/PID', str(p.pid), '/F', '/T'],
                           capture_output=True, text=True, timeout=15)
        else:
            print(f'  MORREU em <5s (exit={poll}) -> Chrome terminado sozinho')
            try:
                txt = Path(stderr_file).read_text(encoding='utf-8', errors='replace')
                tail = '\n'.join(txt.strip().splitlines()[-8:])
                print('  stderr (last 8):')
                for ln in tail.splitlines():
                    print('   ', ln[:200])
            except Exception as e:
                print('  sem stderr:', e)
    except Exception as e:
        print('  erro ao lancar:', e)

print()
print('=' * 70)
print('5) EVENT LOG: crashes do chrome.exe nas ultimas 4h')
print('=' * 70)
try:
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001; StartTime=(Get-Date).AddHours(-4)} -ErrorAction SilentlyContinue | "
         "Where-Object { $_.Message -match 'chrome' } | Select-Object -First 6 TimeCreated,Id | Format-List"],
        capture_output=True, text=True, timeout=40)
    print(r.stdout.strip() or 'Nenhum crash registrado em 4h.')
    if r.stderr.strip() and 'Nenhum' not in r.stdout:
        print('ERR:', r.stderr[:200])
except Exception as e:
    print('event log erro:', e)

print()
print('Diagnostico FASE 2 concluido.')