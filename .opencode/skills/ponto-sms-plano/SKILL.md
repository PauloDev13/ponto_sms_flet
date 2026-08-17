---
name: ponto-sms-plano
description: Plano de execução e arquitetura da migração do app desktop Flet para web (FastAPI + Jinja2/JS). Use quando for implementar as FASES 4-5 do plano (multi-usuário, segurança, deploy Docker, testes E2E) ou quando precisar lembrar onde cada módulo do backend web vive e como os testes rodam.
---

# Plano de migração desktop -> web (ponto_sms_flet)

Aplicação de consulta de ponto eletrônico (portal SMS). Original em Flet +
PyInstaller; está sendo refatorada para monorepo web com FastAPI no backend
e HTML/CSS/JS puro (sem framework) no frontend. O scraping continua usando
Selenium/Chrome com perfil persistente.

## Estado atual (implementado)

- **FASE 0 (feita):** `backend/` (FastAPI + `core/`), `frontend/` (Jinja2/JS
  puro substituído por `frontend/index.html` estático servido pela API);
  `/health`, `POST /api/v1/validate`, `GET /api/v1/unidades?q=`; configuração
  em `backend/core/settings.py` (ler .env, `OUTPUT_DIR` central, sem Flet).
- **FASE 1 (feita):** serviços de dados/acesso desacoplados em
  `backend/core/` sem dependência de Flet (logging + exceções tipadas em
  `core/exceptions.py`: `CoreError`, `LoginError`, `ScrapeError`,
  `FileGenerationError`); caminhos centralizados em `core/paths.py`
  baseados em `settings.output_dir`.
- **FASE 2 (feita):** `core/job.py` (Job, JobStatus, JobFile, JobManager com
  ThreadPoolExecutor serializado), `core/scraper.py` com progresso por mês
  (`on_month_status`), sessão persistente em `backend/app/session_manager.py`
  (driver único + relogin), endpoints de jobs + SSE.
- **FASE 3 (feita):** formulário completo em `frontend/index.html` com
  validação client+server, máscaras (CPF, MM/yyyy), autocomplete de unidades,
  progresso via SSE (`GET /api/v1/jobs/{id}/events`), download
  (`GET /api/v1/jobs/{id}/download?format=xlsx|pdf|zip` e
  `?format=pdf&parts=zip`, `GET /api/v1/jobs/{id}/files/{filename}`),
  auto-download ao concluir (com render final da barra em DONE, garantindo
  100% mesmo em jobs rápidos de só-Excel), seção "Arquivos", histórico navegável
  (`GET /api/v1/jobs`), limpeza manual do histórico (`DELETE /api/v1/jobs`;
  remove terminais + pastas, preserva jobs em execução), exclusão individual
  (`DELETE /api/v1/jobs/{id}`, 409 se em andamento), modal de confirmação
  (sem `window.confirm`) e limpeza agendada por TTL (lifespan do FastAPI, `JOB_TTL_HOURS`,
  `JOBS_HISTORY_LIMIT`).
- **Correções pós-avaliação (FASE 2/3):**
  - Janela do backend: mantida ABERTA e minimizada após o processamento
    (`park_driver()` ao fim do job); o próximo processamento reutiliza a
    MESMA janela (`get_driver`) e, com a sessão viva no navegador,
    dispensa novo login/captcha; só abre maximizada para novo login;
    `close_driver()` (fechamento real) é usado no shutdown do servidor
    (lifespan do FastAPI).
  - Sessão entre janelas: cookies salvos em `~/.ponto_sms_flet/cookies.json`
    como redundância (caso o navegador seja recriado) e renovados apenas
    com a sessão CONFIRMADA ativa (validação pós-login via `_session_alive`);
    detecção de sessão pela PRESENÇA DO FORMULÁRIO DE LOGIN na página
    interna (URL_INIT), robusta a redirects; maximize idempotente
    (Chrome >= 151 lança erro se maximizar janela já maximizada).
  - Cancelamento: `POST /api/v1/jobs/{id}/cancel` (nova rota) + status
    CANCELLED; `cancel_check` entre meses no scraper; sessão perdida na
    coleta (janela fechada/erro) aborta com `JobCancelledError` em vez de
    insistir em segundo plano; "Nova Consulta" no frontend cancela a
    geração ativa.
  - Reuso de sessão: `session_manager._session_alive` navega para `URL_INIT`
    (página interna), não para `URL_BASE` — cookie persistente reaproveitado;
    novo login só quando o portal redirecionar para a página de login.
  - Totais do Excel: `count_markers()` calcula HT/HJ/ST/ADN na geração e
    `write_array_formula(value=total)` grava o valor em cache junto da
    fórmula — sem isso o LibreOffice (e o Modo de Exibição Protegido de
    arquivos baixados) exibe as células de TOTAIS vazias.
- **FASE 4 (feita):** multi-usuário e segurança:
  - Sessão web autenticada por cookie assinado (HMAC-SHA256,
    HttpOnly/SameSite=Lax, expiração via `SESSION_TTL_HOURS`);
    contas locais `WEB_USERS` com senhas hash PBKDF2
    (`backend/app/auth.py`); login/logout/`/me`; todos os endpoints de
    jobs escopados por usuário (`job.owner` + 403/404).
  - Credenciais nunca expostas: `/health` só devolve `masked_user`;
    `USER/PASSWORD` jamais via API/frontend.
  - Rate-limit: login por IP (8/60s, `auth.py`) e criação de jobs por
    usuário+IP (`JOB_MAX_ACTIVE=3` ativos + `_JOB_CREATE_LIMIT=10`/min).
  - Retry no scraper: `fetch_month_table` tenta `SCRAPE_RETRIES=2` com
    `RETRY_BACKOFF=3s` para timeouts TRANSITÓRIOS; NUNCA retenta quando a
    sessão caiu (`session_lost`) — aborta com `JobCancelledError`.
  - **Decisão documentada (drivers):** o pool de drivers por usuário NÃO
    foi implementado de propósito. A fila é serial (1 worker) e o portal
    tem UMA conta (USER/PASSWORD) compartilhada por todos os usuários web;
    portanto um driver único + serializer já garante o isolamento exigido
    ("2 usuários simultâneos não interferem") sem custo nem risco extra.
