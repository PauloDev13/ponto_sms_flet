import flet as ft


def main(page: ft.Page):
    page.title = 'Ponto SMS'
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER

    cpf = ft.TextField(
        label='CPF',
        col={'md': 12},
        hint_text='Digite um CPF',
        expand=True
    )

    start_date = ft.TextField(
        label='Data inicial',
        col={'md': 6},
        expand=True
    )

    end_date = ft.TextField(
        label='Data final',
        col={'md': 6},
        expand=True
    )

    generate_button = ft.ElevatedButton(
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
                    ft.Row([
                        cpf
                    ]),
                    ft.ResponsiveRow([
                        start_date, end_date
                    ]),
                    ft.ResponsiveRow([
                        generate_button, cancel_button, exit_button
                    ])
                ]),
            )

        )
    )

    # def btn_generate_clicked(e):
    #     if not cpf.value:
    #         cpf.error_text = 'Informe o CPF'
    #         cpf.update()
    #     else:
    #         cpf.clean()
    #
    # cpf = ft.TextField(
    #     label='CPF',
    #     hint_text='Digite um CPF',
    #     width=600)
    #
    # start_date = ft.TextField(
    #     label='Data inicial',
    #     width=300)
    #
    # end_date = ft.TextField(
    #     label='Data final',
    #     width=300)
    #
    # generate_button = ft.ElevatedButton(
    #     text='Gerar arquivo',
    #     expand=True,
    #     color='white',
    #     bgcolor='blue',
    #     on_click=btn_generate_clicked
    # )
    # cancel_button = ft.ElevatedButton(text='Cancelar', expand=True)
    # exit_button = ft.ElevatedButton(text='Sair', expand=True)
    #
    # row_1 = ft.Row(controls=[cpf])
    # row_2 = ft.Row(controls=[start_date, end_date])
    # row_3 = ft.Row(controls=[generate_button, cancel_button, exit_button])
    #
    # page.add(row_1, row_2, row_3)


ft.app(main)
