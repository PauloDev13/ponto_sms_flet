"""Testes de isolamento entre usuários (FASE 4).

Dois usuários ('alice' e 'bob') usam a MESMA API/JobManager e comprovam
que cada um só enxerga, baixa, cancela e exclui as PRÓPRIAS gerações:
- B não lista/downloada/deleta/cancela os jobs de A (403);
- limpar histórico de A não afeta o de B;
- o SSE de um job de A é negado para B.
"""
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.auth import reset_rate_limit
from backend.core.job import JobFile, JobManager

XLSX_NAME = 'MARIA SOUZA - CPF_529.982.247-25.xlsx'

ALICE = 'alice'
ALICE_PWD = 'secret123'
BOB = 'bob'
BOB_PWD = 'secret321'

VALID_PAYLOAD = {
    'cpf': '52998224725',
    'unit': '1',
    'date_start': '01/2024',
    'date_end': '03/2024',
    'excel': True,
    'pdf': True,
}


def make_runner(files, delay=0.1):
    def runner(job_id, payload, job_dir, on_message, on_progress, cancel_check=None):
        time.sleep(delay)
        on_message('Coletando...')
        for record in files:
            (job_dir / record.name).write_bytes(f'content-{record.name}'.encode())
        return list(files)
    return runner


@pytest.fixture
def two_clients(monkeypatch, tmp_path):
    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('WEB_USERS', f'{ALICE}:{ALICE_PWD},{BOB}:{BOB_PWD}')
    monkeypatch.setenv('SESSION_SECRET', 'test-secret')
    reset_rate_limit()

    manager = JobManager(
        run_fn=make_runner([JobFile(XLSX_NAME, 'xlsx')]),
        ttl_hours=24,
        history_limit=5,
    )
    main_module.JOB_MANAGER = manager

    def logged(username, password):
        c = TestClient(main_module.app)
        res = c.post('/api/v1/auth/login', json={'username': username, 'password': password})
        assert res.status_code == 200, res.text
        return c

    yield logged(ALICE, ALICE_PWD), logged(BOB, BOB_PWD)
    manager.shutdown()


def wait_done(client, job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = main_module.JOB_MANAGER.get(job_id)
        assert job is not None
        if job.status.value in ('DONE', 'FAILED', 'CANCELLED'):
            return job.to_dict()
        time.sleep(0.05)
    raise AssertionError(f'Job {job_id} não terminou')


def create_done(client, payload=None):
    job_id = client.post('/api/v1/jobs', json=payload or VALID_PAYLOAD).json()['job']['id']
    wait_done(client, job_id)
    return job_id


class TestIsolation:

    def test_list_history_scoped_by_user(self, two_clients):
        alice, bob = two_clients
        create_done(alice)

        assert len(alice.get('/api/v1/jobs').json()['jobs']) == 1
        assert bob.get('/api/v1/jobs').json()['jobs'] == []

    def test_bob_cannot_read_other_users_job(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)

        res = bob.get(f'/api/v1/jobs/{a_job}')
        assert res.status_code == 403

    def test_bob_cannot_download_other_users_job(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)

        assert bob.get(f'/api/v1/jobs/{a_job}/download?format=xlsx').status_code == 403
        assert bob.get(f'/api/v1/jobs/{a_job}/files/{XLSX_NAME}').status_code == 403

    def test_bob_cannot_delete_other_users_job(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)

        assert bob.delete(f'/api/v1/jobs/{a_job}').status_code == 403
        assert alice.get(f'/api/v1/jobs/{a_job}').json()['job']['id'] == a_job  # ainda existe

    def test_bob_cannot_cancel_other_users_job(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)
        # job DONE: mesmo que fosse permitido, cancel daria 409; o 403 vem antes
        assert bob.post(f'/api/v1/jobs/{a_job}/cancel').status_code == 403

    def test_bob_cannot_see_other_users_sse(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)

        res = bob.get(f'/api/v1/jobs/{a_job}/events')
        assert res.status_code == 403

    def test_clear_history_keeps_others_users_jobs(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)
        b_job = create_done(bob)

        res = alice.delete('/api/v1/jobs')
        assert res.json()['removed'] == 1
        assert alice.get('/api/v1/jobs').json()['jobs'] == []
        assert bob.get(f'/api/v1/jobs/{b_job}').status_code == 200

        res = bob.delete('/api/v1/jobs')
        assert res.json()['removed'] == 1
        assert bob.get(f'/api/v1/jobs/{b_job}').status_code == 404

    def test_owner_metadata_recorded(self, two_clients):
        alice, bob = two_clients
        a_job = create_done(alice)
        b_job = create_done(bob)

        assert main_module.JOB_MANAGER.get(a_job).owner == ALICE
        assert main_module.JOB_MANAGER.get(b_job).owner == BOB