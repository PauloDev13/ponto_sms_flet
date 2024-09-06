import flet as ft

# Importação dos módulos locais
from controls.inputs.checkboxs import checkbox_pdf_field, checkbox_excel_field
from controls.inputs.input_text import cpf_field, start_date_field, end_date_field
from services.data.init_generate_service import init_generate_files
from utils.share_model import button_style, close_app, clear_form, open_folder

# Dicionário com os controles do formulário
dict_controls: dict = {
    'cpf_field': cpf_field,
    'start_date_field': start_date_field,
    'end_date_field': end_date_field,
}

dict_search_data: dict = {
    'cpf_field': cpf_field,
    'start_date_field': start_date_field,
    'end_date_field': end_date_field,
    'checkbox_excel_field': checkbox_excel_field,
    'checkbox_pdf_field': checkbox_pdf_field,
}

# Botão para gerar as planilhas
generate_button = ft.ElevatedButton(
    on_click=lambda _: init_generate_files(
        dict_search_data=dict_search_data
    ),
    text='GERAR PLANILHAS',
    style=button_style('OK'),
    expand=True,
)

# Botão para limpar os campos do formulário
cancel_button = ft.ElevatedButton(
    on_click=lambda _: clear_form(
        **dict_controls
    ),
    col={'md': 4},
    text='CANCELAR',
    style=button_style(),
    expand=True,
)

# Botão para sair da aplicação
exit_button = ft.ElevatedButton(
    on_click=close_app,
    col={'md': 4},
    text='FECHAR',
    style=button_style(),
    expand=True
)

# Botão para abrir a pasta de arquivos
open_folder_button = ft.ElevatedButton(
    on_click=open_folder,
    col={'md': 4},
    text='ABRIR PASTA',
    style=button_style(),
    expand=True
)
