from time import sleep

import flet as ft

from models.page_manager import PageManager


class AlertSnackbar:
    @classmethod
    def show(
            cls,
            message: str,
            icon=ft.icons.INFO_ROUNDED,
            icon_color='#4dd0e1',
            text_color='#abb2bf',
            height_container=50
    ):
        # Atribui à variável (page) uma instância da página da classe (PageManager)
        page = PageManager.get_page()

        # Define o conteúdo que será exibido no container
        content = [
            ft.Icon(name=icon, color=icon_color),
            ft.Text(
                value=message,
                color=text_color,
                size=18,
                width=500,
                weight=ft.FontWeight.W_500
            )
        ]

        # Customiza o valor da margem superior dependendo da altura do controle
        margin = ft.margin.only(top=30) if height_container <= 50 else ft.margin.only(top=10)

        # Define o container
        snackbar = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=content,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    margin=margin,
                    height=height_container,
                    padding=10,
                    width=600,
                    bgcolor='#21252b',
                    border=ft.border.all(width=2, color='#5a90fc'),
                    border_radius=10,
                    opacity=1.0,
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        )
        #
        # snackbar_row = ft.Row(
        #     controls=[snackbar],
        #     alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        # )

        page.overlay.append(snackbar)
        page.update()

        # Aplica fade in
        cls.fade_effect(
            container=snackbar,
            page=page,
            start_opacity=0,
            end_opacity=101,
            step=10
        )

        # Espera 2 segundos
        sleep(2)

        # Aplica fade out
        cls.fade_effect(
            container=snackbar,
            page=page,
            start_opacity=100,
            end_opacity=0,
            step=-10
        )

        page.overlay.remove(snackbar)
        page.update()

    # FUNÇÃO QUE APLICA EFEITO FADE
    @classmethod
    def fade_effect(
            cls,
            container: ft.Row,
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
