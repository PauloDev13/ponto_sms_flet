# Guia de Teste - Correções Cenário 2 (Serviço NSSM)

## Visão Geral

Este guia orienta a validação das correções para os problemas:
1. **Fechamento de todas as janelas do Chrome** ao iniciar o serviço
2. **Erro "SESSÃO DO PORTAL EXPIRADA"** ao gerar planilhas

### Arquivos Modificados
- `backend/app/session_manager.py` - Detecção de contexto de serviço
- `backend/core/browser_session.py` - Limpeza de processos e resolução de caminhos
- `scripts/pre_login.py` - Unificação de caminhos de cookies

---

## FASE 1: Validação Local (Antes de Publicar na VM)

### Passo 1.1: Verificar Compilação
```powershell
cd C:\Desenvolvimento\__PROJETOS_PYTHON\ponto_sms_flet
.\.venv\Scripts\python.exe -m py_compile backend\app\session_manager.py
.\.venv\Scripts\python.exe -m py_compile backend\core\browser_session.py
.\.venv\Scripts\python.exe -m py_compile scripts\pre_login.py
```

**✅ Esperado:** Nenhuma mensagem de erro  
**❌ Falha:** Mensagens de erro de sintaxe

### Passo 1.2: Executar Testes Unitários
```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_session_manager.py -v
```

**✅ Esperado:** Todos os testes passam  
**❌ Falha:** Testes falhando

### Passo 1.3: Verificar Importações
```powershell
.\.venv\Scripts\python.exe -c "from backend.app.session_manager import get_driver, _is_service_context; print('Import OK')"
```

**✅ Esperado:** Mensagem "Import OK"  
**❌ Falha:** Erro de importação

---

## FASE 2: Teste do Servidor Manual (Cenário 1)

### Passo 2.1: Iniciar Servidor
```powershell
cd C:\Desenvolvimento\__PROJETOS_PYTHON\ponto_sms_flet
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Passo 2.2: Verificar Logs de Diagnóstico
Observe o terminal e verifique se aparece:

```
INFO: _is_service_context: PID=XXXX, SessionID=X, HOME=C:\Users\..., USERPROFILE=C:\Users\...
INFO: _is_service_context: SessionID=X != 0, retornando False
INFO: DIAG default_profile_dir: source=HOME, HOME=C:\Users\... (exists=True), ...
```

**✅ Esperado:**
- SessionID **diferente de 0** (execução interativa)
- `source=HOME` ou `source=USERPROFILE`
- `exists=True` para o diretório do usuário

**❌ Falha:**
- SessionID = 0 (estaria detectando como serviço incorretamente)
- `exists=False` para o diretório do usuário

### Passo 2.3: Testar Geração de Planilha
1. Acesse `http://127.0.0.1:8000`
2. Faça login com `admin` / `admin123`
3. Preencha o formulário:
   - CPF: `065.605.074-83`
   - Unidade: qualquer uma da lista
   - Período: `01/2024` a `01/2024`
   - Marque: Excel
4. Clique em "Gerar"

**✅ Esperado:**
- Nenhuma janela Chrome é fechada
- Planilha é gerada com sucesso
- Mensagem de sucesso aparece

**❌ Falha:**
- Janela Chrome é fechada
- Erro "SESSÃO DO PORTAL EXPIRADA"

### Passo 2.4: Encerrar Servidor
Pressione `Ctrl+C` no terminal

---

## FASE 3: Teste com pre_login.py

### Passo 3.1: Executar pre_login.py
```powershell
cd C:\Desenvolvimento\__PROJETOS_PYTHON\ponto_sms_flet
.\.venv\Scripts\python.exe scripts\pre_login.py --manual-wait 180
```

### Passo 3.2: Resolver Captcha
1. Uma janela do Chrome abrirá maximizada
2. Resolva o captcha manualmente
3. Aguarde a mensagem de sucesso

### Passo 3.3: Verificar Cookies Salvos
```powershell
Get-Content "$env:USERPROFILE\.ponto_sms_flet\cookies.json" | Select-Object -First 5
```

**✅ Esperado:**
- Arquivo existe e contém JSON com cookies
- Mensagem no terminal: "Cookies salvos: ... (X cookies)"

**❌ Falha:**
- Arquivo não existe
- Mensagem de erro ao salvar

### Passo 3.4: Verificar Caminho dos Cookies
Observe o terminal do `pre_login.py` e verifique:
```
DIAG default_profile_dir: source=HOME, HOME=C:\Users\... (exists=True), ...
```

