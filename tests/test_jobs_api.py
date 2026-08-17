"""Testes da API de Jobs (FASE 2/3): criação, progresso, SSE, downloads,
histórico e limpeza por TTL.

Usa um JobManager com runner fake (sem Chrome/selenium), injetado no
módulo da API. Verifica:
- POST /api/v1/jobs -> 202 e ciclo QUEUED -> RUNNING -> DONE/FAILED
- GET  /api/v1/jobs/{id} e /api/v1/jobs (histórico limitado)
- GET  /api/v1/jobs/{id}/events (SSE emite estado final DONE)
- GET  /api/v1/jobs/{id}/download?format=xlsx|pdf|zip e ?parts=zip
- GET  /api/v1/jobs/{id}/files/{name}
- DELETE /api/v1/jobs (limpa histórico: terminais removidos, execução preservada)
- DELETE /api/v1/jobs/{id} (exclui uma geração específica; 404/409 se inválida)
- cleanup_expired (TTL) remove registros e pastas
"""
import time
import urllib.parse
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.auth import reset_rate_limit
from backend.core.exceptions import JobCancelledError
from backend.core.job import JobFile, JobManager

XLSX_NAME = 'MARIA SOUZA - CPF_529.982.247-25.xlsx'
PDF_PART_1 = 'MARIA SOUZA - CPF_529.982.247-25_part1.pdf'
PDF_PART_2 = 'MARIA SOUZA - CPF_529.982.247-25_part2.pdf'

WEB_USER = 'alice'
WEB_PASSWORD = 'secret123'

VALID_PAYLOAD = {
    'cpf': '52998224725',
    'unit': '1',
    'date_start': '01/2024',
    'date_end': '03/2024',
    'excel': True,
    'pdf': True,
}


def make_runner(files, delay=0.3):
    """Runner fake que simula processamento e gera arquivos reais no job_dir."""

    def runner(job_id, payload, job_dir, on_message, on_progress, cancel_check=None):
        time.sleep(delay)
        if cancel_check and cancel_check():
            raise JobCancelledError('Cancelado pelo usuário.')
        on_message('Janeiro coletado (1/2)')
        on_progress(1, 2)
        time.sleep(delay)
        if cancel_check and cancel_check():
            raise JobCancelledError('Cancelado pelo usuário.')
        on_message('Fevereiro coletado (2/2)')
        on_progress(2, 2)
        on_message('Gerando arquivos finais...')
        for record in files:
            (job_dir / record.name).write_bytes(f'content-{record.name}'.encode())
        return list(files)

    return runner


