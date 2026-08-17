# Inventário de Cobertura — Funcionalidades Desktop → Web (Parte E5, FASE 5)

Checklist de paridade entre a aplicação desktop (Flet) e a web (FastAPI +
frontend estático). Cada funcionalidade do desktop tem: status na web,
endpoint/arquivo responsável e teste que a cobre.

Legenda: ✅ coberto | ⚠️ parcial | ❌ não implementado (descontinuado)

## 1. Formulário e validação

| Funcionalidade | Web | Responsável | Teste |
|---|---|---|---|
| CPF (11 dígitos + verificadores) | ✅ | `backend/core/validators.py` | `test_core_validators.py` |
| Máscara de CPF ###.###.###-## | ✅ | `backend/app/ponto_service.py:format_cpf_br` | `test_core_ponto_service.py` |
| Datas MM/yyyy (início/fim, ano ≥ 2000, ordem) | ✅ | `validators.validate_dates` | `test_core_validators.py` |
| `parse_br_month` (MM/yyyy → date) | ✅ | `ponto_service.parse_br_month` | `test_core_ponto_service.py` |
| `normalize_cpf` (remove pontuação) | ✅ | `ponto_service.normalize_cpf` | `test_core_ponto_service.py` |
| Unidade obrigatória | ✅ | `validators.validate_unit` | `test_core_validators.py` |
| Ao menos um tipo de arquivo | ✅ | `validators.validate_file_types` | `test_core_validators.py` |
| Validação client-side + máscaras no front | ✅ | `frontend/index.html` (JS) | validação manual/E2E |
| Autocomplete de unidades | ✅ | `GET /api/v1/unidades?q=` | `test_api.py` |

## 2. Coleta de dados (scraping no portal)

| Funcionalidade | Web | Responsável | Teste |
|---|---|---|---|
| `build_search_url` (CPF, mês, ano, unidade) | ✅ | `core/scraper.build_search_url` | `test_core_scraper.py` |
| `fetch_month_table` + retry transitório | ✅ | `core/scraper.fetch_month_table` | `test_core_scraper.py` |
| `scrape_months` (múltiplos meses + progresso) | ✅ | `core/scraper.scrape_months` | `test_core_scraper.py` |
| Sessão perdida aborta (não retenta) | ✅ | `core/scraper.session_lost` | `test_core_scraper.py` |
| Cancelamento entre meses (`cancel_check`) | ✅ | `core/scraper` + `JobCancelledError` | `test_core_scraper.py` |
| Nome do servidor pesquisado (não do logado) | ✅ | `core/scraper.find_employee_name` | `test_core_scraper.py` |
| Login + captcha com sessão persistente | ✅ | `core/auth_core` + `app/session_manager` | `test_auth_core.py`, `test_session_manager.py` |
| Janela minimizada / reuso de sessão | ✅ | `session_manager.get_driver/park_driver` | `test_session_manager.py` |

## 3. Geração de arquivos

| Funcionalidade | Web | Responsável | Teste |
|---|---|---|---|
| Excel com abas por ano | ✅ | `core/excel_service.generate_excel_file` | `test_core_excel.py` |
| Cabeçalho PONTO DIGITAL / linha TOTAIS | ✅ | `core/excel_service.apply_formatting` | `test_core_excel.py` |
| Marcadores HT/HJ/ST/ADN | ✅ | `core/excel_service.count_markers` | `test_excel_totals.py` |
| Fórmula array =SUM(...) com valor em cache | ✅ | `write_array_formula(value=total)` | `test_excel_totals.py` |
| Excel com senha | ✅ | `excel_service` | `test_core_excel.py` |
| Nome do arquivo `{nome} - CPF_{cpf}.xlsx` | ✅ | `ponto_service.run_job_flow` | `test_jobs_api.py`, `test_isolation.py` |
| `combine_pdfs` | ✅ | `core/pdf_service.combine_pdfs` | `test_core_pdf.py` |
| Compressão com Ghostscript | ✅ | `core/pdf_service.compress_pdf_with_ghostscript` | `test_core_pdf.py` (mock GS) |
| Divisão por tamanho (`_partN.pdf`) | ✅ | `core/pdf_service.divide_pdf_by_size` | `test_core_pdf.py` |
| Pipeline PDF (combina+comprime+divide) | ✅ | `process_pdf_artifact` | `test_core_pdf.py` |
| ZIP de download | ✅ | `GET /api/v1/jobs/{id}/download?format=zip` | `test_jobs_api.py` |

## 4. Backend web / infra

| Funcionalidade | Web | Responsável | Teste |
|---|---|---|---|
| Jobs assíncronos + fila serializada | ✅ | `core/job.py` (JobManager) | `test_jobs_api.py` |
| Progresso em tempo real (SSE) | ✅ | `GET /api/v1/jobs/{id}/events` | `test_jobs_api.py` |
| Histórico navegável por usuário | ✅ | `GET /api/v1/jobs` (owner) | `test_jobs_api.py`, `test_isolation.py` |
| Limpeza por TTL + exclusão individual | ✅ | `DELETE /api/v1/jobs...` | `test_jobs_api.py` |
| Autenticação (cookie assinado, PBKDF2) | ✅ | `app/auth.py` | `test_auth_api.py` |
| Isolamento entre usuários | ✅ | `_owned_job` (403) | `test_isolation.py` |
| Rate-limit login e criação de jobs | ✅ | `app/auth.py` | `test_auth_api.py`, `test_jobs_api.py` |
| `/health` sem expor credenciais | ✅ | `main.py` (masked_user) | `test_api.py` |
| Deploy VM (venv + NSSM + runbook) | ✅ | `scripts/setup_prod.ps1`, `install_service.ps1`, `docs/runbook-deploy.md` | manual (runbook) |

## Resumo

- **Cobertas:** todas as funcionalidades de validação, scraping, geração de
  Excel/PDF/ZIP, jobs, SSE, autenticação e isolamento.
- **Suíte:** `python -m pytest tests -q` (venv na raiz).
- **Pendência conhecida:** validação manual do fluxo completo com o portal
  real (captcha/Chrome) — não coberto por testes automatizados (mocks).
