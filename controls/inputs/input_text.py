import flet as ft


# Controle que recebe o número do CPF no formulário
cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    border_color='#5a90fc',
    autofocus=True,
    expand=True,
)

# Controle que recebe o número da unidade de lotação
unit_field = ft.TextField(
    label='Unidade',
    col={'md': 4},
    text_align=ft.TextAlign.RIGHT,
    hint_text='Código unidade',
    border_color='#5a90fc',
    expand=True,
)

# Controle que recebe a data inicial no formulário
start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

# Controle que recebe a data final no formulário
end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)
