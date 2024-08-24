import flet as ft
from time import sleep

from utils.share_model import clear_form, close_app, button_style
from utils.validators import file_generate

# CONTROLES DE ENTRADA DE TEXTO
cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    border_color='#5a90fc',
    expand=True,
)

start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

# CONTROLES DE BOTÕES
generate_button = ft.ElevatedButton(
    on_click=lambda e: file_generate(
        e,
        cpf_field,
        start_date_field,
        end_date_field,
    ),
    col={'md': 4},
    text='GERAR AQUIVO',
    style=button_style('OK'),
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
        icon_color='#4dd0e1',
        text_color='#abb2bf',
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
        bgcolor='#21252b',
        padding=10,
        border=ft.border.all(width=1, color='#5a90fc'),
        border_radius=5,
        visible=False,
        opacity=0.0,
        animate_opacity=ft.animation.Animation(
            500, ft.AnimationCurve.EASE_IN_OUT
        ),
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
    title=ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            col=6,
                            name=ft.icons.QUESTION_MARK,
                            color='#4dd0e1',
                            size=30
                        ),
                        ft.Text(
                            col=6,
                            value='Confirmar saída',
                            color='#abb2bf',
                            size=20
                        ),
                    ]
                )
            ),
            ft.Divider(color=ft.colors.GREY_700, thickness=1),
        ]
    ),
    modal=True,
    content=ft.Container(
        width=350,
        height=30,
        content=ft.Row(
            controls=[
                ft.Text(
                    value='Tem certeza de que deseja sair?',
                    color='#abb2bf',
                    size=18
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )),

    content_padding=ft.padding.only(bottom=20),
    shape=ft.RoundedRectangleBorder(radius=10),
    actions=[
        ft.ElevatedButton(
            content=ft.Text(value='SIM', size=12),
            on_click=yes_click,
            style=button_style('OK')
        ),
        ft.ElevatedButton(
            content=ft.Text(value='NÃO', size=12),
            on_click=no_click,
            style=button_style()
        ),
    ],
    elevation=20,
    surface_tint_color='#2b2d30',
    actions_alignment=ft.MainAxisAlignment.END,
)

progress_bar = ft.ProgressBar(
    width=600
)
