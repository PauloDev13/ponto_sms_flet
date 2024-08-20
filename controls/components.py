import flet as ft
from time import sleep

from utils.share_model import clear_form, close_app
from utils.validators import file_generate

# Variável global
container_snackbar = None

cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    expand=True,
)

start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
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
    text='Gerar arquivo',
    col={'md': 4},
    expand=True,
    color='white',
    bgcolor=ft.colors.BLUE_500,
)

cancel_button = ft.ElevatedButton(
    on_click=lambda e: clear_form(
        cpf_field,
        start_date_field,
        end_date_field
    ),
    col={'md': 4},
    text='Cancelar',
    expand=True,
    bgcolor=ft.colors.AMBER_200,
    color=ft.colors.BLACK
)

exit_button = ft.ElevatedButton(
    on_click=close_app,
    col={'md': 4},
    text='Sair',
    expand=True
)


def snack_show(
    page: ft.Page,
    message: str,
    icon_name=ft.icons.INFO_ROUNDED,
    bg_color=ft.colors.AMBER_200,
) -> None:

    global container_snackbar

    if container_snackbar is None:
        container_snackbar = message_snackbar(icon_name, bg_color)
        page.add(container_snackbar)

    container_snackbar.content.controls[0].name = icon_name
    container_snackbar.content.controls[1].value = message
    container_snackbar.bgcolor = bg_color
    container_snackbar.visible = True
    container_snackbar.opacity = 0.6
    container_snackbar.update()

    sleep(3)
    hide_snackbar()


def hide_snackbar() -> None:
    if container_snackbar is not None:
        container_snackbar.opacity = 0.0
        container_snackbar.update()
        sleep(0.3)
        container_snackbar.visible = False,
        container_snackbar.update()


def message_snackbar(icon_name: str, bg_color: str):
    return ft.Container(
        content=ft.Row([
            ft.Icon(
                name=icon_name,
                size=40,
                color=ft.colors.BLUE
            ),
            ft.Text(
                size=20,
                expand=True,
                color=ft.colors.BLACK,
            )
        ]),
        width=600,
        bgcolor=bg_color,
        padding=10,
        border_radius=5,
        visible=False,
        opacity=0.0,
        animate_opacity=300,
    )
