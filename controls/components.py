from typing import Tuple

import flet as ft
from time import sleep

from flet_core import ButtonStyle

from utils.share_model import clear_form, close_app, button_style
from utils.validators import file_generate


cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    border_color=ft.colors.WHITE30,
    expand=True,
)

start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    border_color=ft.colors.WHITE30,
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
    border_color=ft.colors.WHITE30,
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

generate_button = ft.ElevatedButton(
    on_click=lambda e: file_generate(
        e,
        cpf_field,
        start_date_field,
        end_date_field,
    ),
    col={'md': 4},
    text='GERAR AQUIVO',
    style=button_style(),
    expand=True,
)

cancel_button = ft.ElevatedButton(
    on_click=lambda _: clear_form(
        cpf_field,
        start_date_field,
        end_date_field
    ),
    col={'md': 4},
    text='CANCELAR',
    style=button_style(),
    expand=True,
)

exit_button = ft.ElevatedButton(
    on_click=close_app,
    col={'md': 4},
    text='FECHAR',
    style=button_style(),
    expand=True
)


def snack_show(
        page: ft.Page,
        message: str,
        icon=ft.icons.INFO_ROUNDED,
        icon_color=ft.colors.BLUE_100,
        text_color=ft.colors.BLUE_100,
) -> None:
    content = [
        ft.Icon(icon, color=icon_color, size=30),
        ft.Text(
            message,
            color=text_color,
            size=18,
            weight=ft.FontWeight.W_500
        ),
    ]

    container_snackbar = message_snackbar(content)

    column_snackbar = ft.Row(
        controls=[container_snackbar],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
    )
    page.overlay.append(column_snackbar)
    page.update()

    container_snackbar.opacity = 0.8
    container_snackbar.visible = True
    container_snackbar.update()

    sleep(3)
    container_snackbar.opacity = 0.0
    container_snackbar.update()
    sleep(0.5)
    container_snackbar.visible = False,
    container_snackbar.update()


def message_snackbar(content: list):
    return ft.Container(
        content=ft.Row(
            controls=content
        ),
        margin=ft.margin.only(top=50),
        width=600,
        bgcolor=ft.colors.BLACK12,
        padding=10,
        border=ft.border.all(width=1, color=ft.colors.WHITE30),
        border_radius=5,
        visible=False,
        opacity=0.0,
        animate_opacity=ft.animation.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )


def yes_click(e):
    driver = e.page.session.get('driver')

    if driver is not None:
        driver.quit()

    e.page.window.destroy()


def no_click(e):
    e.page.close(confirm_dialog)
    cpf_field.focus()
    # confirm_dialog.open = False
    # e.page.update()


confirm_dialog = ft.AlertDialog(
    modal=True,
    content=ft.Container(
        width=400,
        height=50,
        content=ft.Row(
            controls=[
                ft.Icon(
                    name=ft.icons.QUIZ,
                    color=ft.colors.BLUE_100,
                    size=30
                ),
                ft.Text(
                    value='Confirma saída do aplicativo?',
                    color=ft.colors.BLUE_100,
                    size=18
                )
            ],
            alignment=ft.MainAxisAlignment.START,
        )),

    content_padding=20,
    shape=ft.RoundedRectangleBorder(radius=10),
    actions=[
        ft.ElevatedButton('SIM', on_click=yes_click, style=button_style()),
        ft.ElevatedButton('NÃO', on_click=no_click, style=button_style()),
    ],
    elevation=20,
    surface_tint_color=ft.colors.GREY_900,
    actions_alignment=ft.MainAxisAlignment.END,
)

