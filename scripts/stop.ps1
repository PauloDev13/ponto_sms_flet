<#
.SYNOPSIS
  Para uma ou mais instancias do backend (uvicorn) do ponto eletronico.

.DESCRIPTION
  - Identifica processos python.exe cujo comando contem
    "uvicorn backend.app.main" e os encerra (handle de todas as
    instancias, ativas ou nao).
  - Tambem fecha o chromedriver orfao da janela do navegador do backend,
    se houver (libera recursos do Chrome).
  - Por fim, confirma que a porta 8000 ficou livre.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$KillChromeDriver
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# 1) Instancias de uvicorn do projeto (todas)
# ---------------------------------------------------------------------------
$uvicorn = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'uvicorn backend\.app\.main' }

if ($uvicorn) {
    $uvicorn | ForEach-Object {
        Write-Host "==> Parando PID $($_.ProcessId): $($_.CommandLine)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host 'Nenhuma instancia de uvicorn do projeto encontrada.'
}

# ---------------------------------------------------------------------------
# 2) chromedriver orfao (opcional, flag -KillChromeDriver)
# ---------------------------------------------------------------------------
if ($KillChromeDriver) {
    $cd = Get-Process -Name chromedriver -ErrorAction SilentlyContinue
    if ($cd) {
        $cd | ForEach-Object {
            Write-Host "==> Fechando chromedriver PID $($_.Id)"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host 'Nenhum chromedriver ativo.'
    }
}

# ---------------------------------------------------------------------------
# 3) Confirmacao de porta livre
# ---------------------------------------------------------------------------
Start-Sleep -Seconds 2
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listen) {
    Write-Host "ATENCAO: porta $Port ainda ocupada pelo PID $($listen.OwningProcess)."
} else {
    Write-Host "Porta $Port livre."
}
Write-Host 'Stop concluido.'