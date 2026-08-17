"""Autenticação de usuários da aplicação web (FASE 4).

- Contas locais provisionadas via .env (WEB_USERS, formato
  "user1:senha1,user2:senha2"); as senhas são conferidas por hash
  PBKDF2 (nunca armazenadas nem transmitidas em claro).
- Sessão por cookie assinado (HMAC-SHA256) com flag HttpOnly/SameSite=Lax.
  O SSE (EventSource) não envia header Authorization, mas envia cookies —
  por isso o cookie é o mecanismo de transporte da sessão.
- Rate-limit simples por IP nas tentativas de login.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from backend.core.settings import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE = 'ponto_session'

PBKDF2_ITERATIONS = 200_000

# Rate-limit do login: ip -> [início da janela, tentativas]
_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
_LOGIN_LIMIT = 8
_LOGIN_WINDOW_SECONDS = 60


# ---------------------------------------------------------------------------
# Senhas (PBKDF2)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash PBKDF2-SHA256 no formato 'pbkdf2$iter$salt_hex$hash_hex'."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    return f'pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    """Compara uma senha em claro com o hash armazenado (tempo constante)."""
    try:
        _, iters, salt_hex, hash_hex = stored.split('$')
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac(
            'sha256', password.encode(), salt, int(iters))
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def _users() -> Dict[str, str]:
    """dict nome -> hash da senha (materializado a cada chamada, testável)."""
    return {name: hash_password(pwd) for name, pwd in settings.web_users.items()}


def authenticate_user(username: str, password: str) -> bool:
    """True se as credenciais conferem com uma conta configurada."""
    stored = _users().get(username or '')
    return bool(stored) and verify_password(password or '', stored)


# ---------------------------------------------------------------------------
# Cookie de sessão assinado (HMAC-SHA256)
# ---------------------------------------------------------------------------


def _secret() -> bytes:
    """Segredo de assinatura. Deriva do segredo explícito (SESSION_SECRET)
    ou, na ausência dele, de credenciais estáveis da instalação."""
    secret = settings.session_secret or (settings.user + '|' + settings.url_base)
    return hashlib.sha256(secret.encode()).digest()


def make_session_token(username: str) -> str:
    """Gera o valor do cookie de sessão: payload base64url . assinatura."""
    payload = {
        'u': username,
        'exp': int(time.time()) + settings.session_ttl_hours * 3600,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()).rstrip(b'=').decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f'{body}.{sig}'


def read_session_token(raw: str) -> Optional[str]:
    """Valida a assinatura/expiração e devolve o nome do usuário (ou None)."""
    if not raw:
        return None
    try:
        body, sig = raw.split('.')
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(
            base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if int(payload.get('exp', 0)) < time.time():
            return None
        return payload.get('u') or None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def get_current_user(request: Request) -> str:
    """Usuário autenticado da request; 401 se não houver sessão válida."""
    user = read_session_token(request.cookies.get(SESSION_COOKIE, ''))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Sessão inválida ou expirada.',
        )
    return user


# ---------------------------------------------------------------------------
# Rate-limit do login
# ---------------------------------------------------------------------------


def client_ip(request: Request) -> str:
    """IP do cliente, respeitando X-Forwarded-For quando atrás de proxy."""
    forwarded = request.headers.get('x-forwarded-for', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'


def login_allowed(ip: str) -> bool:
    """True se o IP ainda pode tentar novo login (janela de tentativas)."""
    now = time.time()
    record = _LOGIN_ATTEMPTS.get(ip)
    if record is None or now - record[0] > _LOGIN_WINDOW_SECONDS:
        _LOGIN_ATTEMPTS[ip] = [now, 1]
    else:
        record[1] += 1
    return _LOGIN_ATTEMPTS[ip][1] <= _LOGIN_LIMIT


def reset_rate_limit() -> None:
    """Zera as contagens de tentativas (usado em testes)."""
    _LOGIN_ATTEMPTS.clear()