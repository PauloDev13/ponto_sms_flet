import flet as ft
import ctypes
from components import components


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

        # if not errors:
        #     dialog = ft.AlertDialog(
        #         title=ft.Row([
        #             ft.Icon(name=ft.icons.WARNING, color=ft.colors.RED, size=30),
        #             ft.Text('ATENÇÃO!', weight=ft.FontWeight.BOLD, size=24)
        #         ], alignment=ft.MainAxisAlignment.START),
        #
        #         content=ft.Text('Dados enviados'),
        #         actions=[
        #             ft.TextButton('Fechar', on_click=lambda e_: close_dialog(dialog))
        #         ],
        #         bgcolor=ft.colors.GREEN_300,
        #         shape=ft.RoundedRectangleBorder(radius=10),
        #         alignment=ft.alignment.top_center
        #     )
        #
        #     # Abrindo o diálogo
        #     page.dialog = dialog
        #     page.dialog.open = True
        #     page.update()

    #     def close_dialog(dialog_):
    #         dialog.open = False
    #         page.update()
    #
    # cpf_field = ft.TextField(
    #     label='CPF',
    #     col={'md': 12},
    #     hint_text='Digite um CPF',
    #     expand=True
    # )
    #
    # start_date_field = ft.TextField(
    #     label='Período Inicial',
    #     hint_text='Mês/Ano',
    #     col={'md': 6},
    #     text_align=ft.TextAlign.RIGHT,
    #     expand=True
    # )
    #
    # end_date_field = ft.TextField(
    #     label='Período final',
    #     hint_text='Mês/Ano',
    #     col={'md': 6},
    #     text_align=ft.TextAlign.RIGHT,
    #     expand=True
    # )
    #
    # generate_button = ft.ElevatedButton(
    #     on_click=validate_form,
    #     text='Gerar arquivo',
    #     col={'md': 4},
    #     expand=True,
    #     color='white',
    #     bgcolor=ft.colors.BLUE_500,
    # )
    # cancel_button = ft.ElevatedButton(
    #     col={'md': 4},
    #     text='Cancelar',
    #     expand=True,
    #     bgcolor=ft.colors.AMBER_200,
    #     color=ft.colors.BLACK
    # )
    # exit_button = ft.ElevatedButton(
    #     col={'md': 4},
    #     text='Sair',
    #     expand=True
    # )

    if not components.errors:
        # print(f'CPF: {cpf} - DATA INICIO: {start_date} - DATA FINAL {end_date}')
        page.snack_bar = ft.SnackBar(ft.Text(f'CPF: {components.cpf_field.value}\nDATA INICIO: {components.start_date_field.value} - DATA FINAL {components.end_date_field.value}'))
        page.snack_bar.open = True
        page.update()

    page.add(
        ft.Card(
            content=ft.Container(
                width=600,
                padding=20,
                bgcolor=ft.colors.BLACK12,
                border_radius=20,
                border=ft.border.all(1, ft.colors.WHITE30),

                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text('Consulta ponto SMS')
                    ),
                    ft.ResponsiveRow([
                        components.cpf_field
                    ]),
                    ft.Container(
                        ft.ResponsiveRow([
                            components.start_date_field,
                            components.end_date_field
                        ]),
                        margin=ft.margin.only(top=20)
                    ),
                    ft.Container(
                        ft.ResponsiveRow([
                            components.generate_button,
                            components.cancel_button,
                            components.exit_button
                        ]),
                        margin=ft.margin.only(top=20)
                    )
                ]),
            )
        )
    )

    # components.validate_form()


ft.app(main)
