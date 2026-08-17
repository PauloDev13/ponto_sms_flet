# Runbook de Produção — VM Windows (Parte D, FASE 5)

Guia operacional da VM Windows de produção. Não usa Docker: a instalação é
via venv + serviço Windows (NSSM), com script idempotente para setup e deploy.

## Visão geral

| Item | Valor |
|---|---|
| Porta | `8000` (host `0.0.0.0`) |
| Branch | `PontoSmsWeb` |
| Serviço Windows | `PontoSmsWeb` (NSSM) |
| Python | 3.12 (compatível 3.10+) |
| URL | `http://<ip-da-vm>:8000/` |

## D1 — Primeira instalação (setup_prod.ps1)

```powershell
# 1. Clone/atualize o repositório
cd C:\Apps\ponto_sms_flet

# 2. Setup idempotente: venv + deps + checagens + .env
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
```

O script faz, com segurança para rodar várias vezes:

1. Valida Python no PATH;
2. Cria/atualiza o venv (`.venv`) e instala `requirements-web.txt`;
3. Checa Chrome/Edge e Ghostscript (avisa, não quebra);
4. Garante `data/unidades.csv` presente;
5. Cria o `.env` a partir de `.env.example` **sem sobrescrever** credenciais.

Após a 1ª execução, **preencha o `.env`** (nunca versionar):

```
USER='...'          # CPF do login do portal
PASSWORD='...'
URL_BASE='...'
URL_DATA='...'
URL_INIT='...'
NAME_FOLDER='PLANILHAS_SMS'
WEB_USERS='admin:senha-forte'        # contas da aplicação web
SESSION_SECRET='<gerar: python -c "import secrets; print(secrets.token_urlsafe(32))"'
SESSION_TTL_HOURS=12
JOB_TTL_HOURS=24
JOBS_HISTORY_LIMIT=20
```

## D2 — Instalação do serviço Windows (NSSM)

Pré-requisito: instalar o [NSSM](https://nssm.cc) e adicionar `nssm.exe` ao PATH.

```powershell
# Instala e inicia o serviço "PontoSmsWeb" (uvicorn :8000, autorestart)
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1

# Conferir
Get-Service PontoSmsWeb
Get-Content C:\ProgramData\PontoSmsWeb\logs\err.log
```

O serviço roda `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
a partir da raiz do repositório, com reinício automático em falha (delay 5s) e
rotação de logs (10 MB).

Para remover:

```powershell
nssm stop PontoSmsWeb
nssm remove PontoSmsWeb confirm
```

## D3 — Deploy (nova versão)

```powershell
cd C:\Apps\ponto_sms_flet
git pull origin PontoSmsWeb
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1   # idempotente
nssm restart PontoSmsWeb                                          # aplica a nova versão
```

Smoke test após o deploy:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# => {"status":"ok", ..., "env_ok":true}
```

- Se `env_ok` for `false`, faltam variáveis no `.env`.
- Se a janela do Chrome não abrir para login, verifique o navegador e o
  `chrome_profile` em `C:\Users\<usuario>\.ponto_sms_flet\`.
- Rollback: `git checkout <tag-anterior>` + `nssm restart PontoSmsWeb`.

## D4 — Plano B: manter o desktop (build a partir de version_2.3.1)

Se a web ainda não estiver validada em produção, o desktop continua operando.
O desktop é mantido na branch **`version_2.3.1`** (committer separado, não
misturar com a web na `PontoSmsWeb`).

```powershell
# Em outra pasta de trabalho
git clone -b version_2.3.1 <repo-url> desktop_ponto_sms
cd desktop_ponto_sms
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m PyInstaller --onefile --windowed `
    --name PontoSmsDesktop `
    --add-data "assets;assets" `
    --add-data "data;data" `
    main.py
```

> Ajuste o `--add-data` e os hooks do PyInstaller conforme o layout do
> desktop na branch `version_2.3.1` (o `.spec` gerado fica em `build/`).

**Regra:** a `PontoSmsWeb` nunca recebe código do desktop; e o desktop só é
descontinuado quando a web for aprovada em produção (Aceite da FASE 5).
