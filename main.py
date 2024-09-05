import flet as ft

from controls.buttons.elevated_button import (
    generate_button,
    cancel_button,
    exit_button,
    open_folder_button
)

# Importação dos módulos locais
from controls.inputs.input_text import (
    cpf_field,
    start_date_field,
    end_date_field,
)

from controls.inputs.checkboxs import checkbox_excel_field, checkbox_pdf_field

from utils.share_model import window_event, on_key_enter_event
from models.page_manager import PageManager


def main(page: ft.Page):

    # Definindo a instância de Page no PageManager
    PageManager.set_page(page)

    # Define o nome que será exibido na barra de ferramentas da página
    page.title = 'Ponto SMS'

    # Definindo o tamanho da janela
    page.window.width = 850
    page.window.height = 650

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Define que o tema da página ser DARK (escuro)
    page.theme_mode = ft.ThemeMode.DARK

    # Definindo que a janela não pode ser redimensionada
    page.window_resizable = False
    page.window_maximizable = False
    page.window.minimized = False
    page.window.center()

    # Mantém a janela do aplicativo sobre as demais janelas abertas no PC
    page.window.always_on_top = True

    # Intercepta o evento disparado quando o botão (X) da janela é clicado
    page.window.prevent_close = True
    page.on_window_event = window_event

    # Intercepta o evento disparado quando a tecla (Enter) é pressionada
    page.on_keyboard_event = on_key_enter_event

    # Adiciona à página um controle (Card) com os demais controles do formulário
    page.add(
        ft.Card(
            content=ft.Container(
                width=600,
                padding=20,
                bgcolor='#1e1f22',
                border_radius=10,
                border=ft.border.all(1, '#5a90fc'),
                content=ft.Column(
                    spacing=20,
                    controls=[
                        ft.ListTile(
                            title=ft.Text(
                                value='Consulta ponto SMS',
                                size=25,
                                weight=ft.FontWeight.W_500
                            )
                        ),
                        ft.ResponsiveRow([
                            cpf_field
                        ]),
                        ft.Container(
                            ft.ResponsiveRow([
                                start_date_field,
                                end_date_field
                            ]),
                            margin=ft.margin.only(top=20)
                        ),
                        ft.Container(
                            ft.Row([
                                checkbox_excel_field,
                                checkbox_pdf_field,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                        ),
                        ft.ResponsiveRow([
                                generate_button,
                        ]),
                        ft.Container(
                            ft.ResponsiveRow([
                                open_folder_button,
                                cancel_button,
                                exit_button
                            ]),
                        ),
                    ]
                ),
            )
        ),
    )


ft.app(target=main)
