# Guia: Stealth do Navegador e Perfil com Sessão Persistente

## Contexto

O reCAPTCHA v2 exige múltiplas rodadas de verificação de imagem quando detecta
que o navegador é uma automação. Isso ocorre porque:

1. **Fingerprint do navegador** detecta `navigator.webdriver=true`, plugins
   artificiais, user-agent genérico
2. **Sem histórico de navegação** — perfil novo sem cookies do Google, sem
   buscas anteriores
3. **IP de datacenter** — se o servidor está em cloud, o IP pode ter
   reputação ruim
4. **Comportamento do mouse** — movimentos lineares, cliques instantâneos

## Fluxo Proposto pelo Usuário

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Abrir navegador com perfil Chrome real (com sessão Google)  │
│  2. Login no portal → resolver captcha (1 rodada máxima)        │
│  3. Sessão salva no perfil (cookies persistidos)                │
│  4. Fechar navegador após processamento                         │
│  5. Próxima vez: abrir mesmo perfil → sessão válida → sem login │
│  6. Só fazer login quando sessão expirar                        │
└─────────────────────────────────────────────────────────────────┘
```

## Viabilidade Técnica

### SIM, é possível. O fluxo já está parcialmente implementado.

**O que já funciona:**
- Perfil persistente via `--user-data-dir` (`~/.ponto_sms_flet/chrome_profile`)
- Cookies salvos/carregados manualmente (`_save_cookies` / `_load_cookies`)
- Detecção de sessão via formulário de login (`_session_alive`)
- Reutilização de janela (`park_driver` / `get_driver`)

**O que falta (e por que não funciona hoje):**

| Problema | Causa | Solução |
|----------|-------|---------|
| Cookies não persistem entre sessões | Perfil sintético sem histórico real | Usar perfil Chrome real com sessão Google |
| reCAPTCHA exige múltiplas rodadas | Fingerprint detecta automação | Melhorar stealth + perfil com histórico |
| `_clear_portal_cookies` apaga tudo | Limpa cookies antes do login | Só limpar PHPSESSID, não todos |
| Perfil não tem Google logado | Perfil criado do zero | Setup inicial manual + reuso |

---

## Parte 1: Melhoria do Stealth (Redução de Rodadas)

### 1.1 Técnicas Atuais (mínimas)

```python
# browser_session.py — atual
stealth(driver, languages=['pt-BR'], vendor='Google Inc.', ...)
# + CDP: navigator.webdriver = undefined
```

### 1.2 Técnicas Adicionais (recomendadas)

#### A) CDP Script Injection (antes de qualquer navegação)

```javascript
// navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// navigator.plugins (simular plugins reais)
Object.defineProperty(navigator, 'plugins', {
  get: () => [1, 2, 3, 4, 5].map(() => ({
    name: 'Chrome PDF Plugin',
    description: 'Portable Document Format',
    filename: 'internal-pdf-viewer',
    length: 1
  }))
});

// navigator.languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['pt-BR', 'pt', 'en-US', 'en']
});

// chrome.runtime (fingir extensão)
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };

// permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
  parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);
```

#### B) User-Agent Realista

```python
options.add_argument(
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
)
```

#### C) Desabilitar Detecção de Automação

```python
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('excludeSwitches', [
    'enable-automation',
    'enable-blink-features=AutomationControlled'
])
```

#### D) Mouse Movement Humano (opcional, avançado)

```python
from selenium.webdriver.common.action_chains import ActionChains
import random, time

def human_like_move(driver, element):
    """Move o mouse de forma humana até o elemento."""
    actions = ActionChains(driver)
    offset_x = random.randint(-5, 5)
    offset_y = random.randint(-5, 5)
    actions.move_to_element_with_offset(element, offset_x, offset_y)
    actions.pause(random.uniform(0.1, 0.3))
    actions.click()
    actions.perform()
