"""Exceções tipadas do núcleo.

Permitem que a camada de apresentação (desktop Flet ou API web) trate os
erros de forma estruturada, sem depender de mensagens de texto soltas.
"""


class CoreError(Exception):
    """Erro base do núcleo."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.cause = cause


class ConfigError(CoreError):
    """Erro de configuração/ambiente (ex.: variáveis obrigatórias ausentes)."""


class LoginError(CoreError):
    """Falha na autenticação no portal."""


class ScrapeError(CoreError):
    """Falha durante a coleta de dados do portal."""


class FileGenerationError(CoreError):
    """Falha na geração dos arquivos (Excel/PDF)."""


class JobCancelledError(CoreError):
    """Processamento cancelado pelo usuário (ou sessão perdida mid-flight)."""