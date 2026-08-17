# Guia Completo de Implementação em Produção — Ponto Eletrônico SMS (Web)

Guia passo a passo para colocar a aplicação web em produção em uma **VM
Windows** (sem Docker). Abrange pré-requisitos, instalação, configuração,
subida do serviço, deploy de atualizações, monitoramento e **build**
(necessário apenas para o plano B — o desktop).

---

## 0. Entenda a arquitetura (leitura obrigatória)

| Aspecto | Detalhe |
|---|---|
| Backend | FastAPI (`backend/app/main.py`), servido por **uvicorn** |
| Frontend | Um único arquivo estático `frontend/index.html` servido pela própria API (`GET /`) |
| Scraping | Selenium/Chrome com perfil persistente (`~/.ponto_sms_flet/chrome_profile`) |
| Login portal | Credenciais no `.env` (`USER`, `PASSWORD`, `URL_*`) |
| Login web | Contas locais `WEB_USERS` com sessão por cookie assinado |
| Jobs | Assíncronos, em fila serializada (1 worker) — o frontend acompanha por SSE |
| Arquivos | Gerados em `OUTPUT_DIR` (padrão `~/Documents/PLANILHAS_SMS`) |

**IMPORTANTE — sobre build:** a aplicação **web não precisa de build**. Não há
compilação, bundling de JS/CSS nem PyInstaller. "Subir a aplicação" = instalar
dependências Python, configurar `.env` e executar o uvicorn. O **único cenário
que exige build é o plano B** (manter o desktop rodando), explicado na seção 8.

**IMPORTANTE — sobre a janela do Chrome:** o login no portal + resolução
manual do reCAPTCHA exige uma **janela do Chrome visível** na primeira
execução (depois a sessão fica aberta e minimizada). Em serviço Windows
(NSSM) com execução em Session 0, essa janela NÃO aparece para o usuário
logado. A seção 7 detalha as opções (rodar o serviço como usuário com
interação, ou usar o Agendador de Tarefas).

Requisitos mínimos da VM:

- Windows 10/11 ou Server 2019+ (64 bits)
- Python **3.12** (o CI usa 3.12; 3.11 também funciona localmente)
- Google Chrome ou Microsoft Edge instalados
- Ghostscript (opcional — só para compressão de PDF; sem ele o PDF original é mantido)
- NSSM (`nssm.exe`) no PATH — necessário apenas para o modo serviço
- Git

---

## 1. Obter o código

Na VM, abra o PowerShell e:

```powershell
# Pasta padrão sugerida
New-Item -ItemType Directory -Path C:\Apps -Force | Out-Null
cd C:\Apps

# Clone a branch web de produção
git clone <url-do-repositorio> ponto_sms_flet
cd ponto_sms_flet
git checkout PontoSmsWeb
git pull origin PontoSmsWeb
```

> Use uma conta de usuário e token (não senha de conta) para o clone via HTTPS,
> ou um deploy key via SSH. O repositório contém `.env.example`, nunca o `.env`.

---

## 2. Verificar o ambiente (Python, navegador, Ghostscript)

```powershell
python --version          # esperado 3.12.x
# Chrome / Edge
Test-Path 'C:\Program Files\Google\Chrome\Application\chrome.exe'
Test-Path 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
# Ghostscript (opcional, para compressão de PDF)
Get-Command gswin64c -ErrorAction SilentlyContinue
```

---

## 3. Instalar o ambiente (venv + dependências) — setup automático

Use o script idempotente. Ele pode rodar várias vezes sem quebrar nada.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
```

O que o script faz:

1. Valida Python no PATH.
2. Cria o venv em `.venv` (se não existir) e instala `requirements-web.txt`.
3. Checa navegador e Ghostscript (avisa, não interrompe).
4. Garante `data/unidades.csv` presente (arquivo obrigatório, versionado).
5. Cria o `.env` a partir de `.env.example` **sem sobrescrever** credenciais.

Para verificar manualmente que instalou, antes de continuar:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\pip.exe freeze | Select-String 'fastapi|uvicorn|selenium|pandas'
```

---

## 4. Configurar o `.env` (credenciais do portal + contas web)

Edite o arquivo `.env` (na raiz do projeto) e preencha SEMPRE estes campos:

```ini
# ---- Login do portal (scraping) ----
USER='06511122233'            # CPF usado no portal
PASSWORD='sua-senha-do-portal'
URL_BASE='https://portal/index.php'
URL_DATA='https://portal/pesquisa.php'   # URL onde fica o formulário de busca
URL_INIT='https://portal/interno/inicio.php'

# ---- Contas da aplicação web (login do usuário no browser) ----
WEB_USERS='admin:senha-forte-1,maria:senha-forte-2'
SESSION_SECRET='<gere-um-segredo>'
SESSION_TTL_HOURS=12

# ---- Opcionais ----
NAME_FOLDER='PLANILHAS_SMS'
OUTPUT_DIR='C:/Apps/ponto_sms_flet/saida'   # pasta dos jobs; senão ~/Documents/<NAME_FOLDER>
JOB_TTL_HOURS=24
JOBS_HISTORY_LIMIT=20
GHOSTSCRIPT_BIN=''                           # deixe vazio para auto-detecção
```