```

### 1.3 Implementação no `browser_session.py`

Adicionar nova função `_apply_advanced_stealth(driver)`:

```python
def _apply_advanced_stealth(driver) -> None:
    """Aplica técnicas avançadas de anti-detecção via CDP."""
    stealth_js = """
    // navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

    // navigator.plugins
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5].map(() => ({
        name: 'Chrome PDF Plugin',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        length: 1
      }))
    });

    // navigator.languages
    Object.defineProperty(navigator, 'languages', {
      get: () => ['pt-BR', 'pt', 'en-US', 'en']
    });

    // chrome.runtime
    window.chrome = window.chrome || {};
    window.chrome.runtime = window.chrome.runtime || {};

    // permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
    """
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {'source': stealth_js}
    )
```

---

## Parte 2: Perfil Chrome com Sessão Google

### 2.1 Por que um Perfil Real Ajuda?

O reCAPTCHA v2 usa sinais para determinar se o usuário é humano:

| Sinal | Perfil Sintético | Perfil Real |
|-------|------------------|-------------|
| Google logado | ❌ Não | ✅ Sim |
| Histórico de buscas | ❌ Vazio | ✅ Real |
| Cookies do Google | ❌ Nenhum | ✅ Presentes |
| Extensões | ❌ Nenhuma | ✅ 1-2 reais |
| Localização | ❌ Genérica | ✅ Consistente |

### 2.2 Diretório do Perfil

**Atual:**
```
~/.ponto_sms_flet/chrome_profile/    ← perfil sintético (criado do zero)
```

**Proposto:**
```
~/.ponto_sms_flet/chrome_profile/    ← mesmo diretório, mas com setup inicial
```

A mudança não é no diretório, mas no **conteúdo** do perfil.

### 2.3 Setup Inicial do Perfil (uma única vez)

O perfil precisa ser configurado manualmente UMA VEZ para ter:

1. **Conta Google logada** — login no google.com.br
2. **Algumas buscas no Google** — 5-10 buscas aleatórias
3. **Um site visitado** — qualquer site notício (g1.com.br, uol.com.br)
4. **Extensão real** — optional: adblocker ou similar

**Passo a passo do setup:**

```
1. Fechar qualquer instância do app ponto_sms_flet
2. Abrir Chrome manualmente com o perfil do app:
   chrome.exe --user-data-dir="C:\Users\{user}\.ponto_sms_flet\chrome_profile"
3. Fazer login no Google (google.com.br)
4. Fazer 5-10 buscas no Google (assuntos variados)
5. Visitar 2-3 sites noticiosos (g1, uol, folha)
6. Fechar o Chrome
7. Abrir o app ponto_sms_flet normalmente
```

### 2.4 O que o Perfil Preserva

O Chrome salva no perfil:
- `Default/Cookies` — cookies de todas as sessões (Google, sites visitados)
- `Default/Login Data` — senhas salvas (opcional)
- `Default/History` — histórico de navegação
- `Default/Preferences` — configurações do Chrome
- `Local State` — estado local do Chrome

### 2.5 O que NÃO Preserva (e Por Que)

| Dado | Preserva? | Motivo |
|------|-----------|--------|
| Cookies do Google | ✅ Sim | `--user-data-dir` persiste tudo |
| Sessão do portal | ⚠️ Parcial | PHPSESSID é session cookie (expira ao fechar) |
| Histórico de buscas | ✅ Sim | Salvo no `Default/History` |
| Extensões | ✅ Sim | Salvas no `Default/Extensions` |
| Senhas | ⚠️ Opcional | Depende das prefs do Chrome |

---

## Parte 3: Gerenciamento de Sessão do Portal

### 3.1 Problema Atual

O portal usa **session cookies** (`PHPSESSID`) que expiram quando o navegador
fecha. Mesmo com perfil persistente, a sessão do portal não sobrevive ao
fechamento do Chrome.

### 3.2 Solução: Não Limpar Cookies Automaticamente

**Atual** (`auth_core.py:271`):
```python
_clear_portal_cookies(driver, url_base)  # limpa TODOS os cookies do portal
```

**Proposto:**
```python
_clear_stale_php_sessions(driver, url_base)  # só limpa PHPSESSID duplicados
```

A função `clear_portal_cookies` limpa TODOS os cookies, incluindo os que
o portal pode reutilizar. A função proposta só limpa PHPSESSID duplicados.

### 3.3 Fluxo de Sessão Proposto

```
┌─────────────────────────────────────────────────────────────────┐
│  get_driver() chamado                                           │
│  ├─ Perfil tem cookies do Google?                               │
│  │  ├─ SIM → reCAPTCHA mostra 1 rodada (ou nenhuma)            │
│  │  └─ NÃO → reCAPTCHA mostra 3-5 rodadas (atual)              │
│  ├─ PHPSESSID existe e é válido?                                │
│  │  ├─ SIM → pular login, ir direto para URL_DATA               │
│  │  └─ NÃO → login com captcha                                 │
│  └─ Após login: salvar cookies mas NÃO limpar PHPSESSID         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Modificações Necessárias

