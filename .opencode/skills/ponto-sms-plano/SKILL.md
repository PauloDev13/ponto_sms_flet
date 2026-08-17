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
- **Pendente:** FASES 4 (multi-usuário/segurança) e 5 (Docker/CI/testes E2E).

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
    unidades_service.py, settings.py, paths.py, exceptions.py
frontend/index.html    # UI completa (FASE 3)
services/, config/     # código legado do desktop (manter até FASE 5)

```

## Como rodar

- Backend web: `uvicorn backend.app.main:app --reload` (porta 8000).
  Requer as variáveis do `.env` (USER, PASSWORD, URL_*, NAME_FOLDER).
- Testes: `python -m pytest tests -q` (venv `.venv` na raiz; deps web:
  fastapi, uvicorn, pytest, httpx, python-dotenv, pandas, xlsxwriter, pypdf,
  selenium, lxml, openpyxl).
- `tests/test_jobs_api.py` injeta um JobManager com runner fake (sem Chrome)
  através de `main_module.JOB_MANAGER = JobManager(run_fn=...)`.

## FASE 4 — Robustez/segurança (próxima)

Objetivo: multi-usuário e isolamento de sessão; credenciais protegidas.

1. Sessões web autenticadas (cookie/JWT), pool de drivers por usuário
   thread-safe (hoje há 1 driver global — lembrança de sessão por usuário
   deve mapear para drivers distintos; a fila do JobManager já é serializada).
2. USER/PASSWORD apenas via secrets (nunca expor na API/frontend —
   hoje aparecem mascarados em /health; manter sempre `masked_user`).
3. Rate-limit por IP/job; timeout e retry no scraper.
Aceite: 2 usuários simultâneos não interferem; credenciais nunca transitam.

## FASE 5 — Deploy e validação

- Dockerfile + CI: Python 3.12, Chrome, Ghostscript, fontes pt_BR,
  units.csv; `docker compose` dev; CI com py_compile + pytest.
- Testes E2E: validators, scraper (mocks), Excel/PDF, divisão por tamanho.
- Manter desktop em paralelo só até web validar em produção.
Aceite: suíte verde e funcionalidades inventariadas 100% cobertas na web.

## Regras de convenção do projeto

- `core/` nunca importa flet/UI; erros via exceções tipadas + logging.
- Caminhos de saída sempre via `settings.output_dir` — jamais
  `os.path.expanduser('~')` dentro dos serviços.
- Nomes de arquivo gerados preservam o padrão desktop
  (ex.: `MARIA SOUZA - CPF_529.982.247-25.xlsx`).
- Nenhum segredo entra em commit; `.env` não é versionado.
- Testes novos seguem o padrão `tests/` já existente (pytest + TestClient).