def wait_done(job_id, timeout=10.0):
    """Pota o job até um estado terminal (DONE/FAILED/CANCELLED) e devolve o dict JSON."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = main_module.JOB_MANAGER.get(job_id)
        assert job is not None
        if job.status.value in ('DONE', 'FAILED', 'CANCELLED'):
            return job.to_dict()
        time.sleep(0.05)
    raise AssertionError(f'Job {job_id} não terminou em {timeout}s')


@pytest.fixture(autouse=True)
def _fresh_manager(tmp_path, monkeypatch):
    """Cada teste ganha um JobManager fake, OUTPUT_DIR e usuário web temporários."""
    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('WEB_USERS', f'{WEB_USER}:{WEB_PASSWORD}')
    monkeypatch.setenv('SESSION_SECRET', 'test-secret')
    reset_rate_limit()
    manager = JobManager(
        run_fn=make_runner([
            JobFile(XLSX_NAME, 'xlsx'),
            JobFile(PDF_PART_1, 'pdf'),
            JobFile(PDF_PART_2, 'pdf'),
        ]),
        ttl_hours=24,
        history_limit=5,
    )
    main_module.JOB_MANAGER = manager
    yield manager
    manager.shutdown()


@pytest.fixture
def client(_fresh_manager):
    c = TestClient(main_module.app)
    res = c.post('/api/v1/auth/login',
                 json={'username': WEB_USER, 'password': WEB_PASSWORD})
    assert res.status_code == 200, res.text
    return c


def create_job(client, **overrides):
    payload = dict(VALID_PAYLOAD)
    payload.update(overrides)
    return client.post('/api/v1/jobs', json=payload)


class TestCreateAndStatus:

    def test_create_job_returns_202_with_job(self, client):
        res = create_job(client)
        assert res.status_code == 202
        data = res.json()
        assert data['ok'] is True
        job = data['job']
        assert job['id']
        assert job['status'] in ('QUEUED', 'RUNNING', 'DONE')
        assert job['payload']['cpf'] == '52998224725'

    def test_create_job_invalid_returns_422(self, client):
        res = create_job(client, cpf='123')
        assert res.status_code == 422
        data = res.json()
        assert data['ok'] is False
        assert 'errors' in data and 'cpf' in data['errors']

    def test_job_completes_with_files_and_progress(self, client):
        job_id = create_job(client).json()['job']['id']
        done = wait_done(job_id)

        assert done['status'] == 'DONE'
        assert done['progress']['percent'] == 100
        assert done['progress']['months_total'] == 2
        assert {f['name'] for f in done['files']} == {XLSX_NAME, PDF_PART_1, PDF_PART_2}
        assert done['logs']

    def test_get_job_unknown_404(self, client):
        res = client.get('/api/v1/jobs/nao-existe')
        assert res.status_code == 404

    def test_download_before_done_conflict(self, client, tmp_path):
        """Runner lento: download enquanto executa devolve 409."""
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=1.5), history_limit=5)
        job_id = create_job(client).json()['job']['id']
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=zip')
        assert res.status_code == 409


class TestDownloads:

    def test_download_xlsx_single(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=xlsx')
        assert res.status_code == 200
        assert res.content == f'content-{XLSX_NAME}'.encode()
        disposition = res.headers.get('content-disposition', '')
        assert XLSX_NAME in urllib.parse.unquote(disposition)  # nome igual ao desktop

    def test_download_pdf_requires_parts_when_split(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=pdf')
        assert res.status_code == 400
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=pdf&parts=zip')
        assert res.status_code == 200
        assert res.headers['content-type'] == 'application/zip'
        with zipfile.ZipFile(BytesIO(res.content)) as zf:
            assert set(zf.namelist()) == {PDF_PART_1, PDF_PART_2}

    def test_download_pdf_single_part(self, client):
        single = JobManager(run_fn=make_runner(
            [JobFile(PDF_PART_1, 'pdf')], delay=0.1), history_limit=5)
        main_module.JOB_MANAGER = single
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=pdf')
        assert res.status_code == 200
        assert res.content == f'content-{PDF_PART_1}'.encode()

    def test_download_zip_all_files(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=zip')
        assert res.status_code == 200
        with zipfile.ZipFile(BytesIO(res.content)) as zf:
            assert set(zf.namelist()) == {XLSX_NAME, PDF_PART_1, PDF_PART_2}

    def test_download_wrong_format_400(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=xlsx&parts=zip')
        assert res.status_code == 200  # xlsx único ignora parts
        res = client.get(f'/api/v1/jobs/{job_id}/download?format=banana')
        assert res.status_code == 422  # pattern rejeita formato inválido

    def test_individual_file_download(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.get(f'/api/v1/jobs/{job_id}/files/{PDF_PART_1}')
        assert res.status_code == 200
        assert res.content == f'content-{PDF_PART_1}'.encode()
        res = client.get(f'/api/v1/jobs/{job_id}/files/outro.pdf')
        assert res.status_code == 404


class TestHistoryAndCleanup:

    def test_list_jobs_history_ordered_and_limited(self, client):
        ids = [create_job(client).json()['job']['id'] for _ in range(3)]
        for job_id in ids:
            wait_done(job_id)

        res = client.get('/api/v1/jobs')
        data = res.json()
        assert data['ok'] is True
        assert len(data['jobs']) == 3
        assert [_ for _ in data['jobs'][0]['id']]  # item mais recente primeiro
        assert data['jobs'][0]['id'] == ids[-1]

        res = client.get('/api/v1/jobs?limit=2')
        assert len(res.json()['jobs']) == 2

    def test_cleanup_expired_removes_job_and_folder(self, _fresh_manager, client):
        job_id = create_job(client).json()['job']['id']
        done = wait_done(job_id)
        folder = _fresh_manager.get(job_id).directory
        assert folder.exists()

        removed = _fresh_manager.cleanup_expired(ttl_hours=0)
        assert removed >= 1
        assert _fresh_manager.get(job_id) is None
        assert not folder.exists()

    def test_history_limit_trimmed_on_cleanup(self, _fresh_manager, client):
        for _ in range(7):
            job_id = create_job(client).json()['job']['id']
            wait_done(job_id)
        _fresh_manager.cleanup_expired(ttl_hours=24 * 30)
        assert _fresh_manager.count() <= 5

    def test_clear_history_removes_terminal_jobs_and_folders(self, _fresh_manager, client):
        ids = [create_job(client).json()['job']['id'] for _ in range(2)]
        folders = []
        for job_id in ids:
            wait_done(job_id)
            folders.append(_fresh_manager.get(job_id).directory)
            assert folders[-1].exists()

        res = client.delete('/api/v1/jobs')
        assert res.status_code == 200
        data = res.json()
        assert data['ok'] is True
        assert data['removed'] == 2

        assert client.get('/api/v1/jobs').json()['jobs'] == []
        for folder in folders:
            assert not folder.exists()

    def test_clear_history_keeps_running_job(self, client):
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=2.0), history_limit=5)
        job_id = create_job(client).json()['job']['id']

        res = client.delete('/api/v1/jobs')
        assert res.status_code == 200
        assert res.json()['removed'] == 0
        assert client.get('/api/v1/jobs').json()['jobs']  # job em execução preservado

        wait_done(job_id)
        assert client.delete('/api/v1/jobs').json()['removed'] == 1

    def test_delete_job_removes_record_and_folder(self, _fresh_manager, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        folder = _fresh_manager.get(job_id).directory
        assert folder.exists()

        res = client.delete(f'/api/v1/jobs/{job_id}')
        assert res.status_code == 200
        assert res.json()['ok'] is True

        assert _fresh_manager.get(job_id) is None
        assert not folder.exists()
        assert client.get('/api/v1/jobs').json()['jobs'] == []

    def test_delete_job_unknown_404(self, client):
        res = client.delete('/api/v1/jobs/nao-existe')
        assert res.status_code == 404
        assert res.json()['ok'] is False

    def test_delete_job_running_409(self, client):
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=2.0), history_limit=5)
        job_id = create_job(client).json()['job']['id']

        res = client.delete(f'/api/v1/jobs/{job_id}')
        assert res.status_code == 409
        assert res.json()['message']

        wait_done(job_id)
        assert client.delete(f'/api/v1/jobs/{job_id}').status_code == 200

    def test_delete_one_keeps_others(self, client):
        ids = [create_job(client).json()['job']['id'] for _ in range(2)]
        for job_id in ids:
            wait_done(job_id)

        assert client.delete(f'/api/v1/jobs/{ids[0]}').status_code == 200
        remaining = client.get('/api/v1/jobs').json()['jobs']
        assert [j['id'] for j in remaining] == [ids[1]]


class TestCancel:

    def test_cancel_running_job_marks_cancelled(self, client):
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=2.0), history_limit=5)
        job_id = create_job(client).json()['job']['id']

        res = client.post(f'/api/v1/jobs/{job_id}/cancel')
        assert res.status_code == 200
        assert res.json()['status'] == 'CANCELLED'

        status = wait_done(job_id)['status']
        assert status == 'CANCELLED'

    def test_cancel_job_queued(self, client):
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=0.8), history_limit=5)
        first = create_job(client).json()['job']['id']
        queued = create_job(client).json()['job']['id']  # este ainda na fila

        res = client.post(f'/api/v1/jobs/{queued}/cancel')
        assert res.status_code == 200
        assert res.json()['status'] == 'CANCELLED'

        wait_done(first)
        job = main_module.JOB_MANAGER.get(queued)
        assert job.status.value == 'CANCELLED'  # nunca chegou a executar
        assert job.started_at is None

    def test_cancel_terminal_job_409(self, client):
        job_id = create_job(client).json()['job']['id']
        wait_done(job_id)
        res = client.post(f'/api/v1/jobs/{job_id}/cancel')
        assert res.status_code == 409

    def test_cancel_unknown_404(self, client):
        res = client.post('/api/v1/jobs/nao-existe/cancel')
        assert res.status_code == 404

    def test_sse_emits_cancelled(self, client):
        main_module.JOB_MANAGER = JobManager(run_fn=make_runner(
            [JobFile(XLSX_NAME, 'xlsx')], delay=2.0), history_limit=5)
        job_id = create_job(client).json()['job']['id']
        client.post(f'/api/v1/jobs/{job_id}/cancel')

        res = client.get(f'/api/v1/jobs/{job_id}/events')
        assert res.status_code == 200
        assert '"status": "CANCELLED"' in res.text


class TestSse:

    def test_sse_stream_emits_done(self, client):
        job_id = create_job(client).json()['job']['id']

        res = client.get(f'/api/v1/jobs/{job_id}/events')
        assert res.status_code == 200
        assert res.text.startswith('data: ')
        assert '"status": "DONE"' in res.text
        assert '"percent": 100' in res.text

    def test_sse_unknown_job_emits_error(self, client):
        res = client.get('/api/v1/jobs/nao-existe/events')
        assert res.status_code == 404
        assert 'não encontrado' in res.json()['message']