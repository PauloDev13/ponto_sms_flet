"""Configurações do backend web, desacopladas de Flet e PyInstaller.

Reutiliza o arquivo .env da raiz do projeto (mesmo usado pela aplicação
desktop). Diferente de config/config_env.py, este módulo:
- não depende de sys.frozen (não há empacotamento PyInstaller no backend);
- expõe um objeto Settings tipado, mais conveniente para a API web.

Recarga automática do .env: a cada leitura de variável é feito apenas um
os.stat no arquivo (microssegundos). O conteúdo só é relido/parseado quando
o mtime do .env muda (ex.: incluir/alterar um usuário em WEB_USERS) — assim
não há custo real por requisição, mas edições no .env passam a valer sem
reiniciar o servidor.
"""
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

# Raiz do repositório (contém o .env e data/unidades.csv)
REPO_ROOT = Path(__file__).resolve().parents[2]

_ENV_FILE = REPO_ROOT / '.env'

# Carrega o .env na importação do módulo.
load_dotenv(_ENV_FILE)

_LOCK = threading.Lock()
_ENV_MTIME: float = 0.0


def _env_mtime() -> float:
    try:
        return _ENV_FILE.stat().st_mtime
    except OSError:
        return 0.0


def _refresh_env() -> None:
    """Recarrega o .env APENAS se o arquivo mudou (comparação por mtime).

    Custo por acesso: um os.stat. O parse do arquivo só ocorre quando há
    alteração, então não há impacto de performance no uso normal.
    """
    global _ENV_MTIME
    mtime = _env_mtime()
    if mtime == _ENV_MTIME:
        return
    with _LOCK:
        if mtime != _ENV_MTIME:
            load_dotenv(_ENV_FILE, override=True)
            _ENV_MTIME = mtime


def _env(name: str, default: str = '') -> str:
    """Lê uma variável, garantindo que o .env esteja atualizado."""
    _refresh_env()
    return os.getenv(name, default)


# Linha de base: registra o mtime logo após a carga feita na importação,
# para que o primeiro acesso não dispare um reload desnecessário.
_ENV_MTIME = _env_mtime()


class Settings:
    """Leitura tipada das variáveis de ambiente do projeto."""

    # Credenciais do portal
    @property
    def user(self) -> str:
        return _env('USER', '')

    @property
    def password(self) -> str:
        return _env('PASSWORD', '')

    # URLs do portal
    @property
    def url_base(self) -> str:
        return _env('URL_BASE', '')

    @property
    def url_data(self) -> str:
        return _env('URL_DATA', '')

    @property
    def url_init(self) -> str:
        return _env('URL_INIT', '')

    # Pasta de destino dos arquivos gerados. Avaliado a cada acesso para
    # permitir sobrescrever por environment (NAME_FOLDER) em testes/execução.
    @property
    def name_folder(self) -> str:
        return _env('NAME_FOLDER', 'PLANILHAS_SMS')

    @property
    def output_dir(self) -> Path:
        """Pasta de destino dos arquivos (avalia o env a cada acesso)."""
        env = _env('OUTPUT_DIR', '')
        if env:
            return Path(env).expanduser()
        return Path.home() / 'Documents' / self.name_folder

    # Recursos locais
    @property
    def path_logo(self) -> Path:
        return REPO_ROOT / _env('PATH_LOGO', 'assets/logo_pgm.png')

    @property
    def path_csv(self) -> Path:
        return REPO_ROOT / _env('PATH_CSV', 'data/unidades.csv')

    # reCAPTCHA (opcional)
    @property
    def captcha_provider(self) -> str:
        return _env('CAPTCHA_PROVIDER', '')

    @property
    def captcha_api_key(self) -> str:
        return _env('CAPTCHA_API_KEY', '')

    # Ghostscript (compressão de PDF). Opcional; se vazio, tenta localizar
    # automaticamente (shutil.which ou path padrão do Windows).
    @property
    def ghostscript_binary(self) -> str:
        return _env('GHOSTSCRIPT_BIN', '')

    @property
    def job_ttl_hours(self) -> int:
        """Tempo de vida (h) dos jobs concluídos antes da limpeza em disco."""
        return int(_env('JOB_TTL_HOURS', '24'))

    @property
    def jobs_history_limit(self) -> int:
        """Quantos jobs (por usuário) são mantidos no histórico navegável."""
        return int(_env('JOBS_HISTORY_LIMIT', '20'))

    # ----------------------- sessão web (FASE 4) --------------------------
    @property
    def session_secret(self) -> str:
        """Segredo usado para assinar o cookie de sessão do usuário web."""
        return _env('SESSION_SECRET', '')

    @property
    def session_ttl_hours(self) -> int:
        """Tempo de vida (h) da sessão web antes de exigir novo login."""
        return int(_env('SESSION_TTL_HOURS', '12'))

    @property
    def session_cookie_secure(self) -> bool:
        """Atributo 'Secure' do cookie de sessão (enviado só sobre HTTPS).

        Lido de SESSION_COOKIE_SECURE ('true'/'1'/'yes'/'on' ativam).
        Padrão False: a VM atualmente expõe a aplicação via HTTP puro
        (http://<ip>:8000) sem terminação SSL — ativar Secure nesse cenário
        faria o navegador descartar o cookie e quebraria o login. Defina como
        true somente quando estiver atrás de um proxy reverso com HTTPS.
        """
        return _env('SESSION_COOKIE_SECURE', 'false').strip().lower() \
            in ('1', 'true', 'yes', 'on')

    @property
    def web_users(self) -> dict[str, str]:
        """Contas locais da aplicação web: 'user1:senha1,user2:senha2'.

        Lidas do ambiente a cada acesso (testável). Nunca expostas via
        API/frontend; apenas conferidas no login.
        """
        raw = _env('WEB_USERS', '')
        users: dict[str, str] = {}
        for entry in raw.split(','):
            entry = entry.strip()
            if not entry:
                continue
            name, _, pwd = entry.partition(':')
            users[name.strip()] = pwd.strip()
        return users

    @property
    def required_ok(self) -> bool:
        """True quando as variáveis obrigatórias do portal estão preenchidas."""
        return all([self.user, self.password, self.url_base, self.url_data, self.url_init])

    @property
    def masked_user(self) -> str:
        if not self.user:
            return '(vazio)'
        return f'{self.user[:3]}...***'

    def ensure_output_dir(self) -> Path:
        """Cria (idempotente) e retorna a pasta de destino dos arquivos."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


settings = Settings()