**✅ Esperado:**
- `source=HOME` ou `source=USERPROFILE`
- Caminho aponta para `C:\Users\<usuario>\.ponto_sms_flet\`

---

## FASE 4: Teste do Serviço NSSM (Cenário 2)

### Passo 4.1: Verificar Configuração Atual do Serviço
```powershell
nssm status PontoSmsWeb
nssm get PontoSmsWeb ObjectName
```

**✅ Esperado:**
- Serviço está rodando
- `ObjectName` mostra o usuário configurado (ex: `.\paulo.morais`)

**⚠️ Se `ObjectName` estiver vazio ou `LocalSystem`:**
O serviço está rodando como LocalSystem. Nesse caso, execute:
```powershell
.\scripts\install_service.ps1 -ServiceUser 'paulo.morais' -ServicePassword 'SUA_SENHA'
```

### Passo 4.2: Parar Serviço
```powershell
nssm stop PontoSmsWeb
```

### Passo 4.3: Limpar Logs Antigos
```powershell
Remove-Item "C:\ProgramData\PontoSmsWeb\logs\*.log" -ErrorAction SilentlyContinue
```

### Passo 4.4: Reiniciar Serviço
```powershell
nssm start PontoSmsWeb
```

### Passo 4.5: Aguardar Inicialização
```powershell
Start-Sleep -Seconds 10
nssm status PontoSmsWeb
```

**✅ Esperado:** Status = `SERVICE_RUNNING`

### Passo 4.6: Verificar Logs do Serviço
```powershell
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" -Tail 30
```

**✅ Esperado (serviço com -ServiceUser):**
```
INFO: _is_service_context: PID=XXXX, SessionID=0, HOME=C:\Users\paulo.morais, USERPROFILE=C:\Users\paulo.morais
INFO: _is_service_context: Session 0 detectada, h_winsta=...
INFO: _is_service_context: Session 0 com desktop interativo, retornando False (RDP/sessão isolada)
INFO: DIAG default_profile_dir: source=HOME, HOME=C:\Users\paulo.morais (exists=True), ...
INFO: DIAG: COOKIES_FILE=C:\Users\paulo.morais\.ponto_sms_flet\cookies.json (exists=True, size=XXXX)
INFO: DIAG: XX cookies carregados de ...
```

**⚠️ Se serviço rodar como LocalSystem (sem -ServiceUser):**
```
INFO: _is_service_context: PID=XXXX, SessionID=0, HOME=C:\Windows\system32\config\systemprofile, ...
INFO: _is_service_context: HOME/USERPROFILE aponta para systemprofile, retornando True (LocalSystem)
```
Nesse caso, os cookies NÃO serão encontrados e o erro persistirá.

### Passo 4.7: Testar Geração via Frontend
1. Acesse `http://<IP_DA_VM>:8000`
2. Faça login
3. Solicite geração de planilha

**✅ Esperado:**
- Nenhuma janela Chrome é fechada
- Não aparece erro "SESSÃO DO PORTAL EXPIRADA"
- Geração é concluída com sucesso

**❌ Falha:**
- Todas as janelas Chrome são fechadas
- Erro "SESSÃO DO PORTAL EXPIRADA"

### Passo 4.8: Verificar Processos Chrome
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' } | Select-Object ProcessId, CommandLine | Format-Table -AutoSize
```

**✅ Esperado:**
- Chrome do usuário (profile DEFAULT) **preservado**
- Chrome da aplicação (ponto_sms_flet) **preservado**
- Nenhum Chrome órfão

---

## FASE 5: Teste de Estresse (Opcional)

### Passo 5.1: Múltiplas Gerações Simultâneas
1. Inicie 2-3 gerações ao mesmo tempo via frontend
2. Verifique se não há conflitos de processos

### Passo 5.2: Reinício do Serviço Durante Geração
1. Inicie uma geração
2. Durante o processamento, reinicie o serviço: `nssm restart PontoSmsWeb`
3. Verifique se o serviço reinicia corretamente

---

## Checklist de Validação

| # | Critério | Status |
|---|----------|--------|
| 1 | Compilação sem erros | ☐ |
| 2 | Testes unitários passam | ☐ |
| 3 | Servidor manual funciona (Cenário 1) | ☐ |
| 4 | pre_login.py salva cookies no local correto | ☐ |
| 5 | Serviço NSSM detecta contexto corretamente | ☐ |
| 6 | Serviço NSSM lê cookies do local correto | ☐ |
| 7 | Geração funciona via serviço NSSM (Cenário 2) | ☐ |
| 8 | Janelas Chrome do usuário não são fechadas | ☐ |
| 9 | Logs mostram informações de diagnóstico | ☐ |

---

## Solução de Problemas

### Problema: "SESSÃO DO PORTAL EXPIRADA" persiste
**Causa provável:** Serviço rodando como LocalSystem  
**Solução:** Configurar com `-ServiceUser`:
```powershell
nssm stop PontoSmsWeb
.\scripts\install_service.ps1 -ServiceUser 'USUARIO' -ServicePassword 'SENHA'
nssm start PontoSmsWeb
```

### Problema: Chrome do usuário é fechado
**Causa provável:** `cleanup_all_selenium_browsers` ainda matando processos errados  
**Diagnóstico:** Verificar logs do serviço:
```powershell
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" | Select-String "cleanup_all_selenium_browsers"
```

### Problema: Cookies não são encontrados
**Causa provável:** Caminho incorreto  
**Diagnóstico:** Verificar logs:
```powershell
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" | Select-String "COOKIES_FILE"
```

### Problema: Serviço não inicia
**Causa provabilidade:** Erro na inicialização  
**Diagnóstico:** Verificar logs de erro:
```powershell
Get-Content "C:\ProgramData\PontoSmsWeb\logs\err.log" -Tail 20
```

---

## Comandos Úteis

```powershell
# Status do serviço
nssm status PontoSmsWeb

# Reiniciar serviço
nssm restart PontoSmsWeb

# Parar serviço
nssm stop PontoSmsWeb

# Ver logs em tempo real
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" -Wait

# Verificar processos Chrome
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' }

# Verificar variáveis de ambiente do serviço
nssm get PontoSmsWeb AppEnvironmentExtra
```
