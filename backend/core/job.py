"""Sistema de Jobs assíncronos para a geração dos arquivos (FASE 2/3).

- Fila serializada (ThreadPoolExecutor com 1 worker): as gerações não
  competem pelo driver único do Chrome (sessão persistente do portal).
- Ciclo de vida: QUEUED -> RUNNING -> DONE/FAILED, com progresso
  (meses OK/total), mensagens de status, logs e arquivos gerados.
- Cada job tem uma pasta própria (settings.OUTPUT_DIR/jobs/<id>) que é
  removida na limpeza por TTL (expiração) junto com o registro.
- Histórico limitado aos N jobs mais recentes (JOBS_HISTORY_LIMIT).

O executor real (scraping + geração) é injetado via run_fn, o que
permite testar todo o mecanismo com um runner fake (sem Chrome).
"""
import logging
import shutil
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from .exceptions import JobCancelledError
from .settings import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Estados possíveis de um job (coincidem com o status exibido no frontend)."""

    QUEUED = 'QUEUED'
    RUNNING = 'RUNNING'
    DONE = 'DONE'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


TERMINAL_STATUSES = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)


@dataclass
class JobFile:
    """Arquivo gerado por um job (para download)."""

    name: str
    format: str  # 'xlsx' | 'pdf'


@dataclass
class Job:
    """Registro de um job de geração de arquivos."""

    id: str
    payload: dict[str, object] = field(default_factory=dict)
    owner: str = ''
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    done_at: datetime | None = None
    progress: dict[str, object] = field(default_factory=lambda: {
        'months_ok': 0,
        'months_total': 0,
        'percent': 0,
        'message': 'Na fila...',
    })
    logs: list[str] = field(default_factory=list)
    files: list[JobFile] = field(default_factory=list)
    error: str = ''
    # Sinal de cancelamento (set() interrompe a execução em andamento).
    _cancelled: threading.Event = field(default_factory=threading.Event, repr=False)
    # Incrementado a cada mudança de estado; usado pelo SSE para saber
    # quando emitir uma nova atualização ao frontend.
    version: int = 0

    @property
    def directory(self) -> Path:
        """Pasta exclusiva do job dentro de settings.OUTPUT_DIR."""
        return settings.output_dir / 'jobs' / self.id

    def cancel(self) -> None:
        """Marca o job para cancelamento (a execução aborta entre etapas)."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def to_dict(self, with_payload: bool = True) -> dict[str, object]:
        """Representação JSON-friendly do job (sem credenciais)."""
        data: dict[str, object] = {
            'id': self.id,
            'owner': self.owner,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(timespec='seconds'),
            'progress': self.progress,
            'files': [{'name': f.name, 'format': f.format} for f in self.files],
            'logs': self.logs,
            'error': self.error,
        }
        if self.started_at:
            data['started_at'] = self.started_at.isoformat(timespec='seconds')
        if self.done_at:
            data['done_at'] = self.done_at.isoformat(timespec='seconds')
        if with_payload:
            data['payload'] = self.payload
        return data


JobRunner = Callable[[str, dict[str, object], Path, Callable[[str], None],
                      Callable[[int, int], None], Callable[[], bool]],
                     list[JobFile]]


class JobManager:
    """Gerencia criação, execução, histórico e expiração de jobs.

    - run_fn(job_id, payload, job_dir, on_message, on_progress) -> list[JobFile]
      é o fluxo real (login + scraping + geração de arquivos).
    - A execução é serializada (max_workers=1) para reutilizar com
      segurança o driver único do Chrome.
    """

    def __init__(
            self,
            run_fn: JobRunner,
            ttl_hours: float = 24,
            history_limit: int = 20,
            max_workers: int = 1,
    ):
        self._run_fn = run_fn
        self.ttl_hours = ttl_hours
        self.history_limit = max(history_limit, 1)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix='job')

    # ----------------------------- criação -----------------------------

    def create(self, payload: dict[str, object], owner: str = '') -> Job:
        """Enfileira um novo job e retorna o registro (status QUEUED)."""
        job = Job(id=uuid.uuid4().hex[:12], payload=dict(payload), owner=owner)
        with self._lock:
            self._jobs[job.id] = job
        job.directory.mkdir(parents=True, exist_ok=True)
        self._add_log(job.id, 'Job enfileirado.')
        self._executor.submit(self._run, job.id)
        return job

    # --------------------------- consulta ------------------------------

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, owner: str | None = None,
             limit: int | None = None) -> list[Job]:
        """Histórico: jobs mais recentes primeiro, limitado por history_limit.

        Se owner for informado, retorna apenas os jobs daquele usuário.
        """
        limit = limit if limit is not None else self.history_limit
        with self._lock:
            values = self._jobs.values()
            if owner is not None:
                values = [j for j in values if j.owner == owner]
            ordered = sorted(
                values,
                key=lambda j: (j.created_at, j.id),
                reverse=True,
            )
            return ordered[:limit]

    def count(self, owner: str | None = None) -> int:
        with self._lock:
            values = self._jobs.values()
            if owner is not None:
                values = [j for j in values if j.owner == owner]
            return len(values)

    def count_active(self, owner: str | None = None) -> int:
        """Jobs em QUEUED ou RUNNING (fila + execução) de um usuário.

        Usado pelo rate-limit da API: impede que um usuário entupa a fila
        (execução é serial) com mais do que o limite configurado.
        """
        with self._lock:
            active = 0
            for job in self._jobs.values():
                if owner is not None and job.owner != owner:
                    continue
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                    active += 1
            return active

    # --------------------------- execução ------------------------------

    def _run(self, job_id: str) -> None:
        """Executa o runner injetado e atualiza o estado do job."""
        job = self.get(job_id)
        if job is None:
            return

        if job.is_cancelled():
            # Foi cancelado ainda na fila: encerra sem executar
            with self._lock:
                job.status = JobStatus.CANCELLED
                job.done_at = datetime.now()
                job.version += 1
            self._add_log(job_id, 'Processamento cancelado antes de iniciar.')
            return

        with self._lock:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            job.version += 1
        self._add_log(job_id, 'Processamento iniciado.')

        def track_progress(months_ok: int, months_total: int) -> None:
            percent = 0
            if months_total > 0:
                percent = min(100, round(months_ok * 100 / months_total))
            self._update(job_id, progress={
                'months_ok': months_ok,
                'months_total': months_total,
                'percent': percent,
            })

        try:
            files = self._run_fn(
                job_id,
                job.payload,
                job.directory,
                lambda text: self.message(job_id, text),
                track_progress,
                job.is_cancelled,
            )
            if job.is_cancelled():
                raise JobCancelledError('Processamento cancelado pelo usuário.')
            with self._lock:
                job.status = JobStatus.DONE
                job.done_at = datetime.now()
                job.files = list(files)
                job.progress['percent'] = 100
                job.version += 1
            self._add_log(job_id,
                          f'Concluído: {len(job.files)} arquivo(s) gerado(s).')
        except JobCancelledError as e:
            logger.info('Job %s cancelado', job_id)
            message = getattr(e, 'message', None) or str(e)
            with self._lock:
                job.status = JobStatus.CANCELLED
                job.done_at = datetime.now()
                job.error = message
                job.version += 1
            self._add_log(job_id, f'Cancelado: {message}')
        except Exception as e:  # noqa: BLE001 - qualquer falha marca FAILED
            logger.exception('Job %s falhou', job_id)
            message = getattr(e, 'message', None) or str(e)
            with self._lock:
                job.status = JobStatus.FAILED
                job.done_at = datetime.now()
                job.error = message
                job.version += 1
            self._add_log(job_id, f'Falha: {message}')

    def cancel(self, job_id: str) -> str:
        """Cancela um job na fila ou em execução.

        Retorna 'cancelled' em caso de sucesso; 'not_found' quando o job
        não existe; 'terminal' quando o job já terminou (DONE/FAILED).
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return 'not_found'
            if job.status in TERMINAL_STATUSES:
                return 'terminal'
            was_queued = job.status == JobStatus.QUEUED
            job.cancel()
            job.status = JobStatus.CANCELLED
            job.version += 1
            if was_queued:
                job.done_at = datetime.now()
        return 'cancelled'

    def _update(self, job_id: str, **fields: object) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.version += 1

    def message(self, job_id: str, text: str) -> None:
        """Atualiza a mensagem de progresso do job (callback do runner)."""
        job = self.get(job_id)
        if job is None:
            return
        self._update(job_id, progress={
            **job.progress,
            'message': text,
        })

    def _add_log(self, job_id: str, text: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.logs.append(text)
            job.logs = job.logs[-30:]
            job.version += 1

    # --------------------------- limpeza -------------------------------

    def cleanup_expired(self, ttl_hours: float | None = None) -> int:
        """Remove jobs terminais mais antigos que o TTL (pastas inclusas).

        Também enxuga a memória mantendo no máximo history_limit jobs
        POR USUÁRIO (descartando os mais antigos já terminados). Retorna
        quantos jobs foram removidos.
        """
        ttl = float(ttl_hours) if ttl_hours is not None else float(self.ttl_hours)
        cutoff = datetime.now() - timedelta(hours=ttl)
        removed = 0

        with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.status in TERMINAL_STATUSES and job.created_at < cutoff:
                    self._jobs.pop(job_id, None)
                    self._remove_directory(job.directory)
                    removed += 1

            # Limite do histórico por usuário (não interfere na execução)
            by_owner: dict[str, list[Job]] = {}
            for job in self._jobs.values():
                by_owner.setdefault(job.owner, []).append(job)

            for owner_jobs in by_owner.values():
                ordered = sorted(
                    owner_jobs,
                    key=lambda j: (j.created_at, j.id),
                    reverse=True,
                )
                for job in ordered[self.history_limit:]:
                    if job.status in TERMINAL_STATUSES:
                        self._jobs.pop(job.id, None)
                        self._remove_directory(job.directory)
                        removed += 1

        if removed:
            logger.info('Limpeza: %s job(s) expirado(s) removido(s).', removed)
        return removed

    @staticmethod
    def _remove_directory(path: Path) -> None:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:  # noqa: BLE001
            logger.warning('Não foi possível remover a pasta %s', path)

    def clear(self, owner: str | None = None) -> int:
        """Remove jobs terminais (registro + pasta em disco).

        Jobs na fila ou em execução são preservados. Se owner for
        informado, remove apenas os jobs daquele usuário. Retorna
        quantos jobs foram removidos.
        """
        removed = 0
        with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.status in TERMINAL_STATUSES:
                    if owner is not None and job.owner != owner:
                        continue
                    self._jobs.pop(job_id, None)
                    self._remove_directory(job.directory)
                    removed += 1
        if removed:
            logger.info('Histórico limpo: %s job(s) removido(s).', removed)
        return removed

    def remove(self, job_id: str) -> str:
        """Remove um job terminal específico (registro + pasta em disco).

        Jobs na fila ou em execução não podem ser excluídos. Retorna
        'removed', 'not_found' ou 'busy'.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return 'not_found'
            if job.status not in TERMINAL_STATUSES:
                return 'busy'
            self._jobs.pop(job_id, None)
            self._remove_directory(job.directory)
        logger.info('Job removido: %s.', job_id)
        return 'removed'

    def shutdown(self) -> None:
        """Encerra o pool de threads (não aguarda filas em andamento)."""
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:  # noqa: BLE001
            pass