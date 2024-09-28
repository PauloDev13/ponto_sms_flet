from time import sleep

import flet as ft
from enum import Enum

from models.page_manager import PageManager


class EffectType(Enum):
    OPACITY = 'opacity'
    OFFSET = 'offset'


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
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            animate_offset=ft.Animation(600, ft.AnimationCurve.ELASTIC_OUT)
        )

        # Adiciona a snackbar usando overlay e atualiza a página
        page.overlay.append(snackbar)
        page.update()

        # Chama função (control_effect) que aplica o efeito de
        # entrada no (snackbar) de acordo com os parâmetros passados
        cls.control_effect(
            container=snackbar,
            effect_type=EffectType.OFFSET,
            start=-100,
            end=1,
            step=25
        )

        # Espera 2 segundos
        sleep(2)

        # Chama função (control_effect) que aplica o efeito de
        # saída no (snackbar) considerando os parâmetros passados
        cls.control_effect(
            container=snackbar,
            effect_type=EffectType.OFFSET,
            start=1,
            end=-100,
            step=-25
        )

        # remove a snackbar usando overlay e atualiza a página
        page.overlay.remove(snackbar)
        page.update()

    # FUNÇÃO QUE APLICA EFEITO DE ENTRADA E SAÍDA NO SNACKBAR DE MENSAGENS
    @classmethod
    def control_effect(
            cls,
            container: ft.Row,
            effect_type: EffectType,
            start: int,
            end: int,
            step: int,
    ):
        # Usa um loop aplicando o efeito. Dependendo dos valores passados
        #  nos parâmetros, o efeito pode ser de opacidade ou offset
        for effect in range(start, end, step):
            if effect_type == EffectType.OPACITY:
                container.opacity = effect / 100

            if effect_type == EffectType.OFFSET:
                container.offset = ft.transform.Offset(0, effect / 100)

            # Atualiza somente o snackbar passado por parâmetro
            container.update()

            # Espera 0,05 segundos para reiniciar o loop
            sleep(0.05)

