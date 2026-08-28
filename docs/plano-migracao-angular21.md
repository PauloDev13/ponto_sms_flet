# Plano de Migração: Frontend Vanilla JS → Angular 21 + Tailwind CSS 4

**Data:** 27/08/2026
**Versão:** 1.0
**Status:** Proposta / Análise de Viabilidade

---

## Sumário

1. [Parecer de Viabilidade Técnica](#1-parecer-de-viabilidade-técnica)
2. [Mapeamento do Frontend Atual](#2-mapeamento-do-frontend-atual)
3. [Mapeamento de Requisitos para o Nginx e Integração](#3-mapeamento-de-requisitos-para-o-nginx-e-integração)
4. [Plano de Execução Passo a Passo](#4-plano-de-execução-passo-a-passo)
5. [Matriz de Mapeamento: JS Atual → Angular 21](#5-matrizes-de-mapeamento)
6. [Riscos e Mitigações](#6-riscos-e-mitigações)

---

## 1. Parecer de Viabilidade Técnica

### 1.1 Veredicto: VIÁVEL COM RESSALVAS

A migração é **tecnicamente viável**. O frontend atual é um único arquivo
`frontend/index.html` (831 linhas) com CSS embutido e JavaScript vanilla,
sem framework, sem build e sem dependências de terceiros. A interface se
comunica com o backend FastAPI via API REST/JSON com endpoints padronizados.

### 1.2 Principais Pontos de Atrito

| # | Ponto de Atrito | Severidade | Mitigação |
|---|-----------------|------------|-----------|
| 1 | **CORS** — o frontend e backend passam a rodar em origens diferentes (Nginx Ubuntu vs Python Windows) | **Alta** | Habilitar CORS no FastAPI (middleware `CORSMiddleware`) OU usar proxy reverso no Nginx para que todas as chamadas `/api/*` pareçam ser da mesma origem |
| 2 | **Cookie SameSite/Secure** — o cookie `ponto_session` é HttpOnly + SameSite=Lax; entre domínios/IPs diferentes na intranet, o navegador pode descartar o cookie | **Alta** | Usar proxy reverso no Nginx (recomendado) para manter same-origin, OU configurar o cookie com `SameSite=None; Secure` (requer HTTPS) |
| 3 | **SSE (Server-Sent Events)** — o endpoint `/api/v1/jobs/{id}/events` usa `text/event-stream`; proxies podem buffering | **Média** | Configurar Nginx com `X-Accel-Buffering: no` e `proxy_buffering off` para a rota SSE; o backend já envia `X-Accel-Buffering: no` |
| 4 | **Endpoints relativos** — todas as chamadas JS usam paths relativos (`/api/v1/...`) | **Baixa** | Configurar `proxy_pass` no Nginx mapeando `/api/` → backend; no Angular, usar environment API base URL |
| 5 | **Validação client-side** — funções JS puras (CPF, datas MM/YYYY) precisam ser reescritas em TypeScript | **Baixa** | Reimplementar com Angular Reactive Forms + validators síncronos; lógica é direta e bem documentada no código atual |
| 6 | **Autocomplete de unidades** — debounce + dropdown manual via DOM | **Baixa** | Implementar com `effect()` ou `computed()` do Signal Store + componente Angular com `input` signal |
| 7 | **Sessão do portal (Selenium)** — irrelevante para a migração (permanece no backend Python) | **N/A** | Não sofre alteração |
| 8 | **Compatibilidade visual** — CSS dark theme com variáveis customizadas | **Baixa** | Migrar para Tailwind CSS 4 com tema dark customizado (`@theme` directive) |

### 1.3 Arquitetura Atual vs Alvo

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│       CENÁRIO 1 (ATUAL)         │     │      CENÁRIO 2 (ALVO)            │
│                                 │     │                                  │
│  VM Windows (única)             │     │  VM Ubuntu (Docker/Nginx)        │
│  ┌───────────────────────────┐  │     │  ┌────────────────────────────┐  │
│  │ FastAPI (uvicorn :8000)   │  │     │  │ Nginx (:80)                │  │
│  │  ├── GET / (index.html)   │──│────▶│  │  ├── / → Angular SPA       │  │
│  │  ├── /api/v1/*            │  │     │  │  └── /api/* → proxy_pass   │  │
│  │  └── Selenium/Chrome      │  │     │  └────────────────────────────┘  │
│  └───────────────────────────┘  │     │                                  │
│                                 │     │  VM Windows (Python)             │
│                                 │     │  ┌────────────────────────────┐  │
│                                 │     │  │ FastAPI (uvicorn :8000)    │  │
│                                 │     │  │  └── /api/v1/*             │  │
│                                 │     │  └────────────────────────────┘  │
└─────────────────────────────────┘     └──────────────────────────────────┘
```

---

## 2. Mapeamento do Frontend Atual

### 2.1 Estrutura do Arquivo Único

O `frontend/index.html` contém **três camadas embutidas**:

| Camada | Linhas | Conteúdo |
|--------|--------|----------|
| `<style>` | 7-133 | CSS dark theme (127 linhas) com variáveis CSS (`--bg`, `--card`, `--border`, etc.) |
| `<body>` HTML | 135-261 | Markup: login card, formulário, progresso, histórico, modal de confirmação |
| `<script>` | 262-829 | JavaScript vanilla (567 linhas): estado global, handlers, API, DOM manipulation |

### 2.2 Componentes Visuais Identificados

| # | Componente | Descrição no HTML | Cards/IDs |
|---|------------|-------------------|-----------|
| 1 | **Login Card** | Formulário de autenticação (usuário + senha + toggle visibilidade) | `#loginCard`, `#formLogin` |
| 2 | **User Bar** | Barra superior com nome do usuário + botão "Sair" | `#currentUser`, `#btnLogout` |
| 3 | **Formulário de Consulta** | Campos: CPF (máscara), Unidade (autocomplete), Data Início/Fim (MM/YYYY), Checkboxes Excel/PDF | `#formConsulta`, `#cpf`, `#unit`, `#date_start`, `#date_end`, `#excel`, `#pdf` |
| 4 | **Card de Progresso** | Barra de progresso, status, percentual, mensagem, logs | `#progressCard`, `#progressBar`, `#progressStatus` |
| 5 | **Card de Resultado** | Lista de arquivos gerados + botões de download | `#resultCard`, `#filesList`, `#filesActions` |
| 6 | **Card de Histórico** | Lista de gerações anteriores com status badges e ações | `#historyCard`, `#historyList` |
| 7 | **Modal de Confirmação** | Overlay modal genérico (exclusão, limpar histórico) | `#confirmModal` |
| 8 | **Toast** | Notificações temporárias (sucesso/erro) | `#toast`, `#loginToast` |
| 9 | **Autocomplete Dropdown** | Lista suspensa para busca de unidades | `#unitList` |

### 2.3 Mapeamento Completo de Endpoints da API

#### Autenticação

| Método | Endpoint | Request Body | Response | Cookie |
|--------|----------|--------------|----------|--------|
| `POST` | `/api/v1/auth/login` | `{ username, password }` | `{ ok: true, user: "..." }` | `ponto_session` (HttpOnly, SameSite=Lax) |
| `POST` | `/api/v1/auth/logout` | — | `{ ok: true }` | Remove cookie |
| `GET` | `/api/v1/auth/me` | — | `{ ok: true, user: "...", jobs_active: N }` | — |

#### Validação e Dados

| Método | Endpoint | Request Body/Query | Response |
|--------|----------|--------------------|----------|
| `POST` | `/api/v1/validate` | `{ cpf, unit, date_start, date_end, excel, pdf }` | `{ valid: bool, errors: { field: msg }, fields: {...} }` |
| `GET` | `/api/v1/unidades?q=...&limit=50` | Query params | `{ ok: true, count: N, results: [{ code, description }] }` |

#### Jobs (Assíncronos)

| Método | Endpoint | Request Body/Query | Response |
|--------|----------|--------------------|----------|
| `POST` | `/api/v1/jobs` | `{ cpf, unit, date_start, date_end, excel, pdf }` | `{ ok: true, job: {...} }` (202) |
| `GET` | `/api/v1/jobs?limit=20` | Query param | `{ ok: true, count: N, jobs: [...] }` |
| `GET` | `/api/v1/jobs/{id}` | — | `{ ok: true, job: {...} }` |
| `DELETE` | `/api/v1/jobs/{id}` | — | `{ ok: true, removed: 1 }` |
| `DELETE` | `/api/v1/jobs` | — | `{ ok: true, removed: N }` |
| `POST` | `/api/v1/jobs/{id}/cancel` | — | `{ ok: true, status: "CANCELLED" }` |
| `GET` | `/api/v1/jobs/{id}/events` | — | SSE stream (`text/event-stream`) |
| `GET` | `/api/v1/jobs/{id}/download?format=...` | Query params | Binary (file/ZIP) |
| `GET` | `/api/v1/jobs/{id}/files/{filename}` | — | Binary (file) |

#### Healthcheck

| Método | Endpoint | Response |
|--------|----------|----------|
| `GET` | `/health` | `{ status: "ok", app: "...", env_ok: bool, ... }` |

### 2.4 Estado da Aplicação (Global JS)

```javascript
// Estado global atual (frontend vanilla JS)
const state = {
  job: null,      // Job ativo (objeto completo do backend)
  es: null,       // EventSource para SSE
  pollTimer: null // Timer de fallback polling
};
```

**Variáveis de UI derivadas do estado:**
- `loginCard` visível vs `appView` visível (toggle por `display`)
- `progressCard` visível (quando job ativo)
- `resultCard` visível (quando job DONE com arquivos)
- `historyCard` visível (sempre que há histórico)
- `toast` visível (temporização com `setTimeout`)
- `confirmModal` visível (Promise-based: `askConfirm()` retorna Promise)
- Botão "GERAR" label dinâmico (depende dos checkboxes Excel/PDF)
- Botão "GERAR" estado disabled/spinner (depende do fluxo: VALIDANDO → ENFILEIRANDO → GERANDO)

### 2.5 Padrões de Comunicação

| Padrão | Implementação Atual | Notas |
|--------|---------------------|-------|
| **HTTP** | `fetch()` com `credentials: 'same-origin'` (implícito) | Todas as chamadas usam `fetch()` |
| **SSE** | `new EventSource(url)` | Fallback automático para polling (2s interval) |
| **Cookies** | Enviados automaticamente (HttpOnly, SameSite=Lax) | Mesma origem = funciona sem config extra |
| **Autenticação** | Cookie `ponto_session` via login | `GET /api/v1/auth/me` verifica sessão |
| **Erros** | JSON `{ ok: false, message: "..." }` | Padronizado em todos os endpoints |
| **Validação** | Client-side (JS puro) + Server-side (`POST /api/v1/validate`) | Dupla validação |

---

## 3. Mapeamento de Requisitos para o Nginx e Integração

### 3.1 Configuração do Nginx (Proxy Reverso)

A configuração do Nginx deve fazer **dois mapeamentos**:

1. **Rotas estáticas** (`/`) → servir os arquivos da SPA Angular (build)
2. **Rotas de API** (`/api/*`, `/health`) → proxy reverso para o backend Python na VM Windows

```nginx
# /etc/nginx/conf.d/ponto-sms.conf (ou dentro do server block existente)

# Upstream do backend Python na VM Windows
upstream ponto_backend {
    server 192.168.X.X:8000;  # IP da VM Windows com o FastAPI
    keepalive 32;
}

server {
    listen 80;
    server_name ponto.sms.local;  # ou IP direto

    # Angular SPA (build production)
    root /usr/share/nginx/html/ponto-sms;
    index index.html;

    # ── API: proxy reverso para o backend Python ──

    location /api/ {
        proxy_pass http://ponto_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Para SSE (EventSource): desabilitar buffering
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;  # SSE pode ficar aberto longamente
        chunked_transfer_encoding off;

        # Manter cookies (SameOrigin via proxy)
        proxy_cookie_flags ~ SameSite=Lax;
    }

    location /health {
        proxy_pass http://ponto_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # ── Angular SPA: fallback para index.html ──
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache de assets estáticos (JS/CSS/hash do Angular)
    location ~* \.(?:js|css|woff2?|ttf|eot|ico|svg|png|jpg|jpeg|gif)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Headers de segurança
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
}
```

### 3.2 Habilitar CORS no Backend Python (Alternativa ao Proxy)

Se optar por chamar o backend diretamente (sem proxy), habilitar CORS no FastAPI:

```python
# Adicionar em backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.X.X",      # IP do Nginx/Ubuntu
        "http://ponto.sms.local",  # Nome do host
    ],
    allow_credentials=True,  # NECESSÁRIO para cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Recomendação:** usar proxy reverso (Nginx) em vez de CORS. O proxy evita
> problemas com cookies cross-origin e mantém a arquitetura mais simples.

### 3.3 Configuração do Cookie no Backend

O cookie `ponto_session` já é configurado com `SameSite=Lax` e `path='/'`.
Quando o Nginx proxy faz reverse proxy, as requisições chegam ao backend
como same-origin, então **nenhuma alteração no cookie é necessária** se
usar proxy reverso.

Se optar por CORS (sem proxy):
- Alterar `SameSite` para `None` (requer `Secure=true`, ou seja, HTTPS)
- OU usar HTTPS no Nginx (recomendado em produção)
- Configurar `SESSION_COOKIE_SECURE=true` no `.env` do backend

### 3.4 Variáveis de Ambiente do Frontend Angular

Criar `src/environments/environment.ts` e `environment.prod.ts`:

```typescript
// environment.ts (dev)
export const environment = {
  production: false,
  apiBaseUrl: 'http://192.168.X.X:8000',  // Direto ao backend (dev)
};

// environment.prod.ts
export const environment = {
  production: true,
  apiBaseUrl: '',  // Vazio = relativo (passa pelo proxy Nginx)
};
```

### 3.5 Construção e Deploy do Angular

| Item | Configuração |
|------|-------------|
| **Output** | `ng build --configuration=production` → `dist/ponto-sms/browser/` |
| **Deploy Nginx** | Copiar contents de `dist/` para `/usr/share/nginx/html/ponto-sms/` |
| **Dockerfile** | Multi-stage: build Angular + Nginx (já existe ecossistema Docker no target) |
| **CI/CD** | Build automático → push Docker image → rolling update |

---

## 4. Plano de Execução Passo a Passo

### Fase 1: Mapeamento e Extração

**Objetivo:** Extrair toda a lógica de negócio do JS vanilla e criar os tipos TypeScript.

**1.1 - Definir Interfaces TypeScript dos payloads da API**

```typescript
// src/app/core/models/api.models.ts

// ── Auth ──
export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  ok: boolean;
  user?: string;
  message?: string;
  jobs_active?: number;
}

// ── Validate ──
export interface ValidateRequest {
  cpf: string;
  unit: string;
  date_start: string;
  date_end: string;
  excel: boolean;
  pdf: boolean;
}

export interface ValidateResponse {
  valid: boolean;
  errors: Record<string, string>;
  fields: Record<string, string | boolean>;
}

// ── Jobs ──
export type JobStatus = 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED' | 'CANCELLED';

export interface JobFile {
  name: string;
  format: 'xlsx' | 'pdf';
}

export interface JobProgress {
  months_ok: number;
  months_total: number;
  percent: number;
  message: string;
}

export interface Job {
  id: string;
  owner: string;
  status: JobStatus;
  created_at: string;
  started_at?: string;
  done_at?: string;
  progress: JobProgress;
  files: JobFile[];
  logs: string[];
  error: string;
  payload?: Record<string, unknown>;
}

export interface JobResponse {
  ok: boolean;
  job: Job;
  message?: string;
  errors?: Record<string, string>;
}

export interface JobListResponse {
  ok: boolean;
  count: number;
  jobs: Job[];
}

// ── Unidades ──
export interface Unidade {
  code: string;
  description: string;
}

export interface UnidadesResponse {
  ok: boolean;
  count: number;
  results: Unidade[];
}

// ── SSE ──
export interface SSEMessage {
  type: 'update' | 'error';
  job?: Job;
  message?: string;
}
```

**1.2 - Extrair e documentar todas as rotas da API**

Compilar a tabela completa de endpoints (já feita na Seção 2.3) como
referência para o `ApiService`.

**1.3 - Mapear a lógica de validação client-side**

Extrair do JS atual as funções puras:
- `maskCpf(v)` → formatador CPF
- `maskMonthYear(v)` → formatador MM/YYYY
- `checkCpfDigits(d)` → validador de dígitos verificadores
- `parseMonthYear(v)` → parser MM/YYYY
- `clientValidate(p)` → validador completo do formulário

---

### Fase 2: Arquitetura do Componente em Angular 21

**Objetivo:** Decompor o monolito HTML/JS em componentes Angular com arquitetura reativa.

**2.1 - Estrutura de Módulos e Componentes**

```
src/app/
├── core/
│   ├── models/
│   │   └── api.models.ts              # Interfaces TypeScript
│   ├── services/
│   │   ├── auth.service.ts            # Autenticação (login/logout/me)
│   │   ├── api.service.ts             # HTTP client genérico
│   │   ├── job.service.ts             # CRUD de jobs + SSE
│   │   ├── unidades.service.ts        # Autocomplete de unidades
│   │   └── validation.service.ts      # Validação client-side
│   └── interceptors/
│       └── error.interceptor.ts       # Interceptor de erros HTTP
├── features/
│   └── ponto/
│       ├── ponto.routes.ts            # Rotas do módulo
│       ├── ponto.component.ts         # Page wrapper (layout)
│       ├── ponto.component.html
│       ├── components/
│       │   ├── login-card/            # Tela de login
│       │   │   ├── login-card.component.ts
│       │   │   ├── login-card.component.html
│       │   │   └── login-card.component.ts  (signals)
│       │   ├── user-bar/              # Barra do usuário logado
│       │   ├── query-form/            # Formulário de consulta
│       │   │   ├── query-form.component.ts
│       │   │   └── cpf-input/         # Sub-componente: input com máscara
│       │   ├── progress-card/         # Card de progresso (SSE)
│       │   ├── result-card/           # Lista de arquivos gerados
│       │   ├── history-card/          # Histórico de gerações
│       │   ├── confirm-modal/         # Modal de confirmação genérico
│       │   ├── toast/                 # Notificações
│       │   └── autocomplete/          # Dropdown de autocomplete
│       └── store/
│           └── ponto.store.ts         # Signal Store do módulo
├── shared/
│   ├── pipes/
│   │   ├── cpf-mask.pipe.ts           # Pipe de máscara CPF
│   │   └── date-br.pipe.ts            # Pipe de formatação BR
│   └── directives/
│       └── auto-focus.directive.ts
└── app.component.ts
```

**2.2 - Signal Store (NgRx SignalStore)**

O estado global do JS vanilla (`state.job`, `state.es`, `state.pollTimer`)
será substituído por um Signal Store reativo:

```typescript
// src/app/features/ponto/store/ponto.store.ts
import { signalStore, withState, withMethods, patchState } from '@ngrx/signals';
import { Job, JobStatus } from '../../../core/models/api.models';

interface PontoState {
  // Auth
  isAuthenticated: boolean;
  currentUser: string | null;

  // Job ativo
  activeJob: Job | null;
  isTracking: boolean;

  // UI
  showLogin: boolean;
  showProgress: boolean;
  showResults: boolean;
  showHistory: boolean;

  // Histórico
  historyJobs: Job[];

  // Toast
  toastMessage: string;
  toastType: 'success' | 'error';
  toastVisible: boolean;
}

export const PontoStore = signalStore(
  { providedIn: 'root' },
  withState<PontoState>({
    isAuthenticated: false,
    currentUser: null,
    activeJob: null,
    isTracking: false,
    showLogin: true,
    showProgress: false,
    showResults: false,
    showHistory: false,
    historyJobs: [],
    toastMessage: '',
    toastType: 'success',
    toastVisible: false,
  }),
  withMethods((store) => ({
    // Auth
    loginSuccess(user: string) {
      patchState(store, {
        isAuthenticated: true,
        currentUser: user,
        showLogin: false,
      });
    },
    logout() {
      patchState(store, {
        isAuthenticated: false,
        currentUser: null,
        activeJob: null,
        isTracking: false,
        showLogin: true,
        showProgress: false,
        showResults: false,
      });
    },
    // Job
    setActiveJob(job: Job) {
      patchState(store, {
        activeJob: job,
        isTracking: true,
        showProgress: true,
        showResults: false,
      });
    },
    updateJobProgress(job: Job) {
      patchState(store, { activeJob: job });
    },
    jobCompleted(job: Job) {
      patchState(store, {
        activeJob: job,
        isTracking: false,
        showResults: true,
      });
    },
    jobFailed(job: Job) {
      patchState(store, {
        activeJob: null,
        isTracking: false,
      });
    },
    // Toast
    showToast(message: string, type: 'success' | 'error' = 'error') {
      patchState(store, { toastMessage: message, toastType: type, toastVisible: true });
    },
    hideToast() {
      patchState(store, { toastVisible: false });
    },
    // History
    setHistory(jobs: Job[]) {
      patchState(store, { historyJobs: jobs, showHistory: true });
    },
  }))
);
```

**2.3 - Substituição Imperativo → Reativo**

| Funcionalidade JS Atual | Angular 21 Reativo |
|--------------------------|---------------------|
| `$('loginCard').style.display = 'none'` | `@if (!store.showLogin())` no template |
| `$('btnGenerate').disabled = on` | `[disabled]="store.isTracking()"` |
| `$('progressBar').style.width = percent + '%'` | `[style.width.%]="store.activeJob()?.progress?.percent ?? 0"` |
| `$('toast').textContent = message` | `<app-toast [message]="store.toastMessage()" [type]="store.toastType()" />` |
| `$('unitList').innerHTML = ''` + loop | `@for (item of unidades(); track item.code)` |
| `es.onmessage = (evt) => {...}` | `effect()` ou subscription no service |
| `setInterval(polling)` | `interval(2000).pipe(switchMap(...))` ou `afterNextRender` + signal |

**2.4 - Serviços de Comunicação**

```typescript
// src/app/core/services/job.service.ts (esqueleto)
@Injectable({ providedIn: 'root' })
export class JobService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiBaseUrl;

  createJob(payload: ValidateRequest): Observable<JobResponse> {
    return this.http.post<JobResponse>(`${this.baseUrl}/api/v1/jobs`, payload);
  }

  getJob(id: string): Observable<JobResponse> {
    return this.http.get<JobResponse>(`${this.baseUrl}/api/v1/jobs/${id}`);
  }

  cancelJob(id: string): Observable<{ ok: boolean; status: string }> {
    return this.http.post<{ ok: boolean; status: string }>(
      `${this.baseUrl}/api/v1/jobs/${id}/cancel`, {}
    );
  }

  deleteJob(id: string): Observable<{ ok: boolean; removed: number }> {
    return this.http.delete<{ ok: boolean; removed: number }>(
      `${this.baseUrl}/api/v1/jobs/${id}`
    );
  }

  listJobs(limit = 20): Observable<JobListResponse> {
    return this.http.get<JobListResponse>(`${this.baseUrl}/api/v1/jobs`, {
      params: { limit: limit.toString() },
    });
  }

  // SSE com fallback para polling
  trackJob(id: string): Observable<SSEMessage> {
    return new Observable<SSEMessage>((subscriber) => {
      const es = new EventSource(`${this.baseUrl || ''}/api/v1/jobs/${id}/events`);
      es.onmessage = (evt) => {
        subscriber.next(JSON.parse(evt.data));
      };
      es.onerror = () => {
        es.close();
        // Fallback: polling a cada 2s
        const timer = setInterval(async () => {
          try {
            const res = await fetch(`${this.baseUrl}/api/v1/jobs/${id}`);
            const data = await res.json();
            if (data.ok) {
              subscriber.next({ type: 'update', job: data.job });
              if (['DONE', 'FAILED', 'CANCELLED'].includes(data.job.status)) {
                subscriber.complete();
                clearInterval(timer);
              }
            }
          } catch { /* mantém polling */ }
        }, 2000);
        return () => clearInterval(timer);
      };
      return () => es.close();
    });
  }

  downloadFile(jobId: string, filename: string): string {
    return `${this.baseUrl}/api/v1/jobs/${jobId}/files/${encodeURIComponent(filename)}`;
  }

  downloadZip(jobId: string, format = 'zip', parts = ''): string {
    const params = parts ? `${format}&parts=${parts}` : format;
    return `${this.baseUrl}/api/v1/jobs/${jobId}/download?format=${params}`;
  }
}
```

**2.5 - Pipes e Diretivas Reutilizáveis**

```typescript
// Máscara CPF (replaces maskCpf JS function)
@Pipe({ name: 'cpfMask', standalone: true })
export class CpfMaskPipe implements PipeTransform {
  transform(value: string): string {
    const d = value.replace(/\D/g, '').slice(0, 11);
    if (d.length > 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
    if (d.length > 6) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`;
    if (d.length > 3) return `${d.slice(0,3)}.${d.slice(3)}`;
    return d;
  }
}
```

---

### Fase 3: Estilização e UI (Tailwind CSS 4)

**Objetivo:** Migrar o dark theme CSS para Tailwind CSS 4 sem perda visual.

**3.1 - Configuração do Tema Dark Customizado**

```css
/* src/styles.css (Tailwind CSS 4) */
@import "tailwindcss";

@theme {
  --color-bg: #1e1f22;
  --color-card: #21252b;
  --color-border: #5a90fc;
  --color-fg: #abb2bf;
  --color-accent: #4dd0e1;
  --color-ok: #43a047;
  --color-ko: #e53935;
  --color-warn: #ff8f00;
  --color-input-bg: #2b2d30;
  --color-input-border: #3a3d42;
  --color-dropdown-bg: #2b2d30;
  --color-dropdown-hover: #30343a;
  --color-modal-bg: #1b1d20;
}

body {
  @apply bg-bg text-fg font-sans m-0 p-6 min-h-screen;
}
```

**3.2 - Mapeamento de Classes CSS → Tailwind**

| CSS Atual | Tailwind Equivalente |
|-----------|---------------------|
| `.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 24px; }` | `class="bg-card border border-border rounded-xl p-6"` |
| `.btn { padding: 12px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }` | `class="px-5 py-3 rounded-md cursor-pointer font-semibold"` |
| `.btn-primary { background: var(--border); color: #000; }` | `class="bg-border text-black hover:bg-[#6aafff]"` |
| `.btn-secondary { background: #2b2d30; color: var(--fg); }` | `class="bg-input-bg text-fg hover:bg-input-border"` |
| `.btn-danger { background: #b71c1c; color: #fff; }` | `class="bg-[#b71c1c] text-white hover:bg-[#d32f2f]"` |
| `.status-badge.done { background: #1b5e20; color: #a5d6a7; }` | `class="bg-[#1b5e20] text-[#a5d6a7]"` ou `bg-green-900 text-green-300` |
| `.progress-bar { background: linear-gradient(90deg, #4dd0e1, #5a90fc); }` | `class="bg-gradient-to-r from-accent to-border"` |
| `.field { flex: 1; min-width: 150px; margin-bottom: 12px; }` | `class="flex-1 min-w-[150px] mb-3"` |
| `.row { display: flex; gap: 12px; flex-wrap: wrap; }` | `class="flex gap-3 flex-wrap"` |
| `.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; }` | `class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"` |
| `.layout { display: flex; gap: 20px; max-width: 1440px; margin: 0 auto; }` | `class="flex gap-5 max-w-[1440px] mx-auto items-start"` |
| `.main-col { flex: 1; min-width: 0; }` | `class="flex-1 min-w-0"` |
| `.side-col { width: 720px; flex-shrink: 0; }` | `class="w-[720px] shrink-0"` |
| `input:focus { outline: none; border-color: var(--border); }` | `focus:outline-none focus:border-border` |
| `input.invalid { border-color: var(--ko); }` | `border-ko` (condicional via `[class.border-ko]="hasError"`) |
| `@media (max-width: 1100px) { .layout { flex-direction: column; } }` | `flex flex-col max-md:` (responsive utilities) |

**3.3 - Estrutura do Componente de Exemplo (Login)**

```html
<!-- login-card.component.html -->
<div class="bg-card border border-border rounded-xl p-6 max-w-[420px] mx-auto my-20"
     [style.display]="store.showLogin() ? 'block' : 'none'">

  <h2 class="text-center text-white text-xl font-medium mb-4">
    Consulta Ponto Eletrônico
  </h2>

  <form (ngSubmit)="onSubmit()">
    <div class="mb-3">
      <label class="block text-sm text-[#8f97a3] mb-1">Usuário</label>
      <input type="text" autocomplete="username" spellcheck="false"
             class="w-full px-3 py-2.5 rounded-md bg-input-bg border border-input-border
                    text-[#e6e6e6] text-base focus:outline-none focus:border-border"
             [formControl]="usernameControl" />
    </div>

    <div class="mb-3">
      <label class="block text-sm text-[#8f97a3] mb-1">Senha</label>
      <div class="relative">
        <input [type]="showPassword() ? 'text' : 'password'"
               autocomplete="current-password"
               class="w-full px-3 py-2.5 pr-10 rounded-md bg-input-bg border
                      border-input-border text-[#e6e6e6] text-base
                      focus:outline-none focus:border-border"
               [formControl]="passwordControl" />
        <button type="button"
                class="absolute right-1.5 top-1/2 -translate-y-1/2 bg-transparent
                       border-none text-[#8f97a3] hover:text-fg p-1 cursor-pointer"
                (click)="togglePasswordVisibility()">
          {{ showPassword() ? '&#128064;' : '&#128065;' }}
        </button>
      </div>
    </div>

    <div class="flex gap-3 mt-1">
      <button type="submit" class="flex-1 px-5 py-3 rounded-md font-semibold
              bg-border text-black hover:bg-[#6aafff] disabled:opacity-55
              disabled:cursor-not-allowed"
              [disabled]="loginDisabled()">
        ENTRAR
      </button>
    </div>

    @if (errorMessage()) {
      <div class="mt-3 px-3 py-2.5 rounded-md border border-ko bg-input-bg
                  text-[#ef9a9a] text-sm">
        {{ errorMessage() }}
      </div>
    }
  </form>
</div>
```

---

### Fase 4: Testes de Comunicação e Validação

**Objetivo:** Garantir que a integração Angular ↔ Nginx ↔ Python Backend funciona em produção.

**4.1 - Testes Unitários (Angular)**

| Teste | O que valida |
|-------|-------------|
| `CpfMaskPipe` | Formatação CPF em todos os estágios |
| `ValidationService` | Validação CPF (dígitos verificadores), datas MM/YYYY, intervalo |
| `Auth.service` | Login/logout/me com mock HTTP |
| `Job.service` | CRUD de jobs com mock HTTP |
| `PontoStore` | Transições de estado reativas |

**4.2 - Testes de Integração (E2E)**

| Cenário | Passos |
|---------|--------|
| Login/logout | Abrir app → login com credenciais válidas → verificar `showApp` → logout → verificar `showLogin` |
| Sessão expirada | Abrir app sem cookie → deve mostrar login → login → fechar browser → abrir novamente → verificar `/api/v1/auth/me` retorna 401 |
| Criar job | Preencher formulário → submeter → verificar progresso SSE → verificar arquivos gerados → download |
| Cancelar job | Iniciar job longo → cancelar → verificar status CANCELLED |
| Histórico | Criar vários jobs → verificar lista no card → excluir → limpar histórico |
| Autocomplete | Digitar 2+ caracteres na unidade → verificar dropdown → selecionar |
| Validación server-side | Submeter CPF inválido → verificar erro do backend retornado |

**4.3 - Testes de Infraestrutura (Nginx ↔ Backend)**

| Teste | Comando/Método |
|-------|---------------|
| Proxy reverso funciona | `curl http://ponto.local/api/v1/auth/me` → deve retornar JSON (não 502) |
| SSE funciona | `curl -H "Accept: text/event-stream" http://ponto.local/api/v1/jobs/{id}/events` → stream |
| Cookie é repassado | Login via Angular → inspecionar cookie `ponto_session` no DevTools → verificar que todas as chamadas subsequentes o enviam |
| CORS (se aplicável) | Verificar header `Access-Control-Allow-Origin` e `Access-Control-Allow-Credentials` |
| SPA fallback | `curl http://ponto.local/qualquer/rota` → deve retornar `index.html` do Angular |

**4.4 - Validação Visual**

Comparar screenshot side-by-side:
- App atual (index.html original) vs App Angular (Tailwind)
- Verificar: cores, tamanhos, espaçamentos, responsividade, dark theme
- Testar em: Chrome, Firefox, Edge (desktop + mobile view)

---

## 5. Matrizes de Mapeamento

### 5.1 Mapeamento: HTML Atual → Componentes Angular

| Seção HTML Atual | Componente Angular | Sinal/Signal |
|-------------------|-------------------|--------------|
| `#loginCard` (linhas 138-157) | `LoginCardComponent` | `store.showLogin()` → `@if` |
| `#formLogin` (linhas 140-156) | `LoginCardComponent` | `FormGroup` + `FormControl` |
| User bar (linhas 162-165) | `UserBarComponent` | `store.currentUser()` |
| `#formConsulta` (linhas 173-211) | `QueryFormComponent` | `FormGroup` reativo |
| `#cpf` (máscara + validação) | `QueryFormComponent` | `cpfMask` pipe + signal `cpfValue` |
| `#unit` + `#unitList` (autocomplete) | `AutocompleteComponent` | signal `query` + signal `results[]` |
| `#date_start`, `#date_end` | `QueryFormComponent` | `monthYearMask` pipe + `FormControl` |
| `#excel`, `#pdf` checkboxes | `QueryFormComponent` | `FormControl` boolean |
| `#btnGenerate` label dinâmico | `QueryFormComponent` | `computed(() => ...)` baseado nos checkboxes |
| `#progressCard` (linhas 215-224) | `ProgressCardComponent` | `store.activeJob()` → progress/status/message |
| `#resultCard` (linhas 227-231) | `ResultCardComponent` | `store.activeJob()?.files` → `@for` |
| `#historyCard` (linhas 237-243) | `HistoryCardComponent` | `store.historyJobs()` → `@for` |
| `#confirmModal` (linhas 251-260) | `ConfirmModalComponent` | signal `isOpen` + signal `resolve` |
| Toast notifications | `ToastComponent` | `store.toastVisible()` → `@if` |
| Spinner no botão | `QueryFormComponent` | `store.isTracking()` → `@if` com `[class]` |

### 5.2 Mapeamento: JavaScript Funções → Angular Services

| Função JS | Serviço Angular | Método |
|-----------|-----------------|--------|
| `checkAuth()` | `AuthService` | `checkSession()` |
| `doLogout()` | `AuthService` | `logout()` |
| `showApp(user)` | `PontoStore` | `loginSuccess(user)` |
| `showLogin(msg)` | `PontoStore` | `logout()` |
| `showToast(msg, type)` | `PontoStore` | `showToast(msg, type)` |
| `setFieldError(field, msg)` | `ValidationService` | `setFieldError(form, field, msg)` |
| `clearErrors()` | `ValidationService` | `clearErrors(form)` |
| `clientValidate(payload)` | `ValidationService` | `validate(payload)` |
| `maskCpf(v)` | `CpfMaskPipe` | `transform(v)` |
| `maskMonthYear(v)` | `MonthYearMaskPipe` | `transform(v)` |
| `updateButtonLabel()` | `QueryFormComponent` | `computed(() => ...)` |
| `setGenerating(on, label)` | `PontoStore` | `setTracking(on)` |
| `renderProgress(job)` | `ProgressCardComponent` |绑定 `store.activeJob()` |
| `renderFiles(files)` | `ResultCardComponent` |绑定 `store.activeJob()?.files` |
| `startJob(job)` | `JobService` | `trackJob(id)` + `PontoStore.setActiveJob()` |
| `startPolling(id)` | `JobService` | `trackJob(id)` (SSE com fallback polling) |
| `stopTracking()` | `JobService` | unsubscribe do Observable |
| `onDone(job)` | `PontoStore` | `jobCompleted(job)` |
| `onFailed(job)` | `PontoStore` | `jobFailed(job)` |
| `loadHistory()` | `JobService` | `listJobs()` → `PontoStore.setHistory()` |
| `deleteJob(id)` | `JobService` | `deleteJob(id)` |
| `clearHistory()` | `JobService` | `clearJobs()` |
| `cancelJob(id)` | `JobService` | `cancelJob(id)` |
| `askConfirm(msg)` | `ConfirmModalComponent` | signal `isOpen` + Promise/Signal |
| autocomplete debounce | `AutocompleteComponent` | `toSignal` + `debounceTime(250)` |

### 5.3 Mapeamento: CSS → Tailwind CSS 4

| Classe CSS | Tailwind CSS 4 |
|------------|----------------|
| `var(--bg)` → `#1e1f22` | `bg-bg` (theme custom) |
| `var(--card)` → `#21252b` | `bg-card` |
| `var(--border)` → `#5a90fc` | `border-border` |
| `var(--fg)` → `#abb2bf` | `text-fg` |
| `var(--accent)` → `#4dd0e1` | `text-accent` |
| `var(--ok)` → `#43a047` | `text-ok` / `bg-ok` |
| `var(--ko)` → `#e53935` | `text-ko` / `bg-ko` |
| `var(--warn)` → `#ff8f00` | `text-warn` |
| `border-radius: 10px` | `rounded-xl` |
| `border-radius: 6px` | `rounded-md` |
| `border-radius: 999px` | `rounded-full` |
| `font-size: 14px` | `text-sm` |
| `font-size: 16px` | `text-base` |
| `font-size: 20px` | `text-xl` |
| `font-weight: 500` | `font-medium` |
| `font-weight: 600` | `font-semibold` |
| `font-weight: 700` | `font-bold` |
| `opacity: .55` | `opacity-55` |
| `transition: width .4s ease` | `transition-all duration-400 ease-in-out` |
| `animation: spin .8s linear infinite` | `animate-spin` |
| `min-height: 100vh` | `min-h-screen` |
| `overflow-y: auto` | `overflow-y-auto` |
| `text-align: center` | `text-center` |
| `white-space: nowrap` | `whitespace-nowrap` |
| `word-break: break-all` | `break-all` |
| `position: absolute; z-index: 10` | `absolute z-10` |
| `position: fixed; inset: 0; z-index: 100` | `fixed inset-0 z-50` |
| `box-shadow: 0 8px 30px rgba(0,0,0,.5)` | `shadow-2xl` |
| Scrollbar customizada | Plugin Tailwind ou CSS ad-hoc |

---

## 6. Riscos e Mitigações

| # | Risco | Impacto | Probabilidade | Mitigação |
|---|-------|---------|---------------|-----------|
| 1 | Cookie SameSite quebra entre VMs | **Alto** | Média | Usar proxy reverso Nginx (same-origin). Se CORS, usar HTTPS + `SameSite=None; Secure` |
| 2 | SSE buffering pelo Nginx | **Alto** | Média | Configurar `proxy_buffering off` + `proxy_cache off` + `chunked_transfer_encoding off` |
| 3 | Perda de fidelidade visual na migração Tailwind | **Médio** | Baixa | Teste visual side-a-side; documentar valores exatos das cores/espacamentos |
| 4 | Estado concorrente (job ativo + histórico + SSE) | **Médio** | Baixa | Signal Store centraliza tudo; testes E2E cobrem fluxos |
| 5 | Validação client-side diverge da server-side | **Baixo** | Baixa | Reutilizar a lógica do `validators.py` como referência; testes unitários |
| 6 | Performance do Angular SPA (bundle size) | **Baixo** | Baixa | Angular 21 com build otimizado; app pequena (~10 componentes) |
| 7 | Incompatibilidade de ambiente Docker/Nginx existente | **Médio** | Baixa | Testar em staging antes; o Dockerfile Angular é isolado |

---

## Anexo A: Resumo dos Endpoints (Referência Rápida)

```
AUTH
  POST /api/v1/auth/login       { username, password }     → { ok, user }
  POST /api/v1/auth/logout                                  → { ok }
  GET  /api/v1/auth/me                                      → { ok, user, jobs_active }

DATA
  POST /api/v1/validate         { cpf, unit, dates, opts } → { valid, errors }
  GET  /api/v1/unidades?q=...                              → { ok, count, results }

JOBS
  POST /api/v1/jobs             { cpf, unit, dates, opts } → { ok, job } (202)
  GET  /api/v1/jobs?limit=20                               → { ok, count, jobs }
  GET  /api/v1/jobs/{id}                                   → { ok, job }
  DELETE /api/v1/jobs/{id}                                 → { ok, removed }
  DELETE /api/v1/jobs                                      → { ok, removed }
  POST /api/v1/jobs/{id}/cancel                            → { ok, status }

REAL-TIME
  GET  /api/v1/jobs/{id}/events                            → SSE stream
  GET  /api/v1/jobs/{id}/download?format=...               → Binary
  GET  /api/v1/jobs/{id}/files/{name}                      → Binary

HEALTH
  GET  /health                                            → { status, env_ok, ... }
```

---

## Anexo B: Checklist de Migração

- [ ] Criar projeto Angular 21 com `ng new ponto-sms`
- [ ] Configurar Tailwind CSS 4 com tema dark customizado
- [ ] Criar interfaces TypeScript (`api.models.ts`)
- [ ] Implementar `AuthService` (login/logout/me)
- [ ] Implementar `ApiService` (HTTP client genérico)
- [ ] Implementar `JobService` (CRUD + SSE)
- [ ] Implementar `UnidadesService` (autocomplete)
- [ ] Implementar `ValidationService` (validação client-side)
- [ ] Criar `PontoStore` (Signal Store)
- [ ] Implementar `LoginCardComponent`
- [ ] Implementar `UserBarComponent`
- [ ] Implementar `QueryFormComponent` + sub-componentes
- [ ] Implementar `ProgressCardComponent`
- [ ] Implementar `ResultCardComponent`
- [ ] Implementar `HistoryCardComponent`
- [ ] Implementar `ConfirmModalComponent`
- [ ] Implementar `ToastComponent`
- [ ] Implementar `AutocompleteComponent`
- [ ] Configurar `HttpClient` com interceptors
- [ ] Configurar environment API base URL
- [ ] Testes unitários de todos os services/pipes
- [ ] Testes E2E (Playwright/Cypress)
- [ ] Configurar Nginx proxy reverso
- [ ] Configurar Dockerfile multi-stage
- [ ] Teste visual side-a-side com app original
- [ ] Testes de integração Nginx ↔ Backend Python
- [ ] Documentação de deploy
