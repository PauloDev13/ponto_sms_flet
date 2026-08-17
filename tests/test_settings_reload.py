"""Testes da recarga automática do .env (mtime) — FASE 4.

Editar o arquivo .env deve passar a valer no próximo acesso, sem
reiniciar o servidor. O .env real do projeto NUNCA é tocado: o teste
redireciona _ENV_FILE para um arquivo temporário.
"""
import pytest

from backend.core import settings as settings_module


@pytest.fixture
def tmp_env(tmp_path, monkeypatch):
    """Aponta o settings para um .env temporário e força o primeiro reload."""
    env_file = tmp_path / '.env'
    env_file.write_text(
        "WEB_USERS='admin:a'\nSESSION_SECRET='s1'\n", encoding='utf-8')

    monkeypatch.setattr(settings_module, '_ENV_FILE', env_file)
    monkeypatch.setattr(settings_module, '_ENV_MTIME', 0.0)
    # evita que valores carregados do .env real na importação interfiram
    monkeypatch.delenv('WEB_USERS', raising=False)
    monkeypatch.delenv('SESSION_SECRET', raising=False)
    return env_file


def test_reload_after_edit_keeps_only_new_values(tmp_env):
    assert settings_module.settings.web_users == {'admin': 'a'}

    tmp_env.write_text(
        "WEB_USERS='admin:b,paulo:p'\nSESSION_SECRET='s1'\n", encoding='utf-8')

    assert settings_module.settings.web_users == {'admin': 'b', 'paulo': 'p'}


def test_secret_reflects_edit(tmp_env):
    assert settings_module.settings.session_secret == 's1'

    tmp_env.write_text(
        "WEB_USERS='admin:a'\nSESSION_SECRET='s2'\n", encoding='utf-8')

    assert settings_module.settings.session_secret == 's2'


def test_unchanged_file_keeps_value(tmp_env):
    assert settings_module.settings.web_users == {'admin': 'a'}
    # sem alterar o arquivo, o valor permanece (sem reload)
    assert settings_module.settings.web_users == {'admin': 'a'}