<#
.SYNOPSIS
  Instala a aplicacao web como servico Windows via NSSM (Parte D2, FASE 5).

.DESCRIPTION
  - Usa o NSSM para criar o servico "PontoSmsWeb".
  - Executa uvicorn com o python do venv da raiz, host 0.0.0.0 porta 8000.
  - Configura autorestart (restart automatico em falha) e logs em
    C:\ProgramData\PontoSmsWeb\logs.
  - Se o servico ja existir, apenas reaplica as configuracoes (idempotente).

.PARAMETER ServiceName
  Nome do servico (padrao: PontoSmsWeb).

.PARAMETER NssmExe
  Caminho do nssm.exe (padrao: tenta nssm no PATH).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1
#>
[CmdletBinding()]
param(
    [string]$ServiceName = 'PontoSmsWeb',
    [string]$NssmExe = ''
)

$ErrorActionPreference = 'Stop'

if (-not $NssmExe) {
    $cmd = Get-Command nssm -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw 'nssm.exe nao encontrado. Instale o NSSM (https://nssm.cc) e adicione ao PATH ou passe -NssmExe.'
    }
    $NssmExe = $cmd.Source
}
Write-Host "==> NSSM: $NssmExe" -ForegroundColor Cyan

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    throw "venv nao encontrado ($Python). Execute scripts\setup_prod.ps1 antes."
}

$WorkDir = $Root
$Args = @('-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000')
$LogDir = 'C:\ProgramData\PontoSmsWeb\logs'

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Idempotente: remove para reinstalar limpo (a config e reaplicada abaixo).
& $NssmExe stop $ServiceName | Out-Null
& $NssmExe remove $ServiceName confirm | Out-Null

& $NssmExe install $ServiceName $Python
& $NssmExe set $ServiceName AppParameters ($Args -join ' ')
& $NssmExe set $ServiceName AppDirectory $WorkDir
& $NssmExe set $ServiceName DisplayName 'Ponto Eletronico SMS - Web'
& $NssmExe set $ServiceName Description 'API web de consulta de ponto eletronico (FastAPI)'
& $NssmExe set $ServiceName Start SERVICE_AUTO_START
& $NssmExe set $ServiceName AppStdout (Join-Path $LogDir 'out.log')
& $NssmExe set $ServiceName AppStderr (Join-Path $LogDir 'err.log')
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateBytes 10485760

# Autorestart: reinicia automaticamente em caso de falha (apos 5s).
& $NssmExe set $ServiceName AppExit Default Restart
& $NssmExe set $ServiceName AppRestartDelay 5000

# ---------------------------------------------------------------------------
# Verificacao pre-start: sessao do portal
# ---------------------------------------------------------------------------
$CookieFile = Join-Path $env:USERPROFILE '.ponto_sms_flet\cookies.json'
if (-not (Test-Path $CookieFile)) {
    Write-Warning "cookies.json NAO encontrado em $CookieFile"
    Write-Warning "A sessao do portal nao foi criada. O servico vai precisar de login manual (captcha)."
    Write-Warning "Recomendado: cancele o servico, rode pre_login.py com desktop interativo e volte."
} else {
    Write-Host "==> Sessao do portal encontrada ($CookieFile)." -ForegroundColor Cyan
}

& $NssmExe start $ServiceName

Write-Host "==> Servico '$ServiceName' instalado e iniciado." -ForegroundColor Green
Write-Host "==> Acompanhe: sc query $ServiceName | Get-Service PontoSmsWeb"
Write-Host "==> Logs: $LogDir"