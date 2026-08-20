"""API FastAPI do sistema de consulta de ponto eletrônico (FASE 0 + 3 + 4).

Endpoints atuais:
- GET  /health                            -> status da API e da configuração
- POST /api/v1/auth/login                 -> login (cookie de sessão assinado)
- POST /api/v1/auth/logout                -> encerra a sessão
- GET  /api/v1/auth/me                    -> usuário autenticado
- POST /api/v1/validate                   -> validação server-side do formulário
- GET  /api/v1/unidades?q=                -> autocomplete de unidades (CSV)
- POST /api/v1/ponto                      -> legado: fluxo síncrono (retorna ZIP)
- POST /api/v1/jobs                       -> cria job assíncrono (202)
- GET  /api/v1/jobs                       -> histórico navegável (últimos N)
- DELETE /api/v1/jobs                     -> limpa histórico (jobs terminais + pastas)
- DELETE /api/v1/jobs/{id}                -> exclui uma geração específica
- POST  /api/v1/jobs/{id}/cancel          -> cancela geração na fila/em execução
- GET  /api/v1/jobs/{id}                  -> status/progresso do job
- GET  /api/v1/jobs/{id}/events           -> SSE de progresso em tempo real
- GET  /api/v1/jobs/{id}/download         -> download (format=xlsx|pdf|zip)
- GET  /api/v1/jobs/{id}/files/{filename} -> download de arquivo individual
- GET  /                                  -> página frontend (static)

FASE 4: contas locais (WEB_USERS) + sessão por cookie assinado. Todos os
endpoints de jobs são escopados por usuário: cada usuário só enxerga,
baixa, cancela ou exclui as próprias gerações.
"""
import asyncio
import io
import json
import logging
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.app.auth import (
    SESSION_COOKIE,
    authenticate_user,
    client_ip,
    get_current_user,
    job_creation_allowed,
    login_allowed,
    make_session_token,
)
from backend.app.auth import JOB_MAX_ACTIVE
from backend.app.ponto_service import (
    PontoRequestError,
    build_zip_filename,
    normalize_cpf,
    parse_br_month,
    run_job_flow,
    run_ponto_flow,
)
from backend.app.session_manager import close_driver as _close_browser
from backend.app.session_manager import start_keepalive, stop_keepalive
from backend.core.job import Job, JobManager, JobStatus, TERMINAL_STATUSES
from backend.core.settings import REPO_ROOT, settings
from backend.core.unidades_service import search_unidades
from backend.core.validators import validate_form

logger = logging.getLogger(__name__)

FRONTEND_INDEX = REPO_ROOT / 'frontend' / 'index.html'

# Medias por formato de arquivo gerado (download)
MEDIA_TYPES = {
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pdf': 'application/pdf',
    'zip': 'application/zip',
}


class ValidateRequest(BaseModel):
    cpf: str = ''
    unit: str = ''
    date_start: str = ''
    date_end: str = ''
    excel: bool = False
    pdf: bool = False


class PontoRequest(BaseModel):
    cpf: str = ''
    unit: str = ''
    date_start: str = ''
    date_end: str = ''
    excel: bool = False
    pdf: bool = False


class LoginRequest(BaseModel):
    username: str = ''
    password: str = ''