- **Pendente (FASE 5):** deploy e validação.

## Arquitetura (mapa de módulos)

```
backend/
  app/
    main.py            # FastAPI: health, validate, unidades, jobs, SSE,
                       # download, / (frontend estático); lifespan com cleanup TTL
    ponto_service.py   # run_ponto_flow (ZIP legado, POST /api/v1/ponto) e
                       # run_job_flow (executor de jobs; nomes de arquivo iguais
                       # ao desktop: "{nome} - CPF_{cpf}.xlsx", "_partN.pdf")
    session_manager.py # driver único + sessão persistente (relogin automático)
  core/
    job.py             # JobManager: QUEUED->RUNNING->DONE/FAILED, progresso,
                       # logs, files, version (para SSE), cleanup_expired(ttl),
                       # clear() (limpa histórico)
    scraper.py         # scrape_months(...) + on_month_status(month, success, msg)
    excel_service.py, pdf_service.py, dataframe.py, validators.py,
    unidades_service.py, settings.py, paths.py, exceptions.py,
    auth_core.py, browser_session.py, captcha_solver.py  # movidos de services/ (Parte B)
frontend/index.html    # UI completa (FASE 3)
desktop/               # código legado do desktop (Flet/PyInstaller), isolado:
  main.py, models/, utils/, controls/, config/ (config_env), services/
  (authenticate_service, data/*, compress/divide_pdf_file), requirements.txt
data/                  # compartilhado (unidades.csv, outputs)
scripts/               # utilitários (debug, deploy web)

```

## Como rodar

- Backend web: `uvicorn backend.app.main:app --reload` (porta 8000).
  Requer as variáveis do `.env` (USER, PASSWORD, URL_*, NAME_FOLDER).
- Testes: `python -m pytest tests -q` (venv `.venv` na raiz; deps web:
  fastapi, uvicorn, pytest, httpx, python-dotenv, pandas, xlsxwriter, pypdf,
  selenium, lxml, openpyxl).
- `tests/test_jobs_api.py` injeta um JobManager com runner fake (sem Chrome)
  através de `main_module.JOB_MANAGER = JobManager(run_fn=...)`.

## FASE 4 — Robustez/segurança (feita)

Objetivo: multi-usuário e isolamento de sessão; credenciais protegidas.

1. Sessões web autenticadas (cookie assinado — ver "Estado atual").
2. USER/PASSWORD apenas via secrets (nunca expor na API/frontend; /health
   usa sempre `masked_user`).
3. Rate-limit por IP/job (login 8/60s; jobs `JOB_MAX_ACTIVE` + N/min).
Aceite: 2 usuários simultâneos não interferem; credenciais nunca transitam —
coberto por `tests/test_isolation.py` e `tests/test_auth_api.py`.

## FASE 5 — Deploy e validação

Objetivo: empacotar/validar a web para produção e deixar a suíte verde com
cobertura garantida nas funcionalidades.

- **CI pronto**: `.github/workflows/ci.yml` (Python 3.12, `pip install -r
  requirements-web.txt`, `compileall` em backend/scripts/tests/desktop +
  `pytest tests -q`). Roda em push/PR na branch `PontoSmsWeb`.
- **Produção VM (Parte D)**: `scripts/setup_prod.ps1` (setup idempotente:
  venv, deps web, checagem Chrome/Ghostscript, CSV, .env sem sobrescrever),
  `scripts/install_service.ps1` (serviço NSSM `PontoSmsWeb`, uvicorn :8000,
  autorestart + rotação de logs) e `docs/runbook-deploy.md` (D3: git pull →
  setup → nssm restart; D4: plano B do desktop em `version_2.3.1`).
  Guia completo passo a passo: `docs/guia-producao.md`.
- **Inventário (Parte E5)**: `docs/inventario-cobertura.md` — checklist
  desktop→web com status/teste de cada funcionalidade.
- **Testes E2E/unit**: todos presentes e verdes — `test_core_validators.py`
  (dedicado), `test_core_ponto_service.py` (normalize_cpf, format_cpf_br,
  parse_br_month), `test_core_scraper.py` (mocks, retries, sessão perdida,
  cancelamento), `test_core_excel.py` + `test_excel_totals.py`,
  `test_core_pdf.py` (combine + divide_pdf_by_size + compressão com
  Ghostscript mockado), `test_jobs_api.py`, `test_isolation.py`,
  `test_auth_api.py`, `test_session_manager.py`, `test_settings_reload.py`.
- **Pendente**: arquivos Docker (Dockerfile + `docker compose` dev) — opcional,
  a VM usa venv + NSSM.
- Manter desktop em paralelo só até web validar em produção.
Aceite: suíte verde (162 testes) e funcionalidades inventariadas 100%
cobertas na web.

## Regras de convenção do projeto

- `core/` nunca importa flet/UI; erros via exceções tipadas + logging.
- Caminhos de saída sempre via `settings.output_dir` — jamais
  `os.path.expanduser('~')` dentro dos serviços.
- Nomes de arquivo gerados preservam o padrão desktop
  (ex.: `MARIA SOUZA - CPF_529.982.247-25.xlsx`).
- Nenhum segredo entra em commit; `.env` não é versionado.
- Testes novos seguem o padrão `tests/` já existente (pytest + TestClient).