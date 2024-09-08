import flet as ft

from models.page_manager import PageManager
from models.splash_screen import SplashScreen
from utils.share_model import window_event, on_key_enter_event


def main(page: ft.Page):

    # Definindo a instância de Page no PageManager
    PageManager.set_page(page)

    # Define o nome que será exibido na barra de ferramentas da página
    page.title = 'Consulta ponto Eletrônico'

    # Centralizando o conteúdo da janela
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.center()

    # Define que o tema da página ser DARK (escuro)
    page.theme_mode = ft.ThemeMode.DARK

    # Definindo que a janela não pode ser redimensionada
    page.window.resizable = False
    page.window.maximizable = False
    page.window.minimized = False

    # Mantém a janela do aplicativo sobre as demais janelas abertas no PC
    page.window.always_on_top = True

    # Intercepta o evento disparado quando o botão (X)
    # da barra de título da janela é clicado
    page.window.prevent_close = True
    page.window.on_event = window_event

    # Intercepta o evento disparado quando a tecla (Enter) é pressionada
    page.on_keyboard_event = on_key_enter_event

    # Chama a função (SplashScreen). Ela exibe uma tela inicial por 3
    # segundos e após esse tempo, exibe a janela principal da aplicação
    SplashScreen(page=page, duration=2).show()


ft.app(target=main)
