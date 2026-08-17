<#
.SYNOPSIS
  Prepara a VM Windows de produção com o ambiente web do ponto eletrônico.

.DESCRIPTION
  Runbook idempotente da Parte D (FASE 5). Executa com segurança mais de
  uma vez sem quebrar nada:
    1. Valida Python 3.10+ instalado.
    2. Cria/atualiza o venv (".venv" na raiz) e instala requirements-web.txt.
    3. Checa navegador (Chrome/Edge) e Ghostscript (gswin64c) disponíveis.
    4. Garante data/unidades.csv presente (o CSV não pode existir sem isso).
    5. Cria o .env a partir de .env.example se ainda não existir (NUNCA
       sobrescreve credenciais já configuradas).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Venv = Join-Path $Root '.venv'
$PythonVenv = Join-Path $Venv 'Scripts\python.exe'
$PipVenv = Join-Path $Venv 'Scripts\pip.exe'

function Write-Step { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }

Write-Step "Raiz do projeto: $Root"

# ---------------------------------------------------------------------------
# 1) Python do sistema
# ---------------------------------------------------------------------------
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    throw 'Python nao encontrado. Instale Python 3.10+ e adicione ao PATH.'
}
Write-Step "Python base: $Python"

# ---------------------------------------------------------------------------
# 2) venv + dependencias web
# ---------------------------------------------------------------------------
if (-not (Test-Path $PythonVenv)) {
    Write-Step "Criando venv em $Venv ..."
    & python -m venv $Venv
} else {
    Write-Step "venv ja existe ($Venv) - pulando criacao."
}

Write-Step 'Instalando/atualizando requirements-web.txt ...'
& $PipVenv install --upgrade pip --quiet
& $PipVenv install -r (Join-Path $Root 'requirements-web.txt')

# ---------------------------------------------------------------------------
# 3) Navegador + Ghostscript
# ---------------------------------------------------------------------------
$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$HasBrowser = (Test-Path $Chrome) -or (Test-Path $Edge)
if (-not $HasBrowser) {
    Write-Warning 'Nenhum navegador (Chrome/Edge) encontrado. O login pelo portal nao funcionara.'
} else {
    Write-Step 'Navegador Chrome/Edge disponivel.'
}

$Gswin = Get-Command gswin64c -ErrorAction SilentlyContinue
if (-not $Gswin) {
    Write-Warning 'Ghostscript (gswin64c) nao encontrado no PATH. A compressao de PDF usara o PDF original.'
} else {
    Write-Step "Ghostscript disponivel: $($Gswin.Source)"
}

# ---------------------------------------------------------------------------
# 4) CSV de unidades
# ---------------------------------------------------------------------------
$Csv = Join-Path $Root 'data\unidades.csv'
if (-not (Test-Path $Csv)) {
    throw "Faltando data/unidades.csv. Restaure o arquivo no repositorio e rode novamente."
}
Write-Step "CSV de unidades presente ($Csv)."

# ---------------------------------------------------------------------------
# 5) .env (nunca sobrescreve)
# ---------------------------------------------------------------------------
$EnvExample = Join-Path $Root '.env.example'
$EnvFile = Join-Path $Root '.env'
if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) {
        throw 'Faltando .env.example no repositorio.'
    }
    Copy-Item $EnvExample $EnvFile
    Write-Step ".env criado a partir de .env.example - preencha USER/PASSWORD/URL_*/WEB_USERS/SESSION_SECRET."
} else {
    Write-Step '.env ja existe - mantido (nao sobrescreve credenciais).'
}

Write-Step 'Setup concluido. Para rodar: .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000'