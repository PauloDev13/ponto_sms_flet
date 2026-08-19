<#
.SYNOPSIS
  Instala o Python 3.12 (a versao do projeto) em uma VM Windows 10/11 nova.

.DESCRIPTION
  - Fixa Python 3.12.10 (ultimo build 3.12 com instalador binario; releases
    3.12 posteriores sao "security-fixes only" e so existem em codigo-fonte,
    sem .exe para Windows).
  - Baixa o instalador oficial de python.org e instala em silencio
    (pip + py launcher + PATH).
  - Configura as variaveis de ambiente necessarias:
      * PATH            -> diretorio do Python e de scripts (pip/uvicorn)
      * PYTHONUTF8=1    -> UTF-8 padrao (evita corromper acentos/UTF-8 no
                           portal e nos arquivos gerados em pt-BR)
  - Idempotente: se ja existir Python 3.12.x no PATH/launcher, apenas
    confirma e sai.
  - Sem privilegios de admin, instala so para o usuario (e ajusta so o PATH
    do usuario); com admin, instala para Todos e ajusta o PATH da maquina
    (necessario para o servico NSSM rodar com o mesmo Python).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_python.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_python.ps1 -PythonVersion 3.12.10 -NoCleanup

.NOTES
  Depois de terminar, abra um NOVO PowerShell para o PATH valer.
  Verificacao rapida:  python --version   (esperado 3.12.x)
#>
[CmdletBinding()]
param(
    [string]$PythonVersion = '3.12.10',
    [string]$Arch = 'amd64',
    [switch]$InstallForAllUsers,    # forca instalacao para Todos (exige admin)
    [switch]$NoCleanup              # mantem o instalador baixado em %TEMP%
)

$ErrorActionPreference = 'Stop'
try { $ProgressPreference = 'SilentlyContinue' } catch { }

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# ---------------------------------------------------------------------------
# utilitarios
# ---------------------------------------------------------------------------
function Write-Step { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }
function Write-Warn  { param([string]$Msg) Write-Host "AVISO: $Msg" -ForegroundColor Yellow }

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PythonVersions {
    # Retorna versoes 3.x detectadas via 'python' e 'py' launcher.
    # Ignora pyenv (intercepta 'python' mas nao e Python real).
    $found = @()
    try {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notmatch 'pyenv') {
            $v = (& python --version 2>&1 | Out-String).Trim()
            if ($v -match '3\.') { $found += $v }
        }
    } catch { }
    try { $v = (& py -3 --version 2>&1 | Out-String).Trim();    if ($v -match '3\.') { $found += $v } } catch { }
    return $found
}

function Get-RegPythonPath {
    # Diretorio de instalacao de um Python 3.12 registrado (HKLM=Todos, HKCU=usuario).
    $majorMinor = $PythonVersion -replace '\.\d+$', ''   # "3.12.10" -> "3.12"
    foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore', 'HKCU:\SOFTWARE\Python\PythonCore')) {
        $key = "$hive\$majorMinor\InstallPath"
        if (Test-Path $key) {
            $value = (Get-ItemProperty -Path $key -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
            if ($value -and (Test-Path (Join-Path $value 'python.exe'))) { return $value }
        }
    }
    return $null
}

# ---------------------------------------------------------------------------
# 1) deteccao: ja tem Python 3.12?
# ---------------------------------------------------------------------------
Write-Step "Preparando Python $PythonVersion ($Arch)."

$has312 = (Get-PythonVersions) | Where-Object { $_ -match '^Python 3\.12' }
if ($has312) {
    Write-Step "Python 3.12 ja disponivel: $($has312 -join ' | '). Nada a fazer."
    exit 0
}
$regPath = Get-RegPythonPath
if ($regPath) {
    Write-Step "Python 3.12 ja instalado em $regPath (fora do PATH). Reutilizando este diretorio."
    $TargetDir = $regPath
    $SkipInstall = $true
} else {
    Write-Step 'Python 3.12 nao encontrado. Iniciando download/instalacao.'
    $SkipInstall = $false
}

# ---------------------------------------------------------------------------
# 2) escopo da instalacao (Todos x usuario)
# ---------------------------------------------------------------------------
$isAdmin = Test-IsAdmin
$allUsers = $false

if ($InstallForAllUsers) {
    if (-not $isAdmin) { Write-Warn 'Sem privilegios de admin; instalando para o USUARIO apenas.' }
    else { $allUsers = $true }
} elseif ($isAdmin) {
    Write-Step 'Executando como admin - instalando para TODOS os usuarios (recomendado para o servico NSSM).'
    $allUsers = $true
}

$majorMinor = $PythonVersion -replace '\.\d+$', ''
if (-not $SkipInstall) {
    $TargetDir = if ($allUsers) {
        "C:\Program Files\Python$($majorMinor -replace '\.', '')"
    } else {
        Join-Path $env:LOCALAPPDATA "Programs\Python\Python$($majorMinor -replace '\.', '')"
    }
}