Gerar o `SESSION_SECRET`:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **Segurança:** o `.env` está no `.gitignore` e nunca deve ser commitado.
> Senhas do portal e as contas `WEB_USERS` nunca transitam para o frontend
> (o `/health` só expõe `user_masked`).

---

## 5. Testar manualmente ANTES de virar serviço

Neste passo o login do portal (primeira vez) e o captcha manual são resolvidos
com a janela do Chrome visível na sessão do usuário.

```powershell
cd C:\Apps\ponto_sms_flet
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Em outro terminal, smoke test:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# Esperado: {"status":"ok", ..., "env_ok":true, "user_masked":"065...***"}
```

Abra o frontend no navegador da VM: `http://127.0.0.1:8000/`.

1. Faça login com um usuário de `WEB_USERS`.
2. Preencha CPF + unidade + período e clique em gerar.
3. Se necessário, **resolva o reCAPTCHA na janela do Chrome** que abrir.
4. Confira Excel/PDF gerados e o download.

> Se `env_ok` for `false`: faltam variáveis no `.env` (USER/PASSWORD/URL_BASE/URL_DATA/URL_INIT).

Depois de validar, **ande com o login já feito** (janela aberta e minimizada),
ou deixe os cookies salvos em `~/.ponto_sms_flet/cookies.json` para que o
serviço reaproveite a sessão sem novo captcha.

---

## 6. Subir em produção como serviço Windows (NSSM)

Pré-requisito: instale o [NSSM](https://nssm.cc/download) e adicione o
`nssm.exe` ao PATH da VM.

### 6.1 Instalar o serviço

```powershell
cd C:\Apps\ponto_sms_flet
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1
```

O script cria o serviço **`PontoSmsWeb`** com:

- Executável: `.venv\Scripts\python.exe`
- Parâmetros: `-m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Diretório de trabalho: raiz do projeto
- Início automático, **reinício automático em falha** (delay 5s)
- Logs em `C:\ProgramData\PontoSmsWeb\logs\` (rotação de 10 MB)

### 6.2 Verificar o serviço

```powershell
Get-Service PontoSmsWeb                 # deve constar Running
sc query PontoSmsWeb
Get-Content C:\ProgramData\PontoSmsWeb\logs\err.log -Tail 50
```

### 6.3 Liberar o acesso remoto (firewall)

```powershell
New-NetFirewallRule -DisplayName 'PontoSmsWeb 8000' `
  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

A partir de outra máquina da rede: `http://<ip-da-vm>:8000/`

### 6.4 Remover o serviço (se precisar)

```powershell
nssm stop PontoSmsWeb
nssm remove PontoSmsWeb confirm
```

---

## 7. Cuidados específicos da produção (leia com atenção)

### 7.1 A janela do Chrome (login/captcha) não aparece em Session 0

O NSSM roda serviços na Session 0; a janela do Chrome não fica visível ao
usuário logado. Opções:

- **Opção A (recomendada): pré-login na sessão do usuário antes de iniciar o
  serviço.** Rode `scripts\pre_login.py` logado na VM (resolva o captcha uma
  vez); o perfil/cookies são salvos em `~/.ponto_sms_flet` e o serviço
  reaproveita a sessão. Depois, o serviço mantém a janela aberta/minimizada.
- **Opção B: rodar como serviço com "Allow service to interact with the
  desktop"** (funciona apenas em Windows sem UAC intenso; registrar o serviço
  para rodar na conta do usuário que fará login).
- **Opção C (alternativa ao NSSM): Agendador de Tarefas** com "Executar apenas
  quando o usuário estiver conectado". Crie uma tarefa "Na inicialização" e,
  em "Ações", execute `.venv\Scripts\python.exe -m uvicorn ...`. Assim a
  janela do Chrome aparece na sessão do usuário — ideal quando há captcha
  frequente. Ajuste o trigger para restart também ao logon do usuário.

> Escolha A ou C na prática; a B é frágil com UAC. A escolha depende de com
> que frequência o portal cai a sessão e exige novo captcha.

### 7.2 O serviço roda com a conta certa

- Se usar NSSM, o serviço deve rodar com a **conta do usuário da VM** (não
  LocalSystem) para que o perfil do Chrome (`~/.ponto_sms_flet`) seja o mesmo
  usado no pré-login:
  ```powershell
  nssm set PontoSmsWeb ObjectName ".\Usuario" "senha"
  ```

### 7.3 Disco e retenção