class JobAccessError(Exception):
    """Job inexistente (404) ou de outro usuário (403)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


# ---------------------------------------------------------------------------
# Jobs: gerente global + limpeza agendada (TTL) via lifespan
# ---------------------------------------------------------------------------


def _cleanup_interval_seconds() -> float:
    """Intervalo entre varreduras de expiração (fração do TTL, clamp)."""
    ttl_seconds = max(settings.job_ttl_hours * 3600, 600)
    return min(max(ttl_seconds / 8, 300), 3600)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(_cleanup_interval_seconds())
        removed = JOB_MANAGER.cleanup_expired()
        if removed:
            logger.info('Cleanup agendado: %s job(s) expirado(s) removido(s).', removed)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    JOB_MANAGER.cleanup_expired()
    task = asyncio.create_task(_cleanup_loop())
    start_keepalive()
    yield
    task.cancel()
    stop_keepalive()
    _close_browser()  # encerramento do servidor: fecha a janela do backend


app = FastAPI(
    lifespan=lifespan,
    title='Consulta Ponto Eletrônico - API',
    version='0.1.0',
    description='Backend web do sistema de consulta de ponto eletrônico da SMS.',
)

JOB_MANAGER: JobManager = JobManager(
    run_fn=run_job_flow,
    ttl_hours=settings.job_ttl_hours,
    history_limit=settings.jobs_history_limit,
)


# ---------------------------------------------------------------------------
# FASE 0: healthcheck, validação, unidades e página frontend
# ---------------------------------------------------------------------------


@app.get('/health')
def health() -> dict[str, object]:
    """Healthcheck: status da API e presença das variáveis de ambiente."""
    return {
        'status': 'ok',
        'app': 'ponto_sms_api',
        'env_ok': settings.required_ok,
        'user_masked': settings.masked_user if settings.required_ok else None,
        'jobs_active': JOB_MANAGER.count(),
    }


# ---------------------------------------------------------------------------
# FASE 4: autenticação (contas locais + cookie de sessão assinado)
# ---------------------------------------------------------------------------


@app.post('/api/v1/auth/login')
def api_login(payload: LoginRequest, request: Request, response: Response) -> object:
    """Autentica o usuário e emite o cookie de sessão (HttpOnly)."""
    ip = client_ip(request)
    if not login_allowed(ip):
        return JSONResponse(
            status_code=429,
            content={'ok': False, 'message': 'Muitas tentativas de login. Aguarde um minuto.'},
        )
    if not settings.web_users:
        return JSONResponse(
            status_code=500,
            content={'ok': False, 'message': 'Nenhum usuário configurado (WEB_USERS no .env).'},
        )
    if not authenticate_user(payload.username, payload.password):
        logger.warning('Login falhou (ip=%s, user=%r)', ip, payload.username)
        return JSONResponse(
            status_code=401,
            content={'ok': False, 'message': 'Usuário ou senha inválidos.'},
        )
    token = make_session_token(payload.username)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite='lax',
        secure=settings.session_cookie_secure,
        path='/',
    )
    logger.info('Login ok (user=%s, ip=%s)', payload.username, ip)
    return {'ok': True, 'user': payload.username}


@app.post('/api/v1/auth/logout')
def api_logout(response: Response) -> dict[str, bool]:
    """Encerra a sessão (remove o cookie)."""
    response.delete_cookie(SESSION_COOKIE, path='/')
    return {'ok': True}


@app.get('/api/v1/auth/me')
def api_me(request: Request) -> object:
    """Usuário logado (usado pelo frontend ao abrir a página)."""
    user = get_current_user(request)
    return {'ok': True, 'user': user, 'jobs_active': JOB_MANAGER.count(owner=user)}


@app.post('/api/v1/validate')
def api_validate(payload: ValidateRequest) -> dict[str, object]:
    """Valida os campos do formulário (espelho do validators do desktop)."""
    return validate_form(
        cpf=payload.cpf,
        unit=payload.unit,
        date_start=payload.date_start,
        date_end=payload.date_end,
        excel=payload.excel,
        pdf=payload.pdf,
    )


@app.get('/api/v1/unidades')
def api_unidades(
        q: str = Query(default='', description='Texto de busca (descrição ou código)'),
        limit: int = Query(default=50, le=200),
) -> dict[str, object]:
    """Autocomplete de unidades a partir do data/unidades.csv."""
    try:
        results = search_unidades(query=q, limit=limit)
        return {'ok': True, 'count': len(results), 'results': results}
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={'ok': False, 'message': f'Erro ao carregar unidades: {e}'},
        )


@app.post('/api/v1/ponto')
def api_ponto(payload: PontoRequest, request: Request) -> object:
    """Legado síncrono: executa o fluxo completo e devolve o ZIP.

    Mantido por compatibilidade; requer sessão autenticada (FASE 4).
    O frontend usa a API de jobs (assíncrona) a partir da FASE 3.
    """
    get_current_user(request)
    try:
        cpf_digits = normalize_cpf(payload.cpf)
        start = parse_br_month(payload.date_start, 'date_start')
        end = parse_br_month(payload.date_end, 'date_end')

        zip_bytes = run_ponto_flow(
            cpf=cpf_digits,
            unit=payload.unit,
            start=start,
            end=end,
            excel=payload.excel,
            pdf=payload.pdf,
        )

        filename = build_zip_filename(payload.unit, start, end)
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
    except PontoRequestError as e:
        return JSONResponse(status_code=422, content={'ok': False, 'message': str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={'ok': False, 'message': 'Erro interno ao gerar os arquivos.', 'detail': str(e)},
        )


@app.get('/')
def index() -> FileResponse:
    """Serve a página frontend (formulário + progresso + histórico)."""
    return FileResponse(FRONTEND_INDEX)


# ---------------------------------------------------------------------------
# FASE 2/3: jobs assíncronos, progresso (SSE), download e histórico
# ---------------------------------------------------------------------------


def _owned_job(job_id: str, user: str) -> Job:
    """Busca um job garantindo que pertence ao usuário autenticado.

    Levanta JobAccessError: 404 se não existir, 403 se for de outro usuário.
    """
    job = JOB_MANAGER.get(job_id)
    if job is None:
        raise JobAccessError(404, 'Job não encontrado.')
    if job.owner != user:
        raise JobAccessError(403, 'Acesso negado a esta geração.')
    return job


@app.post('/api/v1/jobs', status_code=202)
def api_create_job(payload: PontoRequest, request: Request) -> object:
    """Enfileira um job de geração e devolve o registro (status QUEUED)."""
    user = get_current_user(request)
    validation = validate_form(
        cpf=payload.cpf,
        unit=payload.unit,
        date_start=payload.date_start,
        date_end=payload.date_end,
        excel=payload.excel,
        pdf=payload.pdf,
    )
    if not validation['valid']:
        return JSONResponse(
            status_code=422,
            content={'ok': False, 'errors': validation['errors']},
        )

    ip = client_ip(request)
    if not job_creation_allowed(ip, user):
        return JSONResponse(
            status_code=429,
            content={'ok': False,
                     'message': 'Muitas gerações iniciadas em pouco tempo. '
                                'Aguarde um minuto.'},
        )
    if JOB_MANAGER.count_active(owner=user) >= JOB_MAX_ACTIVE:
        return JSONResponse(
            status_code=429,
            content={'ok': False,
                     'message': f'Limite de {JOB_MAX_ACTIVE} gerações ativas '
                                'por usuário. Aguarde uma concluir.'},
        )

    job = JOB_MANAGER.create(payload.model_dump(), owner=user)
    logger.info('Job criado: %s (user=%s, cpf=%s, unidade=%s)',
                job.id, user, payload.cpf, payload.unit)
    return {'ok': True, 'job': job.to_dict()}


@app.get('/api/v1/jobs')
def api_list_jobs(
        request: Request,
        limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    """Histórico navegável do usuário: jobs mais recentes primeiro (últimos N)."""
    user = get_current_user(request)
    jobs = JOB_MANAGER.list(owner=user, limit=limit)
    return {
        'ok': True,
        'count': len(jobs),
        'jobs': [j.to_dict() for j in jobs],
    }


@app.delete('/api/v1/jobs')
def api_clear_jobs(request: Request) -> dict[str, object]:
    """Remove as gerações concluídas/falhas DO USUÁRIO (registro + arquivos em disco).

    Jobs na fila ou em execução são preservados.
    """
    user = get_current_user(request)
    removed = JOB_MANAGER.clear(owner=user)
    logger.info('Histórico limpo pela API: %s job(s) removido(s) (user=%s).', removed, user)
    return {'ok': True, 'removed': removed}


@app.delete('/api/v1/jobs/{job_id}')
def api_delete_job(job_id: str, request: Request) -> object:
    """Exclui uma geração concluída/falha do usuário (registro + arquivos em disco)."""
    user = get_current_user(request)
    try:
        _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})

    outcome = JOB_MANAGER.remove(job_id)
    if outcome == 'not_found':
        return JSONResponse(
            status_code=404,
            content={'ok': False, 'message': 'Job não encontrado.'},
        )
    if outcome == 'busy':
        return JSONResponse(
            status_code=409,
            content={'ok': False, 'message': 'Geração em andamento não pode ser excluída.'},
        )
    logger.info('Job excluído pela API: %s (user=%s).', job_id, user)
    return {'ok': True, 'removed': 1}


@app.post('/api/v1/jobs/{job_id}/cancel')
def api_cancel_job(job_id: str, request: Request) -> object:
    """Cancela uma geração do usuário na fila ou em execução.

    O processamento aborta entre etapas (mês a mês) e o job fica com
    status CANCELLED no histórico; a janela do navegador permanece
    aberta (minimizada) para reuso da sessão.
    """
    user = get_current_user(request)
    try:
        _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})

    outcome = JOB_MANAGER.cancel(job_id)
    if outcome == 'not_found':
        return JSONResponse(
            status_code=404,
            content={'ok': False, 'message': 'Job não encontrado.'},
        )
    if outcome == 'terminal':
        return JSONResponse(
            status_code=409,
            content={'ok': False, 'message': 'Geração já concluída/falhou; nada a cancelar.'},
        )
    logger.info('Job cancelado pela API: %s (user=%s).', job_id, user)
    return {'ok': True, 'status': 'CANCELLED'}


@app.get('/api/v1/jobs/{job_id}')
def api_get_job(job_id: str, request: Request) -> object:
    """Status/progresso detalhado de um job do usuário."""
    user = get_current_user(request)
    try:
        job = _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})
    return {'ok': True, 'job': job.to_dict()}


def _sse(data: dict[str, object]) -> str:
    """Serializa um evento SSE (campo 'data' com JSON)."""
    return f'data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n'


@app.get('/api/v1/jobs/{job_id}/events')
async def api_job_events(job_id: str, request: Request) -> object:
    """Fluxo SSE com o progresso do job em tempo real.

    Emite um evento a cada mudança de versão do job (progresso, logs,
    arquivos, estado final) e encerra quando o job termina.
    """
    # Valida a sessão ANTES de abrir o stream (401/403 sem conexão mantida)
    user = get_current_user(request)
    try:
        _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})

    async def event_stream():
        last_version = -1
        while True:
            job = JOB_MANAGER.get(job_id)
            if job is None:
                yield _sse({'type': 'error', 'message': 'Job não encontrado.'})
                return
            if job.version != last_version:
                last_version = job.version
                yield _sse({'type': 'update', 'job': job.to_dict()})
            if job.status in TERMINAL_STATUSES:
                return
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


def _job_files_on_disk(job_id: str, fmt: str) -> list[Path]:
    """Caminhos dos arquivos do job filtrados por formato ('xlsx'|'pdf'|'zip'=todos)."""
    job = JOB_MANAGER.get(job_id)
    if job is None:
        raise LookupError('Job não encontrado.')
    selected = [f for f in job.files if fmt == 'zip' or f.format == fmt]
    paths: list[Path] = []
    for record in selected:
        path = job.directory / record.name
        if path.exists():
            paths.append(path)
    return paths


def _zip_bytes(paths: list[Path]) -> bytes:
    """Compacta os arquivos em um ZIP em memória (nomes originais)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, arcname=path.name)
    return buffer.getvalue()


