import threading
from time import sleep

import flet as ft

# # Atribuições das variáveis declaradas no .env
from config.config_env import PATH_LOGO

# Importações dos módulos locais
from controls.buttons.elevated_button import (
    generate_button,
    cancel_button,
    exit_button,
    open_folder_button
)
from controls.inputs.checkboxs import (
    checkbox_excel_field,
    checkbox_pdf_field
)
from controls.inputs.input_text import (
    cpf_field,
    unit_field,
    start_date_field,
    end_date_field,
)

from controls.inputs.autocomplete import unit_autocomplete_field


# Simula o efeito de fade in ou fade out
def fade_effect(
        container: ft.Column,
        page: ft.Page,
        start_opacity: int,
        end_opacity: int,
        step: int
):
    # Usa um loop aplicando o efeito fade. Dependendo dos valores passados
    #  nos parâmetros, o efeito pode ser (fade in) ou (fade out)
    for opacity in range(start_opacity, end_opacity, step):
        container.opacity = opacity / 100
        page.update()
        sleep(0.05)


class SplashScreen:
    def __init__(self, page: ft.Page, duration: int = 3):
        self.splash_controls = None
        self.page = page
        self.duration = duration

    # Cria e exibe uma tela inicial (splash show) antes de exibir
    # a tela principal do sistema
    def show(self):
        # Esconde a barra de títulos da janela
        self.page.window.title_bar_hidden = True

        # Definindo o tamanho da janela
        self.page.window.width = 600
        self.page.window.height = 400

        # Conteúdo fixo do splash screen
        title = 'Consulta Ponto Eletrônico'
        image_src = PATH_LOGO
        text = 'Departamento de Tecnologia da Informação'

        # Criando os controles da tela inicial (splash screen)
        self.splash_controls = [
            ft.Row(controls=[
                ft.Text(value=title, size=30)
            ],
                alignment=ft.MainAxisAlignment.CENTER),

            ft.Row(controls=[
                ft.Image(src=image_src, width=500),
            ], alignment=ft.MainAxisAlignment.CENTER),

            ft.Row(controls=[
                ft.Text(value=text, size=20),
            ], alignment=ft.MainAxisAlignment.CENTER)
        ]

        # Adicionando os controles à página
        self.page.controls.append(
            ft.Column(
                controls=self.splash_controls,
            )
        )
        # Atualiza a página
        self.page.update()

        # Timer para esconder o splash screen após a duração especificada
        threading.Timer(self.duration, self.hide).start()

    # Retira a tela inicial (splash show) da janela,
    # cria e exibe a tela principal do sistema
    def hide(self):
        # Exibe a barra de título da janela
        self.page.window.title_bar_hidden = False

        # Definindo o tamanho da janela
        self.page.window.width = 800
        self.page.window.height = 750

        # Centralizando o conteúdo da janela
        self.page.window.center()

        # Limpar a tela e trocar para a tela principal
        self.page.controls.clear()

        # Atribui a variável (main_screen) os controles da página principal
        main_screen = ft.Column([
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
                                    value='Dados da consulta',
                                    size=25,
                                    weight=ft.FontWeight.W_500
                                )
                            ),
                            ft.Container(
                                ft.ResponsiveRow([
                                    cpf_field,
                                    unit_autocomplete_field
                                ]),
                            ),
                            ft.Container(
                                ft.ResponsiveRow([
                                    start_date_field,
                                    end_date_field
                                ]),
                                margin=ft.margin.only(top=10)
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
        ])

        # Aplica um efeito de fade in nos controles da página principal
        fade_effect(
            container=main_screen,
            page=self.page,
            start_opacity=0,
            end_opacity=101,
            step=20

        )

        # Adiciona os controles à pagina principal e atualiza a página
        self.page.controls.append(main_screen)
        self.page.update()
