"""Autenticação de usuários da aplicação web (FASE 4).

- Contas locais provisionadas via .env (WEB_USERS, formato
  "user1:senha1,user2:senha2"); as senhas são conferidas por hash
  PBKDF2 (nunca armazenadas nem transmitidas em claro).
- Sessão por cookie assinado (HMAC-SHA256) com flag HttpOnly/SameSite=Lax.
  O SSE (EventSource) não envia header Authorization, mas envia cookies —
  por isso o cookie é o mecanismo de transporte da sessão.
- JWT Bearer via HMAC256 (Spring Boot): mecanismo alternativo para auth
  federada via Angular. Valida assinatura HMAC contra JWT_SECRET
  compartilhado entre Python e Java backends.
- Rate-limit simples por IP nas tentativas de login.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time

from fastapi import HTTPException, Request, status

from backend.core.settings import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE = 'ponto_session'

PBKDF2_ITERATIONS = 200_000

# Segredo criptográfico efêmero usado quando SESSION_SECRET não está no .env.
# Gerado na inicialização do processo: impede qualquer falsificação
# determinística de token e invalida sessões antigas a cada reinício.
_EPHEMERAL_SECRET = secrets.token_bytes(32)
_warned_ephemeral = False

# Rate-limit do login: ip -> [início da janela, tentativas]
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_LIMIT = 8
_LOGIN_WINDOW_SECONDS = 60

# Rate-limit da criação de jobs: "usuário|ip" -> [início da janela, criações]
_JOB_CREATIONS: dict[str, list[float]] = {}
_JOB_CREATE_LIMIT = 10
_JOB_CREATE_WINDOW_SECONDS = 60
# Quantos jobs ativos (fila + execução) cada usuário pode ter simultaneamente
JOB_MAX_ACTIVE = 3

# Sincronização das mutações dos dicionários de rate-limit e limiar de quitação:
# quando o volume de chaves ultrapassa _RATE_PURGE_THRESHOLD, registros com
# timestamp fora da janela são expurgados — evita vazamento gradual de RAM.
_RATE_LOCK = threading.Lock()
_RATE_PURGE_THRESHOLD = 500


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


def _users() -> dict[str, str]:
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
    """Segredo de assinatura do cookie de sessão (HMAC-SHA256).

    Usa SESSION_SECRET do .env quando presente. NUNCA recorre a um fallback
    determinístico (ex.: USER/URL_BASE) — se a variável estiver vazia, gera
    um segredo criptográfico EFÊMERO em memória (secrets.token_bytes(32)) e
    registra aviso explícito no log. Sessões assinadas com o segredo efêmero
    são invalidadas na reinicialização do processo, o que impede a
    falsificação determinística de tokens por quem conheça o ambiente.
    """
    global _warned_ephemeral
    secret = (settings.session_secret or '').strip()
    if not secret:
        if not _warned_ephemeral:
            logger.warning(
                'SESSION_SECRET não configurado no .env! '
                'Utilizando segredo efêmero em memória — sessões serão '
                'invalidadas a cada reinício do serviço. '
                'Gere uma chave fixa: python -c "import secrets; '
                'print(secrets.token_urlsafe(32))"')
            _warned_ephemeral = True
        return _EPHEMERAL_SECRET
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


def read_session_token(raw: str) -> str | None:
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


# ---------------------------------------------------------------------------
# JWT Spring Boot (HMAC256, segredo compartilhado)
# ---------------------------------------------------------------------------

import jwt as _jwt


def validate_spring_jwt(token: str) -> str | None:
    """Valida JWT HMAC256 do Spring Boot usando segredo compartilhado.

    Retorna o username (claim 'sub') se o token for válido, ou None
    caso contrário. Validações aplicadas:
    - Assinatura HMAC256 contra JWT_SECRET compartilhado
    - Expiração (exp)
    - Issuer ('API Cad PGM')

    Cadeia de chamada defensiva: qualquer exceção resulta em None.
    """
    if not token:
        return None

    secret = settings.jwt_secret
    if not secret:
        return None

    try:
        payload = _jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            issuer='API Cad PGM',
        )
        return payload.get('sub')

    except _jwt.ExpiredSignatureError:
        logger.debug('JWT Spring Boot expirado')
        return None
    except _jwt.InvalidSignatureError:
        logger.warning('JWT Spring Boot com assinatura inválida')
        return None
    except _jwt.InvalidTokenError:
        logger.debug('JWT Spring Boot inválido')
        return None
    except Exception:
        logger.debug('Erro inesperado validando JWT Spring Boot', exc_info=True)
        return None


def get_current_user(request: Request) -> str:
    """Usuário autenticado da request; 401 se não houver sessão válida.

    Mecanismos suportados (em ordem de precedência):
    1. JWT Bearer no header Authorization (Angular via Spring Boot)
    2. Cookie de sessão ponto_session (Python frontend)
    """
    # 1. Tenta JWT Bearer (Angular via Spring Boot)
    auth_header = request.headers.get('authorization', '')
    if auth_header.lower().startswith('bearer '):
        jwt_token = auth_header[7:]
        username = validate_spring_jwt(jwt_token)
        if username:
            return username

    # 2. Fallback para cookie (Python frontend)
    user = read_session_token(request.cookies.get(SESSION_COOKIE, ''))
    if user:
        return user

    # 3. Nenhum mecanismo válido
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Sessão inválida ou expirada.',
    )


# ---------------------------------------------------------------------------
# Rate-limit do login
# ---------------------------------------------------------------------------


def client_ip(request: Request) -> str:
    """IP do cliente, respeitando X-Forwarded-For quando atrás de proxy."""
    forwarded = request.headers.get('x-forwarded-for', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'


def _purge_expired_records(
        records: dict[str, list[float]], window_seconds: float, now: float) -> int:
    """Remove registros fora da janela temporal (previne vazamento de memória).

    Deve ser chamada sob _RATE_LOCK quando o volume de entradas ultrapassar o
    limiar (ou diretamente em testes). Retorna a quantidade de registros
    removidos.
    """
    expired = [
        key for key, (started, _count) in records.items()
        if now - started > window_seconds
    ]
    for key in expired:
        del records[key]
    return len(expired)


def login_allowed(ip: str) -> bool:
    """True se o IP ainda pode tentar novo login (janela de tentativas)."""
    now = time.time()
    with _RATE_LOCK:
        if len(_LOGIN_ATTEMPTS) >= _RATE_PURGE_THRESHOLD:
            _purge_expired_records(_LOGIN_ATTEMPTS, _LOGIN_WINDOW_SECONDS, now)
        record = _LOGIN_ATTEMPTS.get(ip)
        if record is None or now - record[0] > _LOGIN_WINDOW_SECONDS:
            _LOGIN_ATTEMPTS[ip] = [now, 1]
        else:
            record[1] += 1
        return _LOGIN_ATTEMPTS[ip][1] <= _LOGIN_LIMIT


def reset_rate_limit() -> None:
    """Zera as contagens de tentativas (usado em testes)."""
    with _RATE_LOCK:
        _LOGIN_ATTEMPTS.clear()


# ---------------------------------------------------------------------------
# Rate-limit da criação de jobs
# ---------------------------------------------------------------------------


def job_creation_allowed(ip: str, username: str) -> bool:
    """True se usuário+IP ainda pode criar jobs na janela (N por minuto)."""
    key = f'{username}|{ip}'
    now = time.time()
    with _RATE_LOCK:
        if len(_JOB_CREATIONS) >= _RATE_PURGE_THRESHOLD:
            _purge_expired_records(_JOB_CREATIONS, _JOB_CREATE_WINDOW_SECONDS, now)
        record = _JOB_CREATIONS.get(key)
        if record is None or now - record[0] > _JOB_CREATE_WINDOW_SECONDS:
            _JOB_CREATIONS[key] = [now, 1]
        else:
            record[1] += 1
        return _JOB_CREATIONS[key][1] <= _JOB_CREATE_LIMIT


def reset_job_rate_limit() -> None:
    """Zera as contagens de criação de jobs (usado em testes)."""
    with _RATE_LOCK:
        _JOB_CREATIONS.clear()