import flet as ft

from controls.components import (
    # Controles
    cpf_field,
    start_date_field,
    end_date_field,

    # Botões
    generate_button,
    cancel_button,
    exit_button
)
# Importa do módulo (share_model) a função (window_event)
from utils.share_model import window_event


def main(page: ft.Page):

    page.title = 'Ponto SMS'

    page.theme_mode = ft.ThemeMode.DARK

    # Intercepta o evento disparado quando o botão "X" da janela é clicado
    page.window.prevent_close = True
    page.on_window_event = window_event

    # Mantém a janela do aplicativo sobre as demais janelas abertas no PC
    page.window.always_on_top = True

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Definindo o tamanho da janela
    page.window.width = 800
    page.window.height = 600

    # Definindo que a janela não pode ser redimensionada
    page.window_resizable = False
    page.window_maximizable = False
    page.window.center()

    page.add(
        ft.Card(
            content=ft.Container(
                width=600,
                padding=20,
                bgcolor='#1e1f22',
                border_radius=10,
                border=ft.border.all(1, '#5a90fc'),
                content=ft.Column(
                    spacing=20,
                    controls=[
                        ft.ListTile(
                            title=ft.Text(
                                value='Consulta ponto SMS',
                                size=25,
                                weight=ft.FontWeight.W_500
                            )
                        ),
                        ft.ResponsiveRow([
                            cpf_field
                        ]),
                        ft.Container(
                            ft.ResponsiveRow([
                                start_date_field,
                                end_date_field
                            ]),
                            margin=ft.margin.only(top=20)
                        ),
                        ft.Container(
                            ft.ResponsiveRow([
                                generate_button,
                                cancel_button,
                                exit_button
                            ]),
                            margin=ft.margin.only(top=20)
                        ),
                    ]
                ),
            )
        ),
    )

    cpf_field.focus()


ft.app(target=main)
