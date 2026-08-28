"""Testes da autenticação web (FASE 4) usando TestClient.

Cobre: login ok/erro, usuários não configurados, /me com e sem sessão,
logout e rate-limit por IP no login. JWT Spring Boot (auth dual).
"""
import hashlib
import json
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
# Testes de JWT Spring Boot (auth dual)
# ---------------------------------------------------------------------------


_jwt_port_counter = 19900  # porta base única por teste


def _make_valid_jwt(monkeypatch):
    """Gera um JWT válido usando chave RSA mockada e configura o JWKS."""
    import base64
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt as pyjwt

    # Porta única por chamada para evitar conflito de cache do PyJWKClient
    global _jwt_port_counter
    _jwt_port_counter += 1
    port = _jwt_port_counter

    # Limpa cache do PyJWKClient
    auth_mod._jwk_client_cache['client'] = None
    auth_mod._jwk_client_cache['url'] = ''

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = private_key.public_key().public_numbers()

    def _int_to_b64url(n, byte_len):
        return base64.urlsafe_b64encode(
            n.to_bytes(byte_len, 'big')).rstrip(b'=').decode()

    jwk = {
        'kty': 'RSA', 'kid': 'test-key', 'use': 'sig', 'alg': 'RS256',
        'n': _int_to_b64url(pub.n, 256),
        'e': _int_to_b64url(pub.e, 3),
    }
    jwks = {'keys': [jwk]}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(jwks).encode())
        def log_message(self, *a):
            pass

    # Porta fixa para evitar conflito
    server = HTTPServer(('127.0.0.1', port), _Handler)
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    monkeypatch.setenv('SPRING_JWKS_URL', f'http://127.0.0.1:{port}/.well-known/jwks.json')
    monkeypatch.delenv('SPRING_JWT_ISSUER', raising=False)

    # Limpa cache do PyJWKClient
    auth_mod._jwk_client_cache['client'] = None
    auth_mod._jwk_client_cache['url'] = ''

    token = pyjwt.encode(
        {'sub': 'admin', 'exp': int(time.time()) + 3600},
        private_key, algorithm='RS256', headers={'kid': 'test-key'},
    )

    token_expired = pyjwt.encode(
        {'sub': 'admin', 'exp': int(time.time()) - 1},
        private_key, algorithm='RS256', headers={'kid': 'test-key'},
    )

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token_bad_sig = pyjwt.encode(
        {'sub': 'hacker', 'exp': int(time.time()) + 3600},
        other_key, algorithm='RS256', headers={'kid': 'test-key'},
    )

    return {
        'token': token,
        'token_expired': token_expired,
        'token_bad_sig': token_bad_sig,
        'server': server,
    }


class TestJWTAuth:
    """Testes de autenticação via JWT Bearer (Spring Boot)."""

    def test_valid_jwt_accesses_me(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {jwt_data["token"]}'})
            assert res.status_code == 200
            assert res.json()['user'] == 'admin'
        finally:
            jwt_data['server'].shutdown()

    def test_expired_jwt_returns_401(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {jwt_data["token_expired"]}'})
            assert res.status_code == 401
        finally:
            jwt_data['server'].shutdown()

    def test_bad_signature_returns_401(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {jwt_data["token_bad_sig"]}'})
            assert res.status_code == 401
        finally:
            jwt_data['server'].shutdown()

    def test_malformed_token_returns_401(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': 'Bearer not.a.jwt'})
            assert res.status_code == 401
        finally:
            jwt_data['server'].shutdown()

    def test_cookie_still_works_with_jwt_configured(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            # Login via cookie (fluxo Python frontend)
            client.post('/api/v1/auth/login',
                        json={'username': 'alice', 'password': 'secret123'})
            res = client.get('/api/v1/auth/me')
            assert res.status_code == 200
            assert res.json()['user'] == 'alice'
        finally:
            jwt_data['server'].shutdown()

    def test_jwt_preferred_over_cookie(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            # Login via cookie como bob
            client.post('/api/v1/auth/login',
                        json={'username': 'bob', 'password': 'secret321'})
            # JWT diz 'admin' — deve prevalecer
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {jwt_data["token"]}'})
            assert res.status_code == 200
            assert res.json()['user'] == 'admin'
        finally:
            jwt_data['server'].shutdown()

    def test_fallback_to_cookie_when_jwt_invalid(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            # Login via cookie como alice
            client.post('/api/v1/auth/login',
                        json={'username': 'alice', 'password': 'secret123'})
            # JWT inválido — deve usar cookie
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': f'Bearer {jwt_data["token_bad_sig"]}'})
            assert res.status_code == 200
            assert res.json()['user'] == 'alice'
        finally:
            jwt_data['server'].shutdown()

    def test_no_auth_returns_401(self, client, monkeypatch):
        _make_valid_jwt(monkeypatch)  # configura JWKS
        res = client.get('/api/v1/auth/me')
        assert res.status_code == 401

    def test_bearer_without_token_returns_401(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            res = client.get('/api/v1/auth/me',
                             headers={'Authorization': 'Bearer '})
            assert res.status_code == 401
        finally:
            jwt_data['server'].shutdown()

    def test_no_jwks_configured_skips_jwt(self, client, monkeypatch):
        """Sem SPRING_JWKS_URL, JWT é ignorado e cookie é único mecanismo."""
        monkeypatch.delenv('SPRING_JWKS_URL', raising=False)
        auth_mod._jwk_client_cache['client'] = None
        auth_mod._jwk_client_cache['url'] = ''

        res = client.get('/api/v1/auth/me',
                         headers={'Authorization': 'Bearer anything'})
        assert res.status_code == 401

    def test_jobs_require_auth_with_jwt(self, client, monkeypatch):
        jwt_data = _make_valid_jwt(monkeypatch)
        try:
            # GET /jobs com JWT válido
            res = client.get('/api/v1/jobs',
                             headers={'Authorization': f'Bearer {jwt_data["token"]}'})
            assert res.status_code == 200
        finally:
            jwt_data['server'].shutdown()