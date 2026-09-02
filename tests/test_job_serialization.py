"""Testes de serialização/deserialização de Job (to_meta / from_meta).

Cobertos:
- Ida-e-volta (roundtrip): Job → to_meta() → from_meta() → campos idênticos
- Campos opcionais (started_at, done_at) ausentes
- Status inválido (fallback para DONE)
- Timestamps inválidos (ignorados)
- files/logs corrompidos (tratados com defaults)
- _meta_version presente no output
- Persistência em disco (_meta.json gravado em estados terminais)
- Reidratação no startup (_hydrate_from_disk)
- Cenário E2E: restart do servidor via API
"""
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.auth import reset_job_rate_limit, reset_rate_limit
from backend.core.job import Job, JobFile, JobManager, JobStatus, _parse_iso


def _make_full_job() -> Job:
    """Job completo com todos os campos preenchidos."""
    job = Job(
        id='abc123def456',
        payload={'cpf': '52998224725', 'unit': '1', 'date_start': '01/2024',
                 'date_end': '03/2024', 'excel': True, 'pdf': True},
        owner='alice',
        status=JobStatus.DONE,
        created_at=datetime(2025, 3, 15, 10, 30, 0),
        started_at=datetime(2025, 3, 15, 10, 30, 5),
        done_at=datetime(2025, 3, 15, 10, 32, 15),
    )
    job.progress = {'months_ok': 3, 'months_total': 3, 'percent': 100, 'message': 'Concluído.'}
    job.files = [
        JobFile(name='MARIA - CPF_123.xlsx', format='xlsx'),
        JobFile(name='MARIA - CPF_123_part1.pdf', format='pdf'),
    ]
    job.logs = ['Job enfileirado.', 'Processamento iniciado.', 'Concluído: 2 arquivo(s).']
    job.error = ''
    job.version = 5
    return job


def _make_minimal_job() -> Job:
    """Job com apenas campos obrigatórios (sem started_at, done_at, files, error)."""
    return Job(
        id='minimal001',
        payload={},
        owner='bob',
        status=JobStatus.FAILED,
        created_at=datetime(2025, 6, 1, 8, 0, 0),
    )


class TestRoundtrip:
    """Ida-e-volta: Job → to_meta() → from_meta() → comparação campo a campo."""

    def test_full_job_roundtrip(self):
        original = _make_full_job()
        meta = original.to_meta()
        restored = Job.from_meta(meta)

        assert restored.id == original.id
        assert restored.owner == original.owner
        assert restored.status == original.status
        assert restored.payload == original.payload
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.done_at == original.done_at
        assert restored.progress == original.progress
        assert restored.error == original.error

        assert len(restored.files) == len(original.files)
        for rf, of in zip(restored.files, original.files):
            assert rf.name == of.name
            assert rf.format == of.format

        assert restored.logs == original.logs

    def test_minimal_job_roundtrip(self):
        original = _make_minimal_job()
        meta = original.to_meta()
        restored = Job.from_meta(meta)

        assert restored.id == original.id
        assert restored.owner == original.owner
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.started_at is None
        assert restored.done_at is None
        assert restored.files == []
        assert restored.error == ''

    def test_meta_has_version_key(self):
        job = _make_full_job()
        meta = job.to_meta()
        assert meta['_meta_version'] == 1

    def test_payload_always_included(self):
        job = _make_full_job()
        meta = job.to_meta()
        assert 'payload' in meta
        assert meta['payload'] == job.payload


class TestFromMetaEdgeCases:
    """from_meta() deve tratar dados faltantes ou corrompidos com graciosidade."""

    def test_empty_dict_returns_defaults(self):
        job = Job.from_meta({})
        assert job.id == ''
        assert job.owner == ''
        assert job.status == JobStatus.DONE  # fallback
        assert isinstance(job.created_at, datetime)
        assert job.files == []
        assert job.logs == []

    def test_invalid_status_falls_back_to_done(self):
        job = Job.from_meta({'status': 'INVALIDO'})
        assert job.status == JobStatus.DONE

    def test_invalid_timestamp_ignored(self):
        job = Job.from_meta({
            'created_at': 'not-a-date',
            'started_at': 'also-not-a-date',
            'done_at': '',
        })
        # created_at cai para datetime.now(); started_at/done_at são None
        assert isinstance(job.created_at, datetime)
        assert job.started_at is None
        assert job.done_at is None

    def test_missing_timestamp_uses_now(self):
        before = datetime.now()
        job = Job.from_meta({'id': 'test'})
        after = datetime.now()
        assert before <= job.created_at <= after

    def test_files_with_invalid_entries_ignored(self):
        job = Job.from_meta({
            'files': [
                {'name': 'ok.xlsx', 'format': 'xlsx'},
                'not-a-dict',
                {'name': 'ok2.pdf'},  # format ausente → string vazia
                42,
            ],
        })
        assert len(job.files) == 2
        assert job.files[0].name == 'ok.xlsx'
        assert job.files[0].format == 'xlsx'
        assert job.files[1].name == 'ok2.pdf'
        assert job.files[1].format == ''

    def test_logs_truncated_to_30(self):
        logs = [f'log-{i}' for i in range(50)]
        job = Job.from_meta({'logs': logs})
        assert len(job.logs) == 30
        assert job.logs[-1] == 'log-49'

    def test_version_restored(self):
        job = Job.from_meta({'version': 42})
        assert job.version == 42

    def test_non_numeric_version_ignored(self):
        job = Job.from_meta({'version': 'abc'})
        assert job.version == 0  # default


