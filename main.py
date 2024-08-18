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


def main(page: ft.Page):
    page.title = 'Ponto SMS'

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Definindo o tamanho da janela
    page.window_width = 800
    page.window_height = 600

    # Obtendo a resolução da tela
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)

    # Calculando a posição para centralizar a janela
    page.window_left = (screen_width - page.window_width) // 2
    page.window_top = (screen_height - page.window_height) // 2

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
