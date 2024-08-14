import flet as ft


errors = []
def validate_form(e):
    cpf = cpf_field.value
    start_date = start_date_field.value
    end_date = end_date_field.value

    # errors = []

    if not cpf:
        errors.append('CPF é obrigatório')
        cpf_field.error_text = 'Digite um CPF válido'
    else:
        cpf_field.error_text = None

    if not start_date:
        errors.append('Data inicial é obrigatória')
        start_date_field.error_text = 'Informe o período inicial'
    else:
        start_date_field.error_text = None

    if not end_date:
        errors.append('Data inicial é obrigatória')
        end_date_field.error_text = 'Informe o período final'
    else:
        end_date_field.error_text = None

    # if not errors:
    #     # print(f'CPF: {cpf} - DATA INICIO: {start_date} - DATA FINAL {end_date}')
    #     snack_bar = ft.SnackBar(ft.Text(f'CPF: {cpf} - DATA INICIO: {start_date} - DATA FINAL {end_date}'))
    #     snack_bar.open = True
    #     snack_bar.update()

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