class TestParseIso:

    def test_valid_iso_string(self):
        dt = _parse_iso('2025-03-15T10:30:00')
        assert dt == datetime(2025, 3, 15, 10, 30, 0)

    def test_none_returns_none(self):
        assert _parse_iso(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_iso('') is None

    def test_invalid_string_returns_none(self):
        assert _parse_iso('not-a-date') is None

    def test_non_string_returns_none(self):
        assert _parse_iso(42) is None


# ---------------------------------------------------------------------------
# Helpers para testes de persistência (reutilizam padrão de test_jobs_api.py)
# ---------------------------------------------------------------------------

XLSX_NAME = 'MARIA - CPF_123.xlsx'
PDF_NAME = 'MARIA - CPF_123_part1.pdf'


def _make_runner(files, delay=0.05):
    def runner(job_id, payload, job_dir, on_message, on_progress, cancel_check=None):
        time.sleep(delay)
        if cancel_check and cancel_check():
            from backend.core.exceptions import JobCancelledError
            raise JobCancelledError('Cancelado.')
        on_progress(1, 1)
        for record in files:
            (job_dir / record.name).write_bytes(f'content-{record.name}'.encode())
        return list(files)
    return runner


def _wait_done(job_manager, job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = job_manager.get(job_id)
        if job is not None and job.status in (
            JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED
        ):
            return job
        time.sleep(0.02)
    raise AssertionError(f'Job {job_id} não terminou em {timeout}s')


class TestPersistence:
    """Verifica que _meta.json é gravado ao atingir estado terminal."""

    def test_meta_json_created_on_done(self, tmp_path):
        manager = JobManager(
            run_fn=_make_runner([JobFile(XLSX_NAME, 'xlsx')]),
            ttl_hours=24, history_limit=10,
        )
        try:
            job = manager.create({'cpf': '123'}, owner='alice')
            _wait_done(manager, job.id)

            meta_path = job.directory / '_meta.json'
            assert meta_path.exists(), '_meta.json não foi criado'

            data = json.loads(meta_path.read_text(encoding='utf-8'))
            assert data['id'] == job.id
            assert data['status'] == 'DONE'
            assert data['owner'] == 'alice'
            assert data['_meta_version'] == 1
            assert len(data['files']) == 1
            assert data['files'][0]['name'] == XLSX_NAME
        finally:
            manager.shutdown()

    def test_meta_json_created_on_failed(self, tmp_path):
        def failing_runner(job_id, payload, job_dir, on_message, on_progress,
                           cancel_check=None):
            raise RuntimeError('Scraping falhou.')

        manager = JobManager(run_fn=failing_runner, ttl_hours=24, history_limit=10)
        try:
            job = manager.create({'cpf': '456'}, owner='bob')
            _wait_done(manager, job.id)

            meta_path = job.directory / '_meta.json'
            assert meta_path.exists()

            data = json.loads(meta_path.read_text(encoding='utf-8'))
            assert data['status'] == 'FAILED'
            assert 'Scraping falhou' in data['error']
        finally:
            manager.shutdown()

    def test_meta_json_created_on_cancelled_before_start(self, tmp_path):
        gate = __import__('threading').Event()

        def blocked_runner(job_id, payload, job_dir, on_message, on_progress,
                           cancel_check=None):
            gate.wait(timeout=5)
            return [JobFile(XLSX_NAME, 'xlsx')]

        manager = JobManager(run_fn=blocked_runner, ttl_hours=24, history_limit=10)
        try:
            job1 = manager.create({}, owner='carol')  # este vai bloquear
            job2 = manager.create({}, owner='carol')  # este será cancelado na fila
            time.sleep(0.05)  # garante que job1 começou a executar
            manager.cancel(job2.id)
            gate.set()  # libera job1

            _wait_done(manager, job1.id)
            _wait_done(manager, job2.id)

            meta_path = job2.directory / '_meta.json'
            assert meta_path.exists()

            data = json.loads(meta_path.read_text(encoding='utf-8'))
            assert data['status'] == 'CANCELLED'
            assert data['id'] == job2.id
        finally:
            manager.shutdown()

    def test_meta_json_removed_on_job_deletion(self, tmp_path):
        manager = JobManager(
            run_fn=_make_runner([JobFile(XLSX_NAME, 'xlsx')]),
            ttl_hours=24, history_limit=10,
        )
        try:
            job = manager.create({}, owner='eve')
            _wait_done(manager, job.id)
            assert (job.directory / '_meta.json').exists()

            result = manager.remove(job.id)
            assert result == 'removed'
            assert not job.directory.exists()
        finally:
            manager.shutdown()

    def test_meta_json_removed_on_clear(self, tmp_path):
        manager = JobManager(
            run_fn=_make_runner([JobFile(XLSX_NAME, 'xlsx')]),
            ttl_hours=24, history_limit=10,
        )
        try:
            job = manager.create({}, owner='frank')
            _wait_done(manager, job.id)
            assert (job.directory / '_meta.json').exists()

            removed = manager.clear(owner='frank')
            assert removed == 1
            assert not job.directory.exists()
        finally:
            manager.shutdown()

    def test_meta_json_is_valid_from_meta_input(self, tmp_path):
        manager = JobManager(
            run_fn=_make_runner([JobFile(XLSX_NAME, 'xlsx')]),
            ttl_hours=24, history_limit=10,
        )
        try:
            job = manager.create({'cpf': '789'}, owner='grace')
            _wait_done(manager, job.id)

            raw = json.loads((job.directory / '_meta.json').read_text(encoding='utf-8'))
            restored = Job.from_meta(raw)

            assert restored.id == job.id
            assert restored.owner == 'grace'
            assert restored.status == JobStatus.DONE
            assert restored.payload == {'cpf': '789'}
            assert len(restored.files) == 1
        finally:
            manager.shutdown()


# ---------------------------------------------------------------------------
# Testes de reidratação (_hydrate_from_disk)
# ---------------------------------------------------------------------------


def _make_runner_simple(files, delay=0.02):
    def runner(job_id, payload, job_dir, on_message, on_progress, cancel_check=None):
        time.sleep(delay)
        for record in files:
            (job_dir / record.name).write_bytes(f'content-{record.name}'.encode())
        return list(files)
    return runner


def _wait_done_simple(job_manager, job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = job_manager.get(job_id)
        if job is not None and job.status in (
            JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED
        ):
            return job
        time.sleep(0.02)
    raise AssertionError(f'Job {job_id} não terminou em {timeout}s')


class TestHydration:
    """Verifica que _hydrate_from_disk() reidrata jobs ao criar um novo JobManager."""

    def test_hydrated_jobs_appear_in_new_manager(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        files = [JobFile(XLSX_NAME, 'xlsx')]
        manager1 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            job = manager1.create({'cpf': '111'}, owner='user_a')
            _wait_done_simple(manager1, job.id)
            job_id = job.id
        finally:
            manager1.shutdown()

        # Novo manager: reidrata do disco
        manager2 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            restored = manager2.get(job_id)
            assert restored is not None, 'Job não foi reidratado'
            assert restored.id == job_id
            assert restored.owner == 'user_a'
            assert restored.status == JobStatus.DONE
            assert restored.payload == {'cpf': '111'}
            assert len(restored.files) == 1
        finally:
            manager2.shutdown()

    def test_hydrated_jobs_listable_by_owner(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        files = [JobFile(XLSX_NAME, 'xlsx')]
        manager1 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            j1 = manager1.create({}, owner='alice')
            j2 = manager1.create({}, owner='bob')
            _wait_done_simple(manager1, j1.id)
            _wait_done_simple(manager1, j2.id)
        finally:
            manager1.shutdown()

        manager2 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            alice_jobs = manager2.list(owner='alice')
            bob_jobs = manager2.list(owner='bob')
            assert len(alice_jobs) == 1
            assert len(bob_jobs) == 1
            assert alice_jobs[0].owner == 'alice'
            assert bob_jobs[0].owner == 'bob'
        finally:
            manager2.shutdown()

    def test_hydrated_job_files_downloadable(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        files = [JobFile(XLSX_NAME, 'xlsx')]
        manager1 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            job = manager1.create({}, owner='carol')
            _wait_done_simple(manager1, job.id)
            # Verifica que o arquivo existe no disco
            file_path = job.directory / XLSX_NAME
            assert file_path.exists()
        finally:
            manager1.shutdown()

        manager2 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            restored = manager2.get(job.id)
            assert restored is not None
            # Download do arquivo reidratado
            file_path = restored.directory / XLSX_NAME
            assert file_path.exists()
            assert file_path.read_bytes() == f'content-{XLSX_NAME}'.encode()
        finally:
            manager2.shutdown()

    def test_hydrated_job_deletable(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        files = [JobFile(XLSX_NAME, 'xlsx')]
        manager1 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            job = manager1.create({}, owner='dave')
            _wait_done_simple(manager1, job.id)
        finally:
            manager1.shutdown()

        manager2 = JobManager(
            run_fn=_make_runner_simple(files), ttl_hours=24, history_limit=10)
        try:
            restored = manager2.get(job.id)
            assert restored is not None
            assert restored.directory.exists()

            result = manager2.remove(job.id)
            assert result == 'removed'
            assert manager2.get(job.id) is None
            assert not restored.directory.exists()
        finally:
            manager2.shutdown()

    def test_folder_without_meta_json_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        # Cria uma pasta de job sem _meta.json
        orphan_dir = tmp_path / 'jobs' / 'orphan000'
        orphan_dir.mkdir(parents=True)
        (orphan_dir / 'arquivo.xlsx').write_bytes(b'fake')

        manager = JobManager(
            run_fn=_make_runner_simple([]), ttl_hours=24, history_limit=10)
        try:
            assert manager.count() == 0
            assert manager.get('orphan000') is None
        finally:
            manager.shutdown()

    def test_corrupted_meta_json_ignored(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        bad_dir = tmp_path / 'jobs' / 'bad0000000'
        bad_dir.mkdir(parents=True)
        (bad_dir / '_meta.json').write_text('{invalid json!!!', encoding='utf-8')

        with caplog.at_level('WARNING'):
            manager = JobManager(
                run_fn=_make_runner_simple([]), ttl_hours=24, history_limit=10)
        try:
            assert manager.count() == 0
            assert 'corrompido' in caplog.text
        finally:
            manager.shutdown()

    def test_non_directory_entries_in_jobs_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))

        jobs_dir = tmp_path / 'jobs'
        jobs_dir.mkdir(parents=True)
        (jobs_dir / 'readme.txt').write_text('not a job', encoding='utf-8')

        manager = JobManager(
            run_fn=_make_runner_simple([]), ttl_hours=24, history_limit=10)
        try:
            assert manager.count() == 0
        finally:
            manager.shutdown()

    def test_no_jobs_directory_is_fine(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
        # Não cria a pasta jobs/

        manager = JobManager(
            run_fn=_make_runner_simple([]), ttl_hours=24, history_limit=10)
        try:
            assert manager.count() == 0
        finally:
            manager.shutdown()


# ---------------------------------------------------------------------------
# Testes E2E: cenário de restart via API (TestClient)
# ---------------------------------------------------------------------------

WEB_USER = 'alice'
WEB_PASSWORD = 'secret123'

E2E_PAYLOAD = {
    'cpf': '52998224725',
    'unit': '1',
    'date_start': '01/2024',
    'date_end': '03/2024',
    'excel': True,
    'pdf': True,
}


def _e2e_runner(files, delay=0.02):
    def runner(job_id, payload, job_dir, on_message, on_progress, cancel_check=None):
        time.sleep(delay)
        on_progress(1, 1)
        for record in files:
            (job_dir / record.name).write_bytes(f'content-{record.name}'.encode())
        return list(files)
    return runner


def _e2e_wait_done(job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = main_module.JOB_MANAGER.get(job_id)
        if job is not None and job.status in (
            JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED
        ):
            return job
        time.sleep(0.02)
    raise AssertionError(f'Job {job_id} não terminou em {timeout}s')


def _simulate_restart(tmp_path):
    """Simula restart: cria novo JobManager que reidrata do disco."""
    old = main_module.JOB_MANAGER
    old.shutdown()
    new_manager = JobManager(
        run_fn=_e2e_runner([JobFile(XLSX_NAME, 'xlsx')]),
        ttl_hours=24, history_limit=10,
    )
    main_module.JOB_MANAGER = new_manager
    return new_manager


class TestRestartE2E:
    """Cenário completo: API → jobs no disco → restart → histórico reidratado."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
        monkeypatch.setenv('WEB_USERS', f'{WEB_USER}:{WEB_PASSWORD}')
        monkeypatch.setenv('SESSION_SECRET', 'test-secret')
        reset_rate_limit()
        reset_job_rate_limit()
        manager = JobManager(
            run_fn=_e2e_runner([JobFile(XLSX_NAME, 'xlsx')]),
            ttl_hours=24, history_limit=10,
        )
        main_module.JOB_MANAGER = manager
        yield
        main_module.JOB_MANAGER.shutdown()

    def _client(self):
        c = TestClient(main_module.app)
        res = c.post('/api/v1/auth/login',
                     json={'username': WEB_USER, 'password': WEB_PASSWORD})
        assert res.status_code == 200
        return c

    def test_restart_restores_history_via_api(self, tmp_path):
        client = self._client()

        # Cria e conclui 2 jobs via API
        res1 = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        assert res1.status_code == 202
        job1_id = res1.json()['job']['id']
        _e2e_wait_done(job1_id)

        res2 = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        assert res2.status_code == 202
        job2_id = res2.json()['job']['id']
        _e2e_wait_done(job2_id)

        # Histórico antes do restart
        history_before = client.get('/api/v1/jobs').json()
        assert history_before['count'] == 2

        # Simula restart
        _simulate_restart(tmp_path)

        # Histórico após restart (nova instância do client para sessão limpa)
        client2 = self._client()
        history_after = client2.get('/api/v1/jobs').json()
        assert history_after['count'] == 2
        ids_after = {j['id'] for j in history_after['jobs']}
        assert job1_id in ids_after
        assert job2_id in ids_after

    def test_restart_preserves_owner(self, tmp_path):
        client = self._client()

        res = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        job_id = res.json()['job']['id']
        _e2e_wait_done(job_id)

        _simulate_restart(tmp_path)

        client2 = self._client()
        job_data = client2.get(f'/api/v1/jobs/{job_id}').json()
        assert job_data['ok'] is True
        assert job_data['job']['owner'] == WEB_USER

    def test_restart_download_works(self, tmp_path):
        client = self._client()

        res = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        job_id = res.json()['job']['id']
        _e2e_wait_done(job_id)

        _simulate_restart(tmp_path)

        client2 = self._client()
        dl = client2.get(f'/api/v1/jobs/{job_id}/download?format=xlsx')
        assert dl.status_code == 200
        assert dl.content == f'content-{XLSX_NAME}'.encode()

    def test_restart_delete_removes_meta(self, tmp_path):
        client = self._client()

        res = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        job_id = res.json()['job']['id']
        _e2e_wait_done(job_id)

        # Verifica _meta.json existe antes do restart
        job = main_module.JOB_MANAGER.get(job_id)
        assert (job.directory / '_meta.json').exists()

        _simulate_restart(tmp_path)

        client2 = self._client()
        dl = client2.delete(f'/api/v1/jobs/{job_id}')
        assert dl.status_code == 200
        assert dl.json()['ok'] is True

        # Pasta + _meta.json removidos
        restored = main_module.JOB_MANAGER.get(job_id)
        assert restored is None

    def test_restart_clear_removes_all(self, tmp_path):
        client = self._client()

        for _ in range(3):
            res = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
            _e2e_wait_done(res.json()['job']['id'])

        _simulate_restart(tmp_path)

        client2 = self._client()
        assert client2.get('/api/v1/jobs').json()['count'] == 3

        clear_res = client2.delete('/api/v1/jobs')
        assert clear_res.json()['removed'] == 3
        assert client2.get('/api/v1/jobs').json()['count'] == 0

    def test_restart_other_users_isolated(self, tmp_path):
        """Jobs de outro usuário não aparecem na reidratação do usuário atual."""
        client = self._client()

        res = client.post('/api/v1/jobs', json=E2E_PAYLOAD)
        _e2e_wait_done(res.json()['job']['id'])

        # Cria um job manualmente com owner diferente via manager direto
        other_manager = main_module.JOB_MANAGER
        other_job = other_manager.create(E2E_PAYLOAD, owner='bob')
        _e2e_wait_done(other_job.id)

        _simulate_restart(tmp_path)

        client2 = self._client()
        history = client2.get('/api/v1/jobs').json()
        # Só os jobs da alice aparecem
        assert all(j['owner'] == WEB_USER for j in history['jobs'])
