import flet as ft
from time import sleep

from utils.validators import validate_form, clear_form

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
    on_click=lambda e: validate_form(
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
    col={'md': 4},
    text='Sair',
    expand=True
)
