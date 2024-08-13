import flet as ft
import ctypes


def main(page: ft.Page):
    page.title = 'Ponto SMS'

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Definindo o tamanho da janela
    page.window_width = 800
    page.window_height = 600

    # Obtendo a resolução da tela
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)

    # Calculando a posição para centralizar a janela
    page.window_left = (screen_width - page.window_width) // 2
    page.window_top = (screen_height - page.window_height) // 2

    def validate_form(e):
        cpf = cpf_field.value
        start_date = start_date_field.value
        end_date = end_date_field.value

        errors = []

        if not cpf:
            errors.append('CPF é obrigatório')
            cpf_field.error_text = 'Digite um CPF válido'
        else:
            cpf_field.error_text = None

        if not start_date:
            errors.append('Data inicial é obrigatória')
            start_date_field.error_text = 'Informe a data inicial'
        else:
            start_date_field.error_text = None

        if not end_date:
            errors.append('Data inicial é obrigatória')
            end_date_field.error_text = 'Informe a data inicial'
        else:
            end_date_field.error_text = None

        cpf_field.update()
        start_date_field.update()
        end_date_field.update()

        if not errors:
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(name=ft.icons.WARNING, color=ft.colors.RED, size=30),
                    ft.Text('ATENÇÃO!', weight=ft.FontWeight.BOLD, size=24)
                ], alignment=ft.MainAxisAlignment.START),

                content=ft.Text('Dados enviados'),
                actions=[
                    ft.TextButton('Fechar', on_click=lambda e_: close_dialog(dialog))
                ],
                bgcolor=ft.colors.YELLOW_200,
                shape=ft.RoundedRectangleBorder(radius=10),
            )

            # Abrindo o diálogo
            page.dialog = dialog
            page.dialog.open = True
            page.update()

        def close_dialog(dialog_):
            dialog.open = False
            page.update()

    cpf_field = ft.TextField(
        label='CPF',
        col={'md': 12},
        hint_text='Digite um CPF',
        expand=True
    )

    start_date_field = ft.DatePicker(
        col={'md': 6},
        expand=True
    )

    end_date_field = ft.DatePicker(
        col={'md': 6},
        expand=True
    )

    generate_button = ft.ElevatedButton(
        on_click=validate_form,
        text='Gerar arquivo',
        col={'md': 4},
        expand=True,
        color='white',
        bgcolor='blue',
    )
    cancel_button = ft.ElevatedButton(
        col={'md': 4},
        text='Cancelar',
        expand=True
    )
    exit_button = ft.ElevatedButton(
        col={'md': 4},
        text='Sair',

        expand=True
    )

    page.add(
        ft.Card(
            content=ft.Container(
                width=600,
                padding=10,
                bgcolor=ft.colors.BLACK12,
                border_radius=20,
                border=ft.border.all(1, ft.colors.WHITE30),

                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text('Consulta ponto SMS')
                    ),
                    ft.ResponsiveRow([
                        cpf_field
                    ]),
                    ft.ResponsiveRow([
                        start_date_field, end_date_field
                    ]),
                    ft.ResponsiveRow([
                        generate_button, cancel_button, exit_button
                    ])
                ]),
            )

        )
    )


ft.app(main)
