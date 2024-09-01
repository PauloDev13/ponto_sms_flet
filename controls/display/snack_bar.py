import flet as ft

from time import sleep
from models.page_manager import *


# FUNÇÃO QUE EXIBE O CONTROLE QUE SIMULA UMA SNACKBAR DE MENSAGENS
def snack_show(
        message: str,
        icon=ft.icons.INFO_ROUNDED,
        icon_color='#4dd0e1',
        text_color='#abb2bf',
        container_height=50,
) -> None:
    content = [
        ft.Icon(icon, color=icon_color, size=30),
        ft.Text(
            message,
            color=text_color,
            size=18,
            width=500,
            weight=ft.FontWeight.W_500
        ),
    ]

    # Atribui a variável (container_snackbar) o resultado da
    # função (message_snackbar) que recebe como argumento o
    # conteúdo que será exibido
    container_snackbar = message_snackbar(
        content=content,
        container_height=container_height
    )

    # Atribui a variável (column_snackbar) uma linha com o
    # (container_snackbar) para deixar conteúdo centralizado
    column_snackbar = ft.Row(
        controls=[container_snackbar],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
    )
    # Adiciona o snack bar e atualiza a página
    PageManager.get_page().overlay.append(column_snackbar)
    PageManager.get_page().update()

    container_snackbar.opacity = 0.8
    container_snackbar.visible = True
    container_snackbar.update()

    # Espera 3 segundos para retirar
    # snackbar da tela com efeito de fade
    sleep(2)
    container_snackbar.opacity = 0.0
    container_snackbar.update()
    sleep(0.5)
    container_snackbar.visible = False,
    container_snackbar.update()

    # Remove da página o snackbar de mensagem e atualiza a página
    PageManager.get_page().overlay.remove(column_snackbar)
    PageManager.get_page().update()


# FUNÇÃO QUE CRIA O CONTROLE PARA SIMULAR UMA SNACKBAR DE MENSAGENS
def message_snackbar(content: list[ft.Control], container_height: int):
    # Customiza o valor da margem superior dependendo da altura do controle
    margin = ft.margin.only(top=30) if container_height <= 50 else ft.margin.only(top=10)

    return ft.Container(
        content=ft.Row(
            controls=content
        ),
        margin=margin,
        height=container_height,
        width=600,
        bgcolor='#21252b',
        padding=10,
        border=ft.border.all(width=2, color='#5a90fc'),
        border_radius=10,
        visible=False,
        opacity=0.0,
        animate_opacity=ft.animation.Animation(
            500, ft.AnimationCurve.EASE_IN_OUT
        ),
    )