- `OUTPUT_DIR` cresce com os jobs; `JOB_TTL_HOURS` (24h) + `JOBS_HISTORY_LIMIT`
  (20) limitam o acumulo. Monitore o espaço em disco.
- Logs do NSSM em `C:\ProgramData\PontoSmsWeb\logs\` com rotação de 10 MB.

### 7.4 Horário/data da VM

- Os nomes de arquivo e relatórios dependem de data/hora; mantenha o relógio
  sincronizado (W32Time/NTP).

---

## 8. Build da aplicação (quando e como fazer)

### 8.1 Web — não precisa de build

Confirmação: o frontend é `frontend/index.html` (estático, servido pela API) e
o backend é Python puro. **Nenhum passo de build/compilação é necessário.**

"Deploy" = atualizar o código + reiniciar o serviço (seção 9).

### 8.2 Plano B — build do desktop (branch `version_2.3.1`)

Somente se precisar manter o app desktop rodando enquanto a web não for
aprovada em produção. O desktop vive na branch **`version_2.3.1`** (committer
separado — nunca misturar código desktop na `PontoSmsWeb`).

Em outra pasta de trabalho:

```powershell
git clone -b version_2.3.1 <url-do-repositorio> desktop_ponto_sms
cd desktop_ponto_sms

# 1. Ambiente
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Build PyInstaller (app desktop OneFile + Windowed)
.\.venv\Scripts\python -m PyInstaller --onefile --windowed `
    --name PontoSmsDesktop `
    --icon assets\icon_sms_2.ico `
    --add-data "assets;assets" `
    --add-data "data;data" `
    main.py

# 3. Resultado: dist\PontoSmsDesktop.exe
```

Importante (desktop):

- O desktop usa `desktop/config/config_env.py` que resolve o `.env` na raiz do
  executável/projeto instalado; na distribuição final, inclua o `.env`
  **fora** do build e o `PATH_CSV`/`PATH_LOGO` apontando para os dados.
- Ajuste `--add-data` conforme o layout real da branch `version_2.3.1`; o
  `*.spec` gerado em `build/` fica disponível para otimizações (ex.: datas,
  fonts, `--noconfirm`).
- Teste o `.exe` em uma VM limpa de referência antes de distribuir.

---

## 9. Deploy de uma nova versão (fluxo contínuo)

```powershell
cd C:\Apps\ponto_sms_flet
git pull origin PontoSmsWeb              # 1. puxa a nova versão
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1   # 2. atualiza venv/deps (idempotente)
nssm restart PontoSmsWeb                 # 3. reinicia o serviço
```

Smoke test pós-deploy:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Rollback (voltando uma versão que funcionava):

```powershell
git log --oneline -5
git checkout <commit-ou-tag-anterior>
nssm restart PontoSmsWeb
```

---

## 10. Monitoramento e troubleshooting

| Sintoma | Caminho |
|---|---|
| `env_ok: false` no `/health` | Faltam `USER/PASSWORD/URL_*` no `.env` |
| Página não abre | Firewall da porta 8000 / serviço parado (ver 6.3) |
| Login web falha | Conferir `WEB_USERS` e `SESSION_SECRET` em `.env` |
| Login do portal falha / sessão caiu | Rodar `scripts\pre_login.py` de novo na sessão do usuário e resolver o captcha |
| PDF sem compressão | Ghostscript ausente (log avisa) — instalar e definir `GHOSTSCRIPT_BIN` |
| `/health` 200 mas sem Chrome | Navegador não instalado ou perfil do Chrome não existe para a conta do serviço |
| Erro na busca | Ver `C:\ProgramData\PontoSmsWeb\logs\err.log` (ou console/agendador) |

```powershell
# Acompanhar em tempo real
Get-Content C:\ProgramData\PontoSmsWeb\logs\err.log -Wait

# Reiniciar
nssm restart PontoSmsWeb
```

---

## 11. Checklist final de implantação

- [ ] Python 3.12 instalado no PATH
- [ ] Chrome/Edge instalado e funcionando
- [ ] Repositório clonado e na branch `PontoSmsWeb`
- [ ] `scripts\setup_prod.ps1` executado sem erros (venv + deps + `.env`)
- [ ] `.env` preenchido (`USER/PASSWORD/URL_*`, `WEB_USERS`, `SESSION_SECRET`)
- [ ] Teste manual: `/health` → `env_ok:true`; frontend faz login e gera arquivo
- [ ] Pré-login no portal feito (janela minimizada / cookies salvos)
- [ ] Serviço NSSM instalado e `Running` (ou tarefa agendada — seção 7.1)
- [ ] Firewall liberado na porta 8000
- [ ] Acesso remoto `http://<ip-da-vm>:8000/` OK
- [ ] Continuidade: `git pull` + `setup_prod.ps1` + `nssm restart` documentado
- [ ] (Opcional) Desktop em paralelo: build PyInstaller da `version_2.3.1` + teste
```