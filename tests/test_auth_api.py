"""Testes da autenticação web (FASE 4) usando TestClient.

Cobre: login ok/erro, usuários não configurados, /me com e sem sessão,
logout e rate-limit por IP no login.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.auth import reset_rate_limit

WEB_USERS = 'alice:secret123,bob:secret321'


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('WEB_USERS', WEB_USERS)
    monkeypatch.setenv('SESSION_SECRET', 'test-secret')
    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    reset_rate_limit()
    return TestClient(main.app)


class TestLogin:

    def test_login_success_sets_cookie(self, client):
        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'secret123'})
        assert res.status_code == 200
        data = res.json()
        assert data['ok'] is True
        assert data['user'] == 'alice'
        assert 'ponto_session' in res.cookies

    def test_login_wrong_password_401(self, client):
        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'errada'})
        assert res.status_code == 401
        assert res.json()['ok'] is False

    def test_login_unknown_user_401(self, client):
        res = client.post('/api/v1/auth/login',
                          json={'username': 'ze', 'password': 'x'})
        assert res.status_code == 401

    def test_login_no_users_configured_500(self, monkeypatch, client):
        monkeypatch.setenv('WEB_USERS', '')
        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'secret123'})
        assert res.status_code == 500

    def test_login_after_rate_limit_429(self, client):
        for _ in range(8):
            client.post('/api/v1/auth/login',
                        json={'username': 'alice', 'password': 'errada'})
        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'secret123'})
        assert res.status_code == 429


class TestSession:

    def test_me_without_session_401(self, client):
        res = client.get('/api/v1/auth/me')
        assert res.status_code == 401

    def test_jobs_require_session(self, client):
        res = client.get('/api/v1/jobs')
        assert res.status_code == 401

    def test_me_with_session(self, client):
        client.post('/api/v1/auth/login',
                    json={'username': 'bob', 'password': 'secret321'})
        res = client.get('/api/v1/auth/me')
        assert res.status_code == 200
        assert res.json()['user'] == 'bob'

    def test_logout_invalidates_session(self, client):
        client.post('/api/v1/auth/login',
                    json={'username': 'alice', 'password': 'secret123'})
        res = client.post('/api/v1/auth/logout')
        assert res.status_code == 200
        assert client.get('/api/v1/auth/me').status_code == 401

    def test_tampered_cookie_rejected(self, client):
        client.post('/api/v1/auth/login',
                    json={'username': 'alice', 'password': 'secret123'})
        token = client.cookies.get('ponto_session')
        client.cookies.set('ponto_session', token + '0')
        assert client.get('/api/v1/auth/me').status_code == 401