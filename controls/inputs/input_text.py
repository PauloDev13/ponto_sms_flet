import flet as ft


# CONTROLES DE ENTRADA DE TEXTO
cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    border_color='#5a90fc',
    autofocus=True,
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