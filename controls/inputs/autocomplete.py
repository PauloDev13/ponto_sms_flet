import flet as ft

from services.data.autocomplete import read_csv, read_csv_dropdown

# Busca no arquivo (.env) o valor da URL base e o nome do diretório (NAME_FOLDER)
from config.config_env import PATH_CSV

suggestions = read_csv(PATH_CSV)

options = read_csv_dropdown(PATH_CSV)


def on_selected(e):
    code = e.control.suggestions[e.control.selected_index].value
    print(f'O VALOR DO CÓDIGO É: {code}')


def on_selected_dropdown(e):
    code = e.control.value
    print(f'O VALOR DO CÓDIGO É: {code}')


unit_field = ft.AutoComplete(
    suggestions=suggestions,
    on_select=lambda e: on_selected(e),
)

unit_dropdown_field = ft.Dropdown(
    label='Unidade',
    options=options,
    on_change=lambda e: on_selected_dropdown(e),
)