@app.get('/api/v1/jobs/{job_id}/download')
def api_job_download(
        job_id: str,
        request: Request,
        format: str = Query(default='zip', pattern='^(xlsx|pdf|zip)$'),
        parts: str = Query(default='', pattern='^(|zip)$'),
) -> object:
    """Download dos arquivos gerados pelo job.

    format=xlsx        -> planilha gerada (falha se o job não gerou Excel)
    format=pdf         -> PDF único
    format=pdf&parts=zip -> ZIP com as partes (_part1..N.pdf)
    format=zip         -> todos os arquivos compactados
    """
    user = get_current_user(request)
    try:
        job = _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})
    if job.status != JobStatus.DONE:
        return JSONResponse(
            status_code=409,
            content={'ok': False, 'message': 'O job ainda não foi concluído.'},
        )
    if not job.files:
        return JSONResponse(
            status_code=409,
            content={'ok': False, 'message': 'O job não gerou arquivos.'},
        )

    fmt = (format or 'zip').lower()
    zip_parts = fmt == 'pdf' and parts == 'zip'
    paths = _job_files_on_disk(job_id, 'pdf' if zip_parts else fmt)
    if not paths:
        return JSONResponse(
            status_code=400,
            content={'ok': False,
                     'message': 'Nenhum arquivo deste tipo foi gerado; escolha outro formato.'},
        )

    # Arquivo único: entrega direto com o mesmo nome do desktop
    if len(paths) == 1 and not zip_parts:
        path = paths[0]
        return FileResponse(
            path,
            media_type=MEDIA_TYPES.get(path.suffix.lstrip('.'), 'application/octet-stream'),
            filename=path.name,
        )

    # Vários PDFs sem ?parts=zip: orienta o cliente
    if fmt == 'pdf' and not zip_parts and len(paths) > 1:
        return JSONResponse(
            status_code=400,
            content={'ok': False,
                     'message': 'O PDF gerado foi dividido em partes. Use pdf&parts=zip '
                                'ou baixe as partes individualmente.'},
        )

    filename = 'ponto_{}.zip'.format(
        job.payload.get('unit', '') or job.id)
    return StreamingResponse(
        io.BytesIO(_zip_bytes(paths)),
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@app.get('/api/v1/jobs/{job_id}/files/{filename}')
def api_job_file(job_id: str, filename: str, request: Request) -> object:
    """Download de um arquivo individual do job (ex.: uma parte do PDF)."""
    user = get_current_user(request)
    try:
        job = _owned_job(job_id, user)
    except JobAccessError as e:
        return JSONResponse(status_code=e.status_code, content={'ok': False, 'message': e.message})
    if job.status != JobStatus.DONE:
        return JSONResponse(
            status_code=409,
            content={'ok': False, 'message': 'O job ainda não foi concluído.'},
        )

    record = next((f for f in job.files if f.name == filename), None)
    if record is None:
        return JSONResponse(status_code=404, content={'ok': False, 'message': 'Arquivo não encontrado.'})

    path = job.directory / record.name
    if not path.exists():
        return JSONResponse(
            status_code=410,
            content={'ok': False, 'message': 'Arquivo expirado (fora do período de retenção).'},
        )
    return FileResponse(
        path,
        media_type=MEDIA_TYPES.get(record.format, 'application/octet-stream'),
        filename=record.name,
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000, reload=True)