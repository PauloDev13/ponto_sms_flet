<#
.SYNOPSIS
  Instala a aplicacao web como servico Windows via NSSM (Parte D2, FASE 5).

.DESCRIPTION
  - Usa o NSSM para criar o servico "PontoSmsWeb".
  - Executa uvicorn com o python do venv da raiz, host 0.0.0.0 porta 8000.
  - Configura autorestart (restart automatico em falha) e logs em
    C:\ProgramData\PontoSmsWeb\logs.
  - Se o servico ja existir, apenas reaplica as configuracoes (idempotente).
  - Resolve o profile path real do usuario via registro do Windows
    (compativel com contas locais e de dominio AD).

.PARAMETER ServiceName
  Nome do servico (padrao: PontoSmsWeb).

.PARAMETER NssmExe
  Caminho do nssm.exe (padrao: tenta nssm no PATH).

.PARAMETER ServiceUser
  Conta que rodara o servico (ex: 'paulo.morais' ou 'PGM\paulo.morais').
  Se omitido, o servico roda como LocalSystem.

.PARAMETER ServicePassword
  Senha da conta de servico.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1 -ServiceUser 'paulo.morais' -ServicePassword 'senha'

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1 -ServiceUser 'PGM\paulo.morais' -ServicePassword 'senha'
#>
[CmdletBinding()]
param(
    [string]$ServiceName = 'PontoSmsWeb',
    [string]$NssmExe = '',
    [string]$ServiceUser = '',
    [string]$ServicePassword = ''
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Funcao auxiliar: resolve o profile path real do usuario no Windows
# ---------------------------------------------------------------------------
# Em vez de assumir C:\Users\<username> (que falha para usuarios de dominio
# com Folder Redirection ou profile em path alternativo), consulta o registro
# do Windows para obter o ProfileImagePath real associado ao SID da conta.
function Get-UserProfilePath {
    param([string]$AccountName)
    try {
        $ntAccount = New-Object System.Security.Principal.NTAccount($AccountName)
        $sid = $ntAccount.Translate([System.Security.Principal.SecurityIdentifier])
        $regKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$($sid.Value)"
        $profilePath = (Get-ItemProperty -Path $regKey -ErrorAction Stop).ProfileImagePath
        if ($profilePath -and (Test-Path $profilePath)) {
            return $profilePath
        }
    } catch {
        # Silencia: SID nao encontrado no registro (usuario nunca logou)
    }
    # Fallback: assume C:\Users\<username>
    $username = ($AccountName -split '\\')[-1]
    return "C:\Users\$username"
}

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
# Variaveis de ambiente do servico (HOME / USERPROFILE / HOMEDRIVE / HOMEPATH)
# ---------------------------------------------------------------------------
# Garante que Path.home() e os.path.expanduser('~') resolvam para o
# diretorio correto do usuario, necessario para que
# ~/.ponto_sms_flet/cookies.json e chrome_profile sejam encontrados.
# Sem isto, LocalSystem usa C:\Windows\system32\config\systemprofile\ como HOME.
# Para usuarios de dominio, o profile path real e obtido via registro do Windows
# (contorna Folder Redirection e profiles em path alternativo).
if ($ServiceUser) {
    $UserProfile = Get-UserProfilePath -AccountName $ServiceUser
    $Drive = $UserProfile.Substring(0, 1)
    $HomePath = $UserProfile.Substring(1)
    & $NssmExe set $ServiceName AppEnvironmentExtra `
        "HOME=$UserProfile" `
        "USERPROFILE=$UserProfile" `
        "HOMEDRIVE=$Drive" `
        "HOMEPATH=$HomePath" `
        "PYTHONUTF8=1"
    Write-Host "==> Variaveis de ambiente: HOME=$UserProfile, HOMEDRIVE=$Drive, HOMEPATH=$HomePath, PYTHONUTF8=1" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Conta do servico: roda como o usuario interativo ( Session 1+ / RDP )
# ---------------------------------------------------------------------------
# Quando roda como LocalSystem (padrao), o Chrome abre na Session 0 (invisivel)
# e Path.home() aponta para systemprofile (cookies nao encontrados).
# Rodar como o usuario garante: (1) Path.home() = C:\Users\<usuario> e
# (2) Chrome abre na sessao interativa do usuario (RDP), permitindo captcha.
if ($ServiceUser -and $ServicePassword) {
    # Conta de dominio (ex: PGM\paulo.morais) nao recebe .\ prefix
    # Conta local (ex: paulo.morais) recebe .\ prefix
    if ($ServiceUser -match '\\') {
        $NssmObjectName = $ServiceUser  # ja tem dominio\usuario
    } else {
        $NssmObjectName = ".\$ServiceUser"  # conta local
    }
    & $NssmExe set $ServiceName ObjectName $NssmObjectName $ServicePassword
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "FALHA ao configurar ObjectName. Verifique:"
        Write-Warning "  1. O usuario '$NssmObjectName' existe no AD/local?"
        Write-Warning "  2. A senha esta correta?"
        Write-Warning "  3. O usuario tem permissao 'Log on as a service'?"
        Write-Warning "     (Editor de Diretrizes de Seguranca Local -> Atribuicao de Direitos de Usuario)"
    } else {
        Write-Host "==> Servico configurado para rodar como: $NssmObjectName" -ForegroundColor Cyan
    }
} else {
    Write-Warning "Nenhuma conta de servico informada (-ServiceUser/-ServicePassword)."
    Write-Warning "O servico rodara como LocalSystem (Session 0, Chrome invisivel)."
    Write-Warning "Para rodar como usuario interativo, use:"
    Write-Warning "  install_service.ps1 -ServiceUser 'paulo.morais' -ServicePassword 'senha'"
}

# ---------------------------------------------------------------------------
# Verificacao pre-start: profile do usuario e sessao do portal
# ---------------------------------------------------------------------------
# Verifica se o profile do usuario existe na máquina (obrigatorio para
# usuarios de dominio que devem fazer logon interativo pelo menos uma vez).
if ($ServiceUser) {
    $UserProfile = Get-UserProfilePath -AccountName $ServiceUser
    if (-not (Test-Path $UserProfile)) {
        Write-Warning "Profile do usuario NAO encontrado: $UserProfile"
        Write-Warning "O usuario '$ServiceUser' deve fazer logon interativo pelo menos uma vez nesta maquina."
        Write-Warning "Cancelando instalacao."
        & $NssmExe stop $ServiceName | Out-Null
        & $NssmExe remove $ServiceName confirm | Out-Null
        exit 1
    }
    Write-Host "==> Profile do usuario encontrado: $UserProfile" -ForegroundColor Cyan
    $CookieFile = Join-Path $UserProfile '.ponto_sms_flet\cookies.json'
} else {
    $CookieFile = Join-Path $env:USERPROFILE '.ponto_sms_flet\cookies.json'
}
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