# ---------------------------------------------------------------------------
# 3+4) download e instalacao (pulados quando reutilizando instalacao existente)
# ---------------------------------------------------------------------------
if (-not $SkipInstall) {
    $Installer = Join-Path $env:TEMP "python-$PythonVersion-$Arch.exe"
    $Url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-$Arch.exe"

    if (-not (Test-Path $Installer)) {
        Write-Step "Baixando $Url"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        try {
            Invoke-WebRequest -Uri $Url -OutFile $Installer -UseBasicParsing
        } catch {
            throw "Falha ao baixar o instalador. Verifique o acesso a internet e se '$PythonVersion' tem instalador .exe (3.12.10 e o ultimo com binario). Erro: $_"
        }
    } else {
        Write-Step "Instalador ja em cache: $Installer"
    }

    Write-Step "Instalando Python em $TargetDir (silencioso)..."

    $InstallArgs = @(
        '/quiet',
        'InstallAllUsers=' + $(if ($allUsers) { 1 } else { 0 }),
        'TargetDir="' + $TargetDir + '"',
        'PrependPath=1',
        'Include_launcher=1',
        'Include_pip=1',
        'Include_test=0',
        'Include_doc=1',
        'Include_debug=0',
        'Shortcuts=0',
        'SimpleInstall=0'
    )

    # 0 = sucesso; 3010 = sucesso com reinicializacao pendente (aceitavel)
    $proc = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru
    if ($proc.ExitCode -notin @(0, 3010)) {
        throw "Instalacao falhou (codigo $($proc.ExitCode)). Abra o instalador manualmente para ver a causa."
    }

    # O TargetDir pode ter caido em outro lugar (caminho com espacos, ex: 'C:\Program Files\...')
    if (-not (Test-Path (Join-Path $TargetDir 'python.exe'))) {
        $found = Get-RegPythonPath
        if ($found) {
            Write-Warn "python.exe nao estava em '$TargetDir'; usando a instalacao encontrada em '$found'."
            $TargetDir = $found
        } else {
            throw "python.exe nao encontrado em '$TargetDir' apos a instalacao (instalador retornou codigo $($proc.ExitCode)). " +
                  "Verifique o argumento TargetDir (deve incluir aspas se o caminho tiver espacos)."
        }
    }
}

# ---------------------------------------------------------------------------
# 5) variaveis de ambiente (PATH + PYTHONUTF8)
# ---------------------------------------------------------------------------
Write-Step 'Configurando variaveis de ambiente...'

if ($allUsers) {
    $envKey  = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    $scope   = 'Maquina (Todos)'
} else {
    $envKey  = 'HKCU:\Environment'
    $scope   = 'Usuario'
}
Write-Step "Escopo do ambiente: $scope"

$pythonRoot   = $TargetDir
$scriptsRoot  = Join-Path $pythonRoot 'Scripts'

# PATH atual do escopo (mantem %VAR% ja existentes)
$currentPath = (Get-ItemProperty -Path $envKey -Name Path -ErrorAction SilentlyContinue).Path
if (-not $currentPath) {
    $currentPath = [Environment]::GetEnvironmentVariable(
        'Path', $(if ($allUsers) { 'Machine' } else { 'User' }))
}

$pathParts = @($pythonRoot, $scriptsRoot)
foreach ($p in $pathParts) {
    if (($currentPath -split ';') -notcontains $p) {
        $currentPath = if ($currentPath) { "$currentPath;$p" } else { $p }
        Write-Step "PATH += $p"
    }
}
Set-ItemProperty -Path $envKey -Name Path -Value $currentPath -Type ExpandString

# PYTHONUTF8=1 (UTF-8 padrao; evita erros de acentuacao/encoding)
Set-ItemProperty -Path $envKey -Name PYTHONUTF8 -Value '1' -Type String
Write-Step 'PYTHONUTF8 = 1'

# ---------------------------------------------------------------------------
# 6) verificacao final
# ---------------------------------------------------------------------------
# Difunde para o processo atual (os scripts seguintes ja enxergam)
$env:PATH = "$pythonRoot;$scriptsRoot;$env:PATH"
$env:PYTHONUTF8 = '1'

$versionOut = (& (Join-Path $pythonRoot 'python.exe') --version 2>&1 | Out-String).Trim()
Write-Step "Instalacao concluida: $versionOut ($pythonRoot)"

if (-not $SkipInstall -and -not $NoCleanup) {
    Remove-Item -Path $Installer -Force -ErrorAction SilentlyContinue
    Write-Step 'Instalador temporario removido.'
}

Write-Host ''
Write-Host 'Proximos passos (NOVO PowerShell, para pegar o PATH):' -ForegroundColor Cyan
Write-Host "  1. cd $Root"
Write-Host '  2. powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1'
Write-Host '  3. Edite o .env com as credenciais do portal'
Write-Host '  4. powershell -ExecutionPolicy Bypass -File scripts\pre_login.py'
Write-Host ''
Write-Host 'Verifique com:  Get-Command python | Select Source ; python --version' -ForegroundColor Cyan