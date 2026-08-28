"""Testes da autenticação web (FASE 4) usando TestClient.

Cobre: login ok/erro, usuários não configurados, /me com e sem sessão,
logout e rate-limit por IP no login. JWT Spring Boot (auth dual — HMAC256).
"""
import hashlib
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import auth as auth_mod
from backend.app import main
from backend.app.auth import (
    _LOGIN_ATTEMPTS,
    _JOB_CREATIONS,
    _purge_expired_records,
    job_creation_allowed,
    login_allowed,
    reset_job_rate_limit,
    reset_rate_limit,
)

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


class TestSessionCookieSecure:
    """MEL-07: cookie de sessão com atributo Secure configurável."""

    def test_cookie_sem_secure_por_padrao(self, monkeypatch, tmp_path):
        monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
        monkeypatch.setenv('WEB_USERS', WEB_USERS)
        monkeypatch.setenv('SESSION_SECRET', 'test-secret')
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
        reset_rate_limit()
        client = TestClient(main.app)

        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'secret123'})
        set_cookie = res.headers.get('set-cookie', '')
        assert res.status_code == 200
        assert 'secure' not in set_cookie.lower()

    def test_cookie_secure_quando_env_ativa(self, monkeypatch, tmp_path):
        monkeypatch.setenv('SESSION_COOKIE_SECURE', 'true')
        monkeypatch.setenv('WEB_USERS', WEB_USERS)
        monkeypatch.setenv('SESSION_SECRET', 'test-secret')
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
        reset_rate_limit()
        client = TestClient(main.app)

        res = client.post('/api/v1/auth/login',
                          json={'username': 'alice', 'password': 'secret123'})
        set_cookie = res.headers.get('set-cookie', '')
        assert res.status_code == 200
        assert 'secure' in set_cookie.lower()
        assert 'httponly' in set_cookie.lower()


class TestSessionSecretHardening:
    """MEL-08: sem SESSION_SECRET, o segredo é efêmero (nunca determinístico)."""

    def test_secret_efemerox_sem_fallback_deterministico(self, monkeypatch, caplog):
        monkeypatch.delenv('SESSION_SECRET', raising=False)
        monkeypatch.setenv('USER', 'portal_user')
        monkeypatch.setenv('URL_BASE', 'https://portal.example')
        monkeypatch.setattr(auth_mod, '_warned_ephemeral', False)

        import logging
        with caplog.at_level(logging.WARNING, logger='backend.app.auth'):
            secret = auth_mod._secret()

        # Nunca deve derivar de USER/URL_BASE (antigo fallback previsível)
        old_fallback = hashlib.sha256(
            'portal_user|https://portal.example'.encode()).digest()
        assert secret != old_fallback
        assert secret == auth_mod._EPHEMERAL_SECRET
        assert any('SESSION_SECRET não configurado' in r.message
                   for r in caplog.records)

    def test_token_efemerox_roundtrip(self, monkeypatch):
        monkeypatch.delenv('SESSION_SECRET', raising=False)
        token = auth_mod.make_session_token('alice')
        assert auth_mod.read_session_token(token) == 'alice'

    def test_secret_explicito_prioritario(self, monkeypatch):
        monkeypatch.setenv('SESSION_SECRET', 'chave-fixa')
        expected = hashlib.sha256(b'chave-fixa').digest()
        assert auth_mod._secret() == expected


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


class TestRateLimitPurge:
    """MEL-03: purga automática de entradas expiradas nos dicionários de rate-limit."""

    def test_purge_removes_only_expired_records(self):
        now = time.time()
        records = {
            'expired': [now - 120, 1],
            'fresh': [now, 1],
        }
        removed = _purge_expired_records(records, 60, now)
        assert removed == 1
        assert 'expired' not in records
        assert 'fresh' in records

    def test_login_allowed_purges_expired_at_threshold(self, monkeypatch):
        reset_rate_limit()
        now = time.time()
        monkeypatch.setattr('backend.app.auth._RATE_PURGE_THRESHOLD', 2)
        _LOGIN_ATTEMPTS['expired_ip'] = [now - 120, 1]
        _LOGIN_ATTEMPTS['recent_ip'] = [now, 1]
        login_allowed('novo_ip')
        assert 'expired_ip' not in _LOGIN_ATTEMPTS
        assert 'recent_ip' in _LOGIN_ATTEMPTS
        assert 'novo_ip' in _LOGIN_ATTEMPTS

    def test_job_creation_purges_expired_at_threshold(self, monkeypatch):
        reset_job_rate_limit()
        now = time.time()
        monkeypatch.setattr('backend.app.auth._RATE_PURGE_THRESHOLD', 2)
        _JOB_CREATIONS['expired_user|ip1'] = [now - 120, 1]
        _JOB_CREATIONS['recent_user|ip2'] = [now, 1]
        job_creation_allowed('ip3', 'novo_user')
        assert 'expired_user|ip1' not in _JOB_CREATIONS
        assert 'recent_user|ip2' in _JOB_CREATIONS
        assert 'novo_user|ip3' in _JOB_CREATIONS