#### A) `auth_core.py` — Limpar Só Duplicados

```python
def _clear_stale_php_sessions(driver, url_base: str) -> None:
    """Remove apenas PHPSESSID duplicados, preservando a sessão válida."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url_base).hostname or ''
        cookies = driver.get_cookies()
        php_sessions = [
            c for c in cookies
            if c.get('name') == 'PHPSESSID' and domain in c.get('domain', '')
        ]
        if len(php_sessions) > 1:
            # Manter o mais recente, remover os outros
            for c in php_sessions[:-1]:
                driver.delete_cookie(c['name'])
    except Exception:
        pass
```

#### B) `session_manager.py` — Não Chamar `_clear_portal_cookies`

Remover a chamada `_clear_portal_cookies(driver, url_base)` do `authenticate`.

#### C) `session_manager.py` — Salvar Cookies Após Login

```python
# Após authenticate retornar 'success':
_driver = driver
_save_cookies(driver)        # salva PHPSESSID + outros cookies
_prepare_window(driver, preload_url)
```

---

## Parte 4: Fluxo Completo Proposto

### 4.1 Primeira Execução (Setup)

```
1. Usuário abre o app
2. Chrome abre com perfil vazio
3. Usuário resolve captcha (3-5 rodadas — perfil novo)
4. Login realizado → cookies salvos em disco
5. Dados processados → navegador FECHADO
```

### 4.2 Segunda Execução (Sessão Ativa)

```
1. Usuário abre o app
2. Chrome abre com mesmo perfil
3. Cookies injetados → PHPSESSID válido
4. Sessão ativa detectada → SEM login
5. Dados processados → navegador FECHADO
```

### 4.3 Execução com Sessão Expirada

```
1. Usuário abre o app
2. Chrome abre com mesmo perfil
3. Cookies injetados → PHPSESSID expirado
4. Sessão expirada detectada → login necessário
5. reCAPTCHA mostra 1-2 rodadas (perfil tem histórico)
6. Login realizado → cookies renovados
7. Dados processados → navegador FECHADO
```

---

## Parte 5: Resumo das Mudanças

### Arquivos a Modificar

| Arquivo | Mudança | Prioridade |
|---------|---------|------------|
| `services/browser_session.py` | Adicionar `_apply_advanced_stealth()` | Alta |
| `services/auth_core.py` | Trocar `_clear_portal_cookies` por `_clear_stale_php_sessions` | Alta |
| `services/captcha_solver.py` | Não precisa mudar | — |
| `backend/app/session_manager.py` | Ajustar fluxo de cookies | Média |

### Scripts de Setup

| Script | Propósito |
|--------|-----------|
| `scripts/setup_profile.py` | Setup inicial do perfil (abre Chrome para configuração manual) |
| `scripts/verify_profile.py` | Verifica se o perfil tem Google logado |

### Ordem de Implementação

1. **Stealth avançado** (`browser_session.py`) — impacto imediato
2. **Limpeza seletiva de cookies** (`auth_core.py`) — preserva sessão
3. **Script de setup** (`scripts/setup_profile.py`) — facilita configuração
4. **Testes** — verificar se sessão persiste entre execuções

---

## Referências

- [Selenium Stealth](https://github.com/MeinLiX/selenium-stealth)
- [reCAPTCHA v2 Detection Signals](https://developers.google.com/recaptcha/docs/faq)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
