<#
.SYNOPSIS
  Sobe o backend (uvicorn) do ponto eletronico em segundo plano.

.DESCRIPTION
  - Garante que nao ha instancia ativa na porta alvo antes de iniciar
    (se houver, roda o stop.ps1 primeiro).
  - Executa o uvicorn com o python do venv, em background e minimizado,
    redirecionando stdout/stderr para server_out.log / server_err.log na
    raiz do projeto.
  - Aguarda o /health responder e exibe o resultado.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$OutLog = Join-Path $Root 'server_out.log'
$ErrLog = Join-Path $Root 'server_err.log'

if (-not (Test-Path $Python)) {
    throw "venv nao encontrado ($Python). Execute scripts\setup_prod.ps1 antes."
}

# ---------------------------------------------------------------------------
# 1) Nao pode haver instancia ativa na porta alvo
# ---------------------------------------------------------------------------
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listen) {
    Write-Host "Porta $Port ocupada (PID $($listen.OwningProcess)). Executando stop.ps1 primeiro..."
    & (Join-Path $PSScriptRoot 'stop.ps1') -Port $Port
    Start-Sleep -Seconds 2
}

# ---------------------------------------------------------------------------
# 2) Inicia o uvicorn em background
# ---------------------------------------------------------------------------
Write-Host "==> Iniciando uvicorn na porta $Port (venv: $Python)"
$Args = @('-m', 'uvicorn', 'backend.app.main:app',
          '--host', '0.0.0.0', '--port', "$Port")
$proc = Start-Process -FilePath $Python -ArgumentList $Args `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden -PassThru
Write-Host "==> Processo lancado (PID $($proc.Id)). Logs em server_out.log / server_err.log."

# ---------------------------------------------------------------------------
# 3) Aguarda o health responder (ate ~30s)
# ---------------------------------------------------------------------------
$ok = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
        Write-Host "==> Backend no ar: $($health | ConvertTo-Json -Compress)"
        $ok = $true
        break
    } catch {
        # ainda subindo...
    }
}
if (-not $ok) {
    Write-Warning 'Backend nao respondeu em 30s. Verifique o arquivo server_err.log.'
    Write-Host '==> server_err.log (ultimas linhas):'
    if (Test-Path $ErrLog) { Get-Content $ErrLog -Tail 10 }
    Write-Host '==> server_out.log (ultimas linhas):'
    if (Test-Path $OutLog) { Get-Content $OutLog -Tail 10 }
}