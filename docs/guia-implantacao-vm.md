# Guia de Implantação — Web em Produção na VM Windows

Guia passo a passo para subir a versão web do ponto eletrônico em uma
**VM Windows 10/11** com Chrome instalado.

---

## Pré-requisitos

| Item | Obrigatório? |
|---|---|
| Windows 10/11 (64 bits) | Sim |
| Google Chrome | **Sim** |
| Python 3.12 | **Sim** (instalado pelo script) |
| Git | Sim |
| NSSM (`nssm.exe`) | Sim (para modo serviço) |
| Ghostscript (`gswin64c`) | Opcional (compressão PDF) |

---

## Passo 1 — Obter o código

```powershell
New-Item -ItemType Directory -Path C:\Apps -Force | Out-Null
cd C:\Apps
git clone <url-do-repositorio> ponto_sms_flet
cd ponto_sms_flet
git checkout PontoSmsWeb
```

---

## Passo 2 — Instalar Python 3.12

```powershell
cd C:\Apps\ponto_sms_flet
powershell -ExecutionPolicy Bypass -File scripts\install_python.ps1
```

**Abra um NOVO PowerShell** após a instalação. Confirme:

```powershell
python --version
```

---

## Passo 3 — Setup do projeto (venv + dependências)

```powershell
cd C:\Apps\ponto_sms_flet
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
```

Este script:
- Cria o venv `.venv` e instala dependências
- Adiciona exclusões no Windows Defender
- Cria `.env` a partir de `.env.example` (se não existir)
- Gera `SESSION_SECRET` automaticamente

---

## Passo 4 — Configurar o `.env`

Edite `C:\Apps\ponto_sms_flet\.env` e preencha:

```ini
# Login do portal (scraping)
USER='06511122233'
PASSWORD='senha-do-portal'
URL_BASE='https://natal.rn.gov.br/sms/ponto/index.php'
URL_DATA='https://natal.rn.gov.br/sms/ponto/pesquisa.php'
URL_INIT='https://natal.rn.gov.br/sms/ponto/interno/inicio.php'

# Contas da aplicação web (login no browser)
WEB_USERS='admin:senha-forte,maria:senha-forte'
SESSION_SECRET='')

# Opcionais
NAME_FOLDER='PLANILHAS_SMS'
```

---

## Passo 5 — Pré-login (resolver captcha 1ª vez)

> **CRÍTICO:** Este passo DEVE ser executado pelo **mesmo usuário** que
> rodará o serviço NSSM. Se o serviço rodará como `PGM\paulo.morais`,
> conecte-se à VM via RDP como `paulo.morais` e execute este comando.

```powershell
cd C:\Apps\ponto_sms_flet
.\.venv\Scripts\python.exe scripts\pre_login.py --manual-wait 180
```

- Chrome abre → resolva o captcha manualmente
- Ao terminar com `session_active` ou `success`, os cookies são salvos em:
  `C:\Users\<usuario>\.ponto_sms_flet\cookies.json`
- Se falhar, execute novamente até obter sucesso

---

## Passo 6 — Instalar NSSM (se não estiver no PATH)

```powershell
New-Item -ItemType Directory -Path "C:\Tools\nssm" -Force | Out-Null
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"
Expand-Archive -Path "$env:TEMP\nssm.zip" -DestinationPath "$env:TEMP\nssm" -Force
Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" "C:\Tools\nssm\nssm.exe" -Force
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($CurrentPath -notlike "*C:\Tools\nssm*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;C:\Tools\nssm", "Machine")
}
$env:Path = "$env:Path;C:\Tools\nssm"
nssm --version
```

---

## Passo 7 — Instalar o serviço NSSM

> **CRÍTICO:** O serviço DEVE rodar como o **mesmo usuário** do passo 5.
> Senão, os cookies serão encontrados em local errado e o Chrome não
> terá desktop interativo.

### 7.1 Conta de domínio (ex: `PGM\paulo.morais`)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1 `
    -ServiceUser 'PGM\paulo.morais' `
    -ServicePassword 'senha-do-usuario'
```

### 7.2 Conta local (ex: `paulo.morais`)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_service.ps1 `
    -ServiceUser 'paulo.morais' `
    -ServicePassword 'senha-do-usuario'
```

### 7.3 Verificar

```powershell
Get-Service PontoSmsWeb
Invoke-RestMethod http://127.0.0.1:8000/health
```

---

## Passo 8 — Liberar firewall (se necessário)

```powershell
New-NetFirewallRule -DisplayName 'PontoSmsWeb 8000' `
  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## Passo 9 — Testar o frontend

Abra o navegador em `http://<ip-da-vm>:8000/`:

1. Login com usuário/senha de `WEB_USERS`
2. Preencha CPF + unidade + período
3. Clique em "Gerar"
4. Acompanhe a barra de progresso até 100%
5. Baixe os arquivos gerados

---

## Renovação de sessão (quando expirar)

Quando a sessão do portal expirar, o próximo job mostrará erro.
Para renovar:

1. Conecte-se à VM via RDP **como o usuário do serviço**
2. Execute:
   ```powershell
   cd C:\Apps\ponto_sms_flet
   .\.venv\Scripts\python.exe scripts\pre_login.py --manual-wait 180
   ```
3. Resolva o captcha
4. O serviço detectará automaticamente a nova sessão no próximo job

**Não é necessário reiniciar o serviço.**

---

## Deploy de novas versões

```powershell
cd C:\Apps\ponto_sms_flet
git pull origin PontoSmsWeb
powershell -ExecutionPolicy Bypass -File scripts\setup_prod.ps1
nssm restart PontoSmsWeb
```

---

## Checklist

- [ ] Python 3.12 instalado (`python --version`)
- [ ] Clone da branch `PontoSmsWeb` em `C:\Apps\ponto_sms_flet`
- [ ] `setup_prod.ps1` executado (venv + deps + `.env`)
- [ ] `.env` preenchido (USER, PASSWORD, URL_*, WEB_USERS)
- [ ] `pre_login.py` concluído com sucesso (cookies salvos)
- [ ] Serviço `PontoSmsWeb` rodando como o **mesmo usuário** do pre_login
- [ ] `Invoke-RestMethod http://127.0.0.1:8000/health` retorna `env_ok:true`
- [ ] Frontend: login, geração, download OK
