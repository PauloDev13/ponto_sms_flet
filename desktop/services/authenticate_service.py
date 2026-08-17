"""Wrapper de autenticação usado pela aplicação Flet.

A lógica real está em services/auth_core.py (desacoplada de Flet, reutilizável
no backend web). Este módulo apenas cria o driver, exibe a barra de progresso
durante a resolução manual do captcha e mostra as mensagens de feedback.

Fluxo original mantido: retorna o driver válido ou None.
"""
import flet as ft

from desktop.models.alert_snackbar import AlertSnackbar
from backend.core.auth_core import authenticate, login_service
from desktop.utils.share_model import login_progress_bar


def login():
    """Fluxo usado pela aplicação Flet.

    Retorna uma instância do WebDriver (sessão válida) ou None em falha.
    """
    status, driver = login_service(
        on_manual_wait=lambda seconds: login_progress_bar(total_time=seconds),
    )

    if status in ('session_active', 'success'):
        AlertSnackbar.show(
            message='Login realizado com sucesso!'
            if status == 'success' else 'Sessão ativa recuperada!',
            icon=ft.icons.LOGIN_SHARP,
            icon_color=ft.colors.GREEN,
        )
        return driver

    AlertSnackbar.show(
        message='Falha no login! Tente novamente.',
        icon=ft.icons.INFO,
    )
    return None
