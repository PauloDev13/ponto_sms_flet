import ctypes

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

    # Intercepta o evento disparado quando o botão "X" da janela é clicado
    page.window_prevent_close = True
    page.on_window_event = window_event

    # Mantém a janela do aplicativo sobre as demais janelas abertas no PC
    page.window.always_on_top = True
    page.window.center()

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Definindo o tamanho da janela
    page.window_width = 800
    page.window_height = 600
    page.window.max_width = 800
    page.window.max_height = 800
    page.window.center()

    page.add(
        ft.Card(
            content=ft.Container(
                width=600,
                padding=20,
                bgcolor=ft.colors.BLACK12,
                border_radius=20,
                border=ft.border.all(1, ft.colors.WHITE30),

                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text('Consulta ponto SMS')
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
                ]),
            )
        ),
    )

    cpf_field.focus()


ft.app(main)