# ---------------------------------------------------------------------------
# Testes de JWT Spring Boot (auth dual — HMAC256)
# ---------------------------------------------------------------------------

JWT_TEST_SECRET = 'test-hmac-secret-key-for-unit-tests'


def _make_jwt_tokens(secret: str = JWT_TEST_SECRET):
    """Gera tokens JWT HMAC para testes (sem servidor HTTP, sem RSA)."""
    import jwt as pyjwt

    now = int(time.time())
    token = pyjwt.encode(
        {'sub': 'admin', 'exp': now + 3600, 'iss': 'API Cad PGM'},
        secret, algorithm='HS256',
    )
    token_expired = pyjwt.encode(
        {'sub': 'admin', 'exp': now - 1, 'iss': 'API Cad PGM'},
        secret, algorithm='HS256',
    )
    token_bad_sig = pyjwt.encode(
        {'sub': 'hacker', 'exp': now + 3600, 'iss': 'API Cad PGM'},
        'wrong-secret', algorithm='HS256',
    )
    return {
        'token': token,
        'token_expired': token_expired,
        'token_bad_sig': token_bad_sig,
    }


@pytest.fixture
def jwt_client(monkeypatch, tmp_path):
    """Client com JWT_SECRET configurado para testes de auth dual."""
    monkeypatch.setenv('WEB_USERS', WEB_USERS)
    monkeypatch.setenv('SESSION_SECRET', 'test-secret')
    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('JWT_SECRET', JWT_TEST_SECRET)
    reset_rate_limit()
    return TestClient(main.app)


class TestJWTAuth:
    """Testes de autenticação via JWT Bearer HMAC256 (Spring Boot)."""

    def test_valid_jwt_accesses_me(self, jwt_client):
        tokens = _make_jwt_tokens()
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {tokens["token"]}'})
        assert res.status_code == 200
        assert res.json()['user'] == 'admin'

    def test_expired_jwt_returns_401(self, jwt_client):
        tokens = _make_jwt_tokens()
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {tokens["token_expired"]}'})
        assert res.status_code == 401

    def test_bad_signature_returns_401(self, jwt_client):
        tokens = _make_jwt_tokens()
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {tokens["token_bad_sig"]}'})
        assert res.status_code == 401

    def test_malformed_token_returns_401(self, jwt_client):
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': 'Bearer not.a.jwt'})
        assert res.status_code == 401

    def test_cookie_still_works_with_jwt_configured(self, jwt_client):
        jwt_client.post('/api/v1/auth/login',
                        json={'username': 'alice', 'password': 'secret123'})
        res = jwt_client.get('/api/v1/auth/me')
        assert res.status_code == 200
        assert res.json()['user'] == 'alice'

    def test_jwt_preferred_over_cookie(self, jwt_client):
        tokens = _make_jwt_tokens()
        jwt_client.post('/api/v1/auth/login',
                        json={'username': 'bob', 'password': 'secret321'})
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {tokens["token"]}'})
        assert res.status_code == 200
        assert res.json()['user'] == 'admin'

    def test_fallback_to_cookie_when_jwt_invalid(self, jwt_client):
        tokens = _make_jwt_tokens()
        jwt_client.post('/api/v1/auth/login',
                        json={'username': 'alice', 'password': 'secret123'})
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {tokens["token_bad_sig"]}'})
        assert res.status_code == 200
        assert res.json()['user'] == 'alice'

    def test_no_auth_returns_401(self, jwt_client):
        res = jwt_client.get('/api/v1/auth/me')
        assert res.status_code == 401

    def test_bearer_without_token_returns_401(self, jwt_client):
        res = jwt_client.get('/api/v1/auth/me',
                             headers={'Authorization': 'Bearer '})
        assert res.status_code == 401

    def test_no_jwt_secret_skips_jwt(self, monkeypatch, tmp_path):
        """Sem JWT_SECRET, JWT é ignorado e cookie é único mecanismo."""
        monkeypatch.setenv('WEB_USERS', WEB_USERS)
        monkeypatch.setenv('SESSION_SECRET', 'test-secret')
        monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
        monkeypatch.delenv('JWT_SECRET', raising=False)
        reset_rate_limit()
        client = TestClient(main.app)

        res = client.get('/api/v1/auth/me',
                         headers={'Authorization': 'Bearer anything'})
        assert res.status_code == 401

    def test_jobs_require_auth_with_jwt(self, jwt_client):
        tokens = _make_jwt_tokens()
        res = jwt_client.get('/api/v1/jobs',
                             headers={'Authorization': f'Bearer {tokens["token"]}'})
        assert res.status_code == 200