import flet as ft

from controls.inputs.input_text import cpf_field, start_date_field, end_date_field
from services.generate_service import file_generate
from utils.share_model import button_style, close_app, clear_form, open_folder

# Dicionário com os controles do formulário
dict_controls: dict = {
    'cpf_field': cpf_field,
    'start_date_field': start_date_field,
    'end_date_field': end_date_field
}

# CONTROLES DE BOTÕES
generate_button = ft.ElevatedButton(
    on_click=lambda _: file_generate(
        cpf_field,
        start_date_field,
        end_date_field,
    ),
    text='GERAR AQUIVO',
    style=button_style('OK'),
    expand=True,
)

cancel_button = ft.ElevatedButton(
    on_click=lambda _: clear_form(
        **dict_controls
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

open_folder_button = ft.ElevatedButton(
    on_click=open_folder,
    col={'md': 4},
    text='ABRIR PASTA',
    style=button_style(),
    expand=True
)
