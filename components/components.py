import flet as ft
from time import sleep


def validate_form(e) -> None:
    cpf = cpf_field.value
    start_date = start_date_field.value
    end_date = end_date_field.value

    if not cpf:
        snack_show('CPF é obrigatório')
        return

    elif not start_date:
        snack_show('Data Inicial é obrigatório')
        return

    elif not end_date:
        snack_show('Data Final é obrigatório')
        return
    else:
        print('TUDO OK')
        clear_form()


def snack_show(message: str) -> None:
    custom_snackbar.content.controls[1].value = message
    custom_snackbar.visible = True
    custom_snackbar.opacity = 0.6
    custom_snackbar.update()

    sleep(3)
    hide_custom_snackbar()


def hide_custom_snackbar() -> None:
    custom_snackbar.opacity = 0.0
    custom_snackbar.update()
    sleep(0.3)
    custom_snackbar.visible = False,
    custom_snackbar.update()


def clear_form():
    cpf_field.value = '',
    start_date_field.value = '',
    end_date_field.value = '',

    cpf_field.update()
    start_date_field.update()
    end_date_field.update()


cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    expand=True
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
    on_click=validate_form,
    text='Gerar arquivo',
    col={'md': 4},
    expand=True,
    color='white',
    bgcolor=ft.colors.BLUE_500,
)
cancel_button = ft.ElevatedButton(
    col={'md': 4},
    text='Cancelar',
    expand=True,
    bgcolor=ft.colors.AMBER_200,
    color=ft.colors.BLACK
)
exit_button = ft.ElevatedButton(
    col={'md': 4},
    text='Sair',
    expand=True
)

custom_snackbar = ft.Container(
    content=ft.Row([
        ft.Icon(
            name=ft.icons.WARNING,
            color=ft.colors.BLACK
        ),
        ft.Text(
            color=ft.colors.BLACK,
            size=20,
            expand=True
        )
    ]),
    width=600,
    bgcolor=ft.colors.AMBER_200,
    padding=10,
    border_radius=5,
    visible=False,
    opacity=0.0,
    animate_opacity=300
)
