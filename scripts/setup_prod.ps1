<#
.SYNOPSIS
  Prepara a VM Windows de producao com o ambiente web do ponto eletronico.

.DESCRIPTION
  Runbook idempotente da Parte D (FASE 5). Executa com seguranca mais de
  uma vez sem quebrar nada:
    1. Valida Python 3.10+ instalado.
    2. Cria/atualiza o venv (".venv" na raiz) e instala requirements-web.txt.
    3. Checa navegador (Chrome/Edge) e Ghostscript (gswin64c) disponiveis.
    4. Garante data/unidades.csv presente (o CSV nao pode existir sem isso).
    5. Cria o .env a partir de .env.example se ainda nao existir (NUNCA
       sobrescreve credenciais ja configuradas).

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
# 0) Exclusoes do Windows Defender (contorna bloqueio de automacao Selenium)
# ---------------------------------------------------------------------------
# O Windows Defender (MsMpEng) em ambientes corporativos pode matar o Chrome
# quando o Selenium ChromeDriver o inicia com flags automaticas. Adicionar
# os diretorios do projeto na lista de exclusoes resolve o problema.
$ExclusionPaths = @(
    $Root,                                          # projeto inteiro
    (Join-Path $env:USERPROFILE '.cache\selenium'), # ChromeDriver cache
    (Join-Path $env:USERPROFILE '.ponto_sms_flet')  # perfil Chrome/Edge
)

try {
    $CurrentExclusions = (Get-MpPreference -ErrorAction SilentlyContinue).ExclusionPath
} catch {
    $CurrentExclusions = @()
}

foreach ($Path in $ExclusionPaths) {
    if ($Path -notin $CurrentExclusions) {
        try {
            Add-MpPreference -ExclusionPath $Path -ErrorAction Stop
            Write-Step "Defender exclusion added: $Path"
        } catch {
            Write-Warning "Nao foi possivel adicionar exclusao Defender para $Path : $_"
        }
    } else {
        Write-Step "Defender exclusion already present: $Path"
    }
}

# ---------------------------------------------------------------------------
# 1) Python do sistema
# ---------------------------------------------------------------------------
# O comando 'python' pode resolver o stub 0-byte da Microsoft Store
# (WindowsApps\python.exe), que nao e um Python real. Preferimos o launcher
# 'py -3' (habilitado pelo install_python.ps1) e validamos que o caminho
# encontrado realmente executa.
function Resolve-RealPython {
    $candidates = New-Object System.Collections.Generic.List[string]

    # 1a. Launcher py -3 (aponta sempre para um Python REAL instalado)
    try {
        $out = (& py -3 -c "import sys; print(sys.executable)" 2>&1 | Out-String).Trim()
        if ($out -match '^[A-Za-z]:\\' -and (Test-Path $out)) { $candidates.Add($out) }
    } catch { }

    # 1b. 'python' no PATH, descartando o alias do WindowsApps
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch 'AppData\\Local\\Microsoft\\WindowsApps') {
        $candidates.Add($cmd.Source)
    }

    # 1c. Instalacoes registradas no Windows (HKLM/HKCU)
    foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore', 'HKCU:\SOFTWARE\Python\PythonCore')) {
        $roots = Get-ChildItem -Path $hive -ErrorAction SilentlyContinue | Where-Object Name -match '3\.'
        foreach ($r in $roots) {
            $installKey = Join-Path $r.PSPath 'InstallPath'
            $path = (Get-ItemProperty -Path $installKey -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
            $exe = Join-Path $path 'python.exe'
            if (Test-Path $exe) { $candidates.Add($exe) }
        }
    }

    foreach ($p in ($candidates | Select-Object -Unique)) {
        try {
            $ver = (& $p --version 2>&1 | Out-String).Trim()
            if ($ver -match '\d+\.\d+') { return @{ Exe = $p; Version = $ver } }
        } catch { }
    }
    return $null
}

$Py = Resolve-RealPython
if (-not $Py) {
    throw 'Python 3.10+ nao encontrado. Rode primeiro: scripts\install_python.ps1 e abra um NOVO terminal.'
}
Write-Step "Python base: $($Py.Exe)  ($($Py.Version))"

# ---------------------------------------------------------------------------
# 2) venv + dependencias web
# ---------------------------------------------------------------------------
if (-not (Test-Path $PythonVenv)) {
    Write-Step "Criando venv em $Venv ..."
    & $Py.Exe -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o venv com $($Py.Exe)."
    }
} else {
    Write-Step "venv ja existe ($Venv) - pulando criacao."
}

if (-not (Test-Path $PipVenv)) {
    throw "pip.exe nao encontrado em $PipVenv. O venv nao foi criado corretamente."
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