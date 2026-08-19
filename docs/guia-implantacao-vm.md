# Guia de Implantação — Web em Produção na VM Windows 10

Guia objetivo para subir a versão web do ponto eletrônico em uma **VM Windows
10** com o **Chrome já instalado**, deixando o ambiente em execução e pronto
para os **testes de uso pelo frontend**.

Base: `docs/guia-producao.md` (versão completa, com troubleshooting e plano B
do desktop). Use este guia para a implantação inicial; o guia completo para
operações contínuas, monitoramento e rollback.

---

## 1. O que é obrigatório na VM

### 1.1 Programas (pré-requisitos)

| Item | Obrigatório? | Observação |
|---|---|---|
| Windows 10/11 (64 bits) | Sim | A VM já atende |
| Google Chrome | **Sim** | Já instalado no cenário; sem ele não há scraping |
| Python 3.12 (no PATH) | **Sim** | O CI/usado em produção é 3.12 |
| Git | Sim | Necessário para clonar/atualizar a branch `PontoSmsWeb` |
| NSSM (`nssm.exe`, no PATH) | Opcional | Só se rodar como serviço Windows (recomendado) |
| Ghostscript (`gswin64c`) | Opcional | Só para compressão de PDF; sem ele o PDF original é mantido |

---

### 1.2 Pastas e arquivos obrigatórios (da branch `PontoSmsWeb`)

Não é preciso copiar o repositório inteiro — o clone traz tudo, mas **só estes
itens são consumidos em runtime**. O restante (desktop/, tests/, .github/,
docs/, pyproject.toml, poetry.lock, backend/requirements.txt) é opcional.

```
C:\Apps\ponto_sms_flet\          # raiz do projeto (clone)
├── backend\                     # OBRIGATÓRIO — API FastAPI
│   ├── app\                     #   main.py, ponto_service.py, session_manager.py, auth.py
│   └── core\                    #   scraper, excel/pdf_service, settings, paths, job, ...
├── frontend\
│   └── index.html               # OBRIGATÓRIO — página única servida pela API (GET /)
├── data\
│   └── unidades.csv             # OBRIGATÓRIO — autocomplete de unidades (versionado)
├── assets\
│   └── logo_pgm.png             # Opcional — default de PATH_LOGO (não consumido pelo frontend)
├── requirements-web.txt         # OBRIGATÓRIO — manifest de dependências do ambiente web
├── .env.example                 # OBRIGATÓRIO — modelo para gerar o .env
├── .env                         # OBRIGATÓRIO (criado no passo 4; NUNCA versionar)
└── scripts\
    ├── setup_prod.ps1           # OBRIGATÓRIO — setup idempotente (venv + deps + .env)
    ├── install_service.ps1      # Obrig. p/ modo serviço — instala NSSM PontoSmsWeb
    └── pre_login.py             # OBRIGATÓRIO — pré-login no portal (resolve o captcha 1ª vez)
```

**O que NÃO sobe para produção (opcional/ignorar):**

- `desktop/` — código legado Flet/PyInstaller (plano B); não participa da web.
- `tests/`, `.github/` — apenas CI/desenvolvimento.
- `pyproject.toml`, `poetry.lock`, `backend/requirements.txt` — obsoleto
  (manifest web oficial é `requirements-web.txt`).
- `.idea/`, `__init__.py` (raiz), `README.md`, `server_*.log` — irrelevantes.

### 1.3 Onde o app grava dados em runtime

| Dado | Local |
|---|---|
| Arquivos gerados (jobs) | `OUTPUT_DIR` (padrão `~/Documents/PLANILHAS_SMS`) |
| Perfil do Chrome | `~/.ponto_sms_flet/chrome_profile` |
| Cookies de sessão (redundantes) | `~/.ponto_sms_flet/cookies.json` |
| Logs (modo serviço) | `C:\ProgramData\PontoSmsWeb\logs\` |

> Essas pastas são criadas automaticamente. Mantenha as permissões da conta do
> serviço sobre elas (ver passo 7).

---

## 2. Obter o código

```powershell
New-Item -ItemType Directory -Path C:\Apps -Force | Out-Null
cd C:\Apps
git clone <url-do-repositorio> ponto_sms_flet
cd ponto_sms_flet
git checkout PontoSmsWeb
git pull origin PontoSmsWeb
```

---

## 3. Instalar o ambiente web (venv + dependências) — automático

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
```

O script é **idempotente** (pode rodar várias vezes). Ele:

