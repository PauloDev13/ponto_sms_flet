<#
.SYNOPSIS
  Remove completamente a implantacao do ponto_sms_flet de uma VM Windows.

.DESCRIPTION
  Executa limpeza completa para permitir uma nova implantacao do zero:
    1. Para e remove o servico NSSM PontoSmsWeb
    2. Remove exclusoes do Windows Defender
    3. Remove regra de firewall
    4. Remove perfil do Chrome e cookies
    5. Remove cache do Selenium
    6. Remove diretorio do projeto
    7. Remove variaveis de ambiente (PATH Python, PYTHONUTF8)
    8. Remove pasta de saida dos arquivos gerados

  Execute como ADMINISTRADOR.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\uninstall_all.ps1
#>
[CmdletBinding()]
param(
    [switch]$KeepPython,      # nao remove Python 3.12
    [switch]$KeepNssm,        # nao remove nssm.exe
    [switch]$KeepProject      # nao remove C:\Apps\ponto_sms_flet
)

$ErrorActionPreference = 'SilentlyContinue'

function Write-Step  { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Msg) Write-Host "    OK: $Msg" -ForegroundColor Green }
function Write-Skip  { param([string]$Msg) Write-Host "    SKIP: $Msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# 0) Verificar se esta rodando como administrador
# ---------------------------------------------------------------------------
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERRO: Execute este script como ADMINISTRADOR." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Red
Write-Host "  LIMPEZA COMPLETA - ponto_sms_flet" -ForegroundColor Red
Write-Host "=============================================" -ForegroundColor Red
Write-Host ""
Write-Host "ATENCAO: Este script vai remover TODOS os dados do aplicativo." -ForegroundColor Yellow
Write-Host "         Arquivos gerados (planilhas) tambem serao removidos." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Digite SIM para confirmar a limpeza"
if ($confirm -notin @('sim', 'SIM', 'Sim', 's', 'S')) {
    Write-Host "Cancelado." -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------------------
# 1) Parar e remover servico NSSM
# ---------------------------------------------------------------------------
Write-Step "1/8 - Removendo servico NSSM..."

$nssmCmd = Get-Command nssm -ErrorAction SilentlyContinue
if ($nssmCmd) {
    & nssm stop PontoSmsWeb 2>$null
    & nssm remove PontoSmsWeb confirm 2>$null
    if ($?) { Write-Ok "Servico PontoSmsWeb removido." }
    else { Write-Skip "Servico nao encontrado ou ja removido." }
} else {
    # Tentar caminho padrao
    $nssmPath = "C:\Tools\nssm\nssm.exe"
    if (Test-Path $nssmPath) {
        & $nssmPath stop PontoSmsWeb 2>$null
        & $nssmPath remove PontoSmsWeb confirm 2>$null
        if ($?) { Write-Ok "Servico PontoSmsWeb removido." }
        else { Write-Skip "Servico nao encontrado ou ja removido." }
    } else {
        Write-Skip "NSSM nao encontrado. Servico nao removido."
    }
}

# ---------------------------------------------------------------------------
# 2) Remover exclusoes do Windows Defender
# ---------------------------------------------------------------------------
Write-Step "2/8 - Removendo exclusoes do Windows Defender..."

$ExclusionPaths = @(
    'C:\Apps\ponto_sms_flet',
    "$env:USERPROFILE\.cache\selenium",
    "$env:USERPROFILE\.ponto_sms_flet"
)

try {
    $CurrentExclusions = (Get-MpPreference -ErrorAction Stop).ExclusionPath
    foreach ($Path in $ExclusionPaths) {
        if ($Path -in $CurrentExclusions) {
            Remove-MpPreference -ExclusionPath $Path -ErrorAction Stop
            Write-Ok "Exclusao removida: $Path"
        }
    }
} catch {
    Write-Skip "Nao foi possivel remover exclusoes Defender (sem privilegios?)."
}

# ---------------------------------------------------------------------------
# 3) Remover regra de firewall
# ---------------------------------------------------------------------------
Write-Step "3/8 - Removendo regra de firewall..."

Remove-NetFirewallRule -DisplayName 'PontoSmsWeb 8000' -ErrorAction SilentlyContinue
if ($?) { Write-Ok "Regra de firewall removida." }
else { Write-Skip "Regra nao encontrada." }

# ---------------------------------------------------------------------------
# 4) Remover perfil do Chrome e cookies
# ---------------------------------------------------------------------------
Write-Step "4/8 - Removendo perfil Chrome e cookies..."

$PontoDir = "$env:USERPROFILE\.ponto_sms_flet"
if (Test-Path $PontoDir) {
    Remove-Item -Path $PontoDir -Recurse -Force
    Write-Ok "Diretorio removido: $PontoDir"
} else {
    Write-Skip "Diretorio nao encontrado: $PontoDir"
}

# ---------------------------------------------------------------------------
# 5) Remover cache do Selenium
# ---------------------------------------------------------------------------
Write-Step "5/8 - Removendo cache do Selenium..."

$SeleniumCache = "$env:USERPROFILE\.cache\selenium"
if (Test-Path $SeleniumCache) {
    Remove-Item -Path $SeleniumCache -Recurse -Force
    Write-Ok "Cache removido: $SeleniumCache"
} else {
    Write-Skip "Cache nao encontrado: $SeleniumCache"
}

# ---------------------------------------------------------------------------
# 6) Remover diretorio do projeto
# ---------------------------------------------------------------------------
Write-Step "6/8 - Removendo diretorio do projeto..."

if (-not $KeepProject) {
    $ProjectDir = 'C:\Apps\ponto_sms_flet'
    if (Test-Path $ProjectDir) {
        # Muda para fora do diretorio antes de deletar (o script roda de dentro dele)
        Set-Location -Path $env:TEMP
        try {
            Remove-Item -Path $ProjectDir -Recurse -Force -ErrorAction Stop
            Write-Ok "Projeto removido: $ProjectDir"
        } catch {
            Write-Warning "Falha ao remover: $_"
            Write-Warning "Tente manualmente apos fechar todos os terminais PowerShell."
        }
    } else {
        Write-Skip "Diretorio nao encontrado: $ProjectDir"
    }
} else {
    Write-Skip "Mantido por -KeepProject."
}

# ---------------------------------------------------------------------------
# 7) Remover variaveis de ambiente
# ---------------------------------------------------------------------------
Write-Step "7/8 - Limpando variaveis de ambiente..."

# PATH da maquina (HKLM)
$envKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
$currentPath = (Get-ItemProperty -Path $envKey -Name Path -ErrorAction SilentlyContinue).Path

if ($currentPath) {
    $newParts = ($currentPath -split ';') | Where-Object {
        $_ -notmatch 'Python312' -and
        $_ -notmatch 'Python310' -and
        $_ -notmatch 'Python311' -and
        $_ -notmatch 'Programs\\Python'
    }
    $newPath = $newParts -join ';'
    Set-ItemProperty -Path $envKey -Name Path -Value $newPath -Type ExpandString
    Write-Ok "PATH limpo (entradas Python removidas)."
}

# PYTHONUTF8
Remove-ItemProperty -Path $envKey -Name PYTHONUTF8 -ErrorAction SilentlyContinue
Write-Ok "PYTHONUTF8 removido."

# ---------------------------------------------------------------------------
# 8) Remover pasta de saida (arquivos gerados)
# ---------------------------------------------------------------------------
Write-Step "8/8 - Removendo pasta de saida..."

$OutputDir = "$env:USERPROFILE\Documents\PLANILHAS_SMS"
if (Test-Path $OutputDir) {
    $size = (Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "    Tamanho: $sizeMB MB" -ForegroundColor Yellow
    $confirmOut = Read-Host "    Remover $OutputDir? (S/N)"
    if ($confirmOut -in @('s', 'S', 'sim', 'SIM')) {
        Remove-Item -Path $OutputDir -Recurse -Force
        Write-Ok "Pasta de saida removida."
    } else {
        Write-Skip "Pasta de saida mantida."
    }
} else {
    Write-Skip "Pasta de saida nao encontrada."
}

# Remover logs do servico
$LogDir = 'C:\ProgramData\PontoSmsWeb'
if (Test-Path $LogDir) {
    Remove-Item -Path $LogDir -Recurse -Force
    Write-Ok "Logs do servico removidos: $LogDir"
}

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  LIMPEZA CONCLUIDA" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Itens removidos:" -ForegroundColor Cyan
Write-Host "  - Servico NSSM PontoSmsWeb"
Write-Host "  - Exclusoes do Windows Defender"
Write-Host "  - Regra de firewall (porta 8000)"
Write-Host "  - Perfil Chrome e cookies"
Write-Host "  - Cache do Selenium"
if (-not $KeepProject) { Write-Host "  - Diretorio do projeto (C:\Apps\ponto_sms_flet)" }
if (-not $KeepPython) { Write-Host "  - Variaveis de ambiente Python" }
Write-Host "  - Logs do servico"
Write-Host ""

if (-not $KeepPython) {
    Write-Host "NOTA: Python 3.12 continua instalado em C:\Program Files\Python312" -ForegroundColor Yellow
    Write-Host "      Para remover, desinstale painel: Configuracoes > Apps > Python 3.12" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Para nova implantacao, siga: docs/guia-implantacao-vm.md" -ForegroundColor Cyan
