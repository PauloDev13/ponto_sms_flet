# Guia Rápido de Teste - Correções Cenário 2

## Teste Completo (5 passos)

```powershell
# 1 - Parar o serviço
nssm stop PontoSmsWeb

# 2 - Executar pre-login (resolva o captcha na janela)
.\.venv\Scripts\python.exe scripts\pre_login.py --manual-wait 180

# 3 - Reiniciar o serviço
nssm restart PontoSmsWeb

# 4 - Aguardar 10 segundos
Start-Sleep -Seconds 10

# 5 - Acessar o frontend e testar geração
# http://<IP_DA_VM>:8000
# Login: admin / admin123
# Solicite uma geração de planilha
```

## Verificação de Logs

```powershell
# Ver últimos 30 linhas do log
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" -Tail 30

# Procurar por erros
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" | Select-String "SESSÃO DO PORTAL EXPIRADA"

# Verificar se cookies foram encontrados
Get-Content "C:\ProgramData\PontoSmsWeb\logs\out.log" | Select-String "COOKIES_FILE"
```

## Resultados Esperados

| Passo | ✅ Sucesso | ❌ Falha |
|-------|-----------|----------|
| pre-login | Cookies salvos em `C:\Users\<user>\.ponto_sms_flet\` | Erro ao salvar cookies |
| Serviço inicia | Status `SERVICE_RUNNING` | Serviço não inicia |
| Logs | `COOKIES_FILE (exists=True)` | `COOKIES_FILE (exists=False)` |
| Geração | Planilha gerada com sucesso | Erro "SESSÃO DO PORTAL EXPIRADA" |
| Chrome | Janelas do usuário preservadas | Todas as janelas fechadas |

## Solução se Falhar

Se o erro "SESSÃO DO PORTAL EXPIRADA" persistir, o serviço está como LocalSystem. Reinstale com usuário:

```powershell
nssm stop PontoSmsWeb
nssm remove PontoSmsWeb confirm
.\scripts\install_service.ps1 -ServiceUser 'USUARIO' -ServicePassword 'SENHA'
```