1. Valida Python no PATH;
2. Cria o venv `.venv` e instala `requirements-web.txt`;
3. Checa Chrome e Ghostscript (avisa, não interrompe);
4. Garante `data/unidades.csv`;
5. Cria o `.env` a partir de `.env.example` **sem sobrescrever** credenciais.

Confirmar a instalação:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\pip.exe freeze | Select-String 'fastapi|uvicorn|selenium|pandas'
```

---

## 4. Configurar o `.env` (credenciais do portal + contas web)

Edite o `.env` (na raiz) e preencha obrigatoriamente:

```ini
# ---- Login do portal (scraping) ----
USER='06511122233'            # CPF usado no portal
PASSWORD='senha-do-portal'
URL_BASE='https://portal/index.php'
URL_DATA='https://portal/pesquisa.php'
URL_INIT='https://portal/interno/inicio.php'

# ---- Contas da aplicação web (login no browser) ----
WEB_USERS='admin:senha-forte-1,maria:senha-forte-2'
SESSION_SECRET=''
SESSION_TTL_HOURS=12

# ---- Opcionais ----
NAME_FOLDER='PLANILHAS_SMS'
OUTPUT_DIR='C:/Apps/ponto_sms_flet/saida'
JOB_TTL_HOURS=24
JOBS_HISTORY_LIMIT=20
GHOSTSCRIPT_BIN=''
```

Gerar o `SESSION_SECRET` (ou deixe vazio — o `setup_prod.ps1` gera automaticamente se for o placeholder):

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

> O `.env` está no `.gitignore` e nunca vai para o git.
> O `setup_prod.ps1` detecta se `SESSION_SECRET` ainda é `troque-este-segredo`
> e gera um valor seguro automaticamente.

---

## 5. Subir manualmente e validar ANTES de virar serviço

Neste passo o login do portal (primeira vez) e o captcha são resolvidos com a
janela do Chrome visível.

```powershell
cd C:\Apps\ponto_sms_flet
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Em outro terminal (ou outra máquina da rede):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# Esperado: {"status":"ok", ..., "env_ok":true, "user_masked":"065...***"}
```

> Se `env_ok` for `false`: faltam `USER/PASSWORD/URL_BASE/URL_DATA/URL_INIT` no `.env`.

---

## 6. Transcrição do login: deixar a sessão do portal pronta (1ª vez)

> **OBRIGATÓRIO:** Este passo deve ser executado ANTES do passo 7 (serviço).
> Sem ele, o serviço não tem sessão válida no portal e todos os jobs falham
> com "Captcha não resolvido no tempo limite".

> **IMPORTANTE:** Use SEMPRE o Python do venv (`.\.venv\Scripts\python.exe`),
> nunca o `python.exe` do sistema. O selenium só está instalado no venv.

Antes de parar o uvicorn manual e migrar para o serviço, **faça o pré-login no
portal** para o serviço reaproveitar a sessão sem novo captcha:

```powershell
cd C:\Apps\ponto_sms_flet
.\.venv\Scripts\python.exe scripts\pre_login.py --manual-wait 180
```

- Uma janela do Chrome abre; se o reCAPTCHA aparecer, resolva-o manualmente.
- Ao terminar com `session_active` ou `success`, o perfil/cookies ficam em
  `~/.ponto_sms_flet\` e o serviço reaproveita a sessão (janela minimizada).
- Se falhar ou der timeout, execute novamente até obter `session_active`/`success`.

---

## 7. Subir em produção como serviço Windows (NSSM) — recomendado

Pré-requisito: `nssm.exe` no PATH da VM.

### 7.1 Instalar o serviço

**IMPORTANTE:** O serviço DEVE rodar como o usuário interativo (não `LocalSystem`)
para que o Chrome tenha desktop visível via RDP e os cookies sejam encontrados
no home do usuário (`C:\Users\<usuario>\.ponto_sms_flet\`).

```powershell
# Instalar como o usuário da VM (substitua 'paulo.morais' e 'senha' pelos dados reais)
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1 `
    -ServiceUser 'paulo.morais' `
    -ServicePassword 'senha-do-usuario'
