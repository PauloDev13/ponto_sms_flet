import flet as ft

from services.data.autocomplete import read_csv

# Busca no arquivo (.env) o valor da URL base e o nome do diretório (NAME_FOLDER)
from config.config_env import PATH_CSV

suggestions = read_csv(PATH_CSV)


def autocomplete_value(control: ft.AutoComplete) -> str:
    selected_index = control.selected_index
    value = control.suggestions[selected_index].value

    return value.split('-')[0]


unit_field = ft.AutoComplete(
    suggestions_max_height=200,
    suggestions=suggestions,
)

label = ft.Text(value='Unidade', color='#5a90fc')

unit_autocomplete_field = ft.Container(
    content=ft.Column(
        controls=[
            label,
            unit_field
        ]),

    margin=ft.margin.only(top=10)
)
