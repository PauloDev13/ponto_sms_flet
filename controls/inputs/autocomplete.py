import flet as ft

from services.data.autocomplete import read_csv

# Busca no arquivo (.env) o valor da URL base e o nome do diretório (NAME_FOLDER)
from config.config_env import PATH_CSV

suggestions = read_csv(PATH_CSV)


# def on_selected(e):
    # code = e.control.suggestions[e.control.selected_index].key
    # print(f'O VALOR DO CÓDIGO É: {code}')


unit_field = ft.AutoComplete(
    suggestions=suggestions,
    on_select=lambda e: print(e.control.selected_index, e.selection),
)