```

> **Por que é necessário?** O Chrome precisa de um desktop interativo para
> exibir a janela de captcha. Serviços Windows rodam na Session 0 (invisível).
> Ao rodar como o usuário logado via RDP, o Chrome abre na sessão interativa.


# Se der erro, verificar se NSSM já existe na VM. Se não existir, baixar e instalar
Usar Powershell para executar todos os comandos

- Criar diretório de instalação 
New-Item -ItemType Directory -Path "C:\Tools\nssm" -Force | Out-Null

- Baixar NSSM 2.24 (última estável)
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"

- Extrair
Expand-Archive -Path "$env:TEMP\nssm.zip" -DestinationPath "$env:TEMP\nssm" -Force

- Copiar o executável para o destino
Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" "C:\Tools\nssm\nssm.exe" -Force

- Adicionar ao PATH do sistema (permanente)
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($CurrentPath -notlike "*C:\Tools\nssm*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;C:\Tools\nssm", "Machine")
    Write-Host "PATH atualizado: C:\Tools\nssm adicionado"
}

- Atualizar PATH na sessão atual
$env:Path = "$env:Path;C:\Tools\nssm"

- Confirmar
nssm --version

Cria o serviço **`PontoSmsWeb`**:

- Executável: `.venv\Scripts\python.exe`
- Parâmetros: `-m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Início automático + **reinício automático em falha** (delay 5s)
- Logs rotacionados (10 MB) em `C:\ProgramData\PontoSmsWeb\logs\`

### 7.2 Verificar que o usuário está logado via RDP

Para o Chrome abrir a janela de captcha, o usuário do serviço DEVE estar
logado via RDP com sessão ativa. Verifique:

```powershell
# Na VM, execute:
query session
```

Esperado:
```
 SESSIONNAME       USERNAME                 ID  STATE   TYPE        DEVICE
 services                                    0  Disc
 rdp-tcp#0         paulo.morais              1  Active
```

Se `paulo.morais` estiver com estado `Active`, o serviço pode usar a sessão
interativa do Chrome.

> **Se o usuário não estiver logado via RDP:** O Chrome abre na Session 0
> (invisível) e o captcha não pode ser resolvido. Conecte-se à VM via RDP
> antes de iniciar o serviço.

### 7.3 Rodar como processo normal (alternativa ao serviço)

Se o captcha for muito frequente, uma alternativa é rodar o servidor como
**processo interativo** em vez de serviço Windows:

```powershell
# Criar tarefa que roda ao logar (interativa, com desktop visível)
schtasks /create /tn "PontoSmsWeb" /tr "C:\Apps\ponto_sms_flet\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000" /sc ONLOGON /rl HIGHEST
```

**Vantagem:** roda como processo do usuário, com desktop visível. Chrome abre
normalmente para captcha. Não precisa de RDP logado o tempo todo.

### 7.4 Verificar

```powershell
Get-Service PontoSmsWeb                 # deve estar Running
Get-Content C:\ProgramData\PontoSmsWeb\logs\err.log -Tail 50
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 7.5 Liberar o acesso remoto (firewall)

```powershell
New-NetFirewallRule -DisplayName 'PontoSmsWeb 8000' `
  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## 8. Testes de uso pelo frontend

Na VM (ou de outra máquina da rede), abra `http://<ip-da-vm>:8000/`:

1. **Login web** — use um usuário/senha de `WEB_USERS`.
2. Preencha CPF (máscara) + **unidade** (autocomplete vem de `data/unidades.csv`)
   + período (MM/yyyy).
3. Clique em gerar; acompanhe a **barra de progresso** (SSE) até 100%.
4. Confira os **arquivos** gerados (Excel/PDF) e o **download**; teste também
   `zip` com `parts=zip` (que divide o PDF).
5. Veja o histórico navegável; se quiser, **limpe o histórico** ou exclua um job.
6. Valide o logout (cookie assinado apagado).

Smoke test de rotina (qualquer momento):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# user_masked deve aparecer mascarado (credenciais nunca expostas)
```

---

## 9. Deploy de novas versões (resumo)

```powershell
cd C:\Apps\ponto_sms_flet
git pull origin PontoSmsWeb                    # 1. puxa versão nova
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1   # 2. deps (idempotente)
nssm restart PontoSmsWeb                       # 3. aplica (não roda na 1ª instalação antes do passo 7)
```

---

## 10. Checklist de prontidão

- [ ] Chrome instalado e Python 3.12 no PATH
- [ ] Clone na branch `PontoSmsWeb` em `C:\Apps\ponto_sms_flet`
- [ ] `setup_prod.ps1` OK (venv + deps + `data/unidades.csv`)
- [ ] `.env` preenchido (`USER/PASSWORD/URL_*`, `WEB_USERS`, `SESSION_SECRET`)
- [ ] `/health` → `env_ok:true`
- [ ] `pre_login.py` concluído (`session_active`/`success`) — sessão do portal pronta
- [ ] Serviço `PontoSmsWeb` `Running` (rodando com a conta do usuário)
- [ ] Firewall liberado na porta 8000
- [ ] Frontend: login, geração, progresso, download e histórico OK