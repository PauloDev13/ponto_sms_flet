import flet as ft
from time import sleep, time

from models.page_manager import PageManager


def progress_control(
    progress_bar: ft.ProgressBar,
    control_count_down: ft.Control,
    message: str | None = None,
):
    # Cria uma linha com os controles de ícone e de
    # texto e atribui à variável (content_row)
    content_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.icons.INFO, color='#4dd0e1', size=30),
            ft.Text(value=message, color='#abb2bf', size=20)
            if message else control_count_down,
        ]
    )
    # Cria uma coluna que recebe a barra de progresso e
    # atribui à variável (content_progress_bar)
    content_progress_bar = ft.Column(
        controls=[
            progress_bar,
        ]
    )
    # Cria uma coluna que recebe o (content_row) com o ícone
    # e a mensagem, o (content_progress_bar) com a barra de
    # progresso e atribui à variável (content)
    content = ft.Column(
        controls=[
            content_row,
            content_progress_bar,
        ]
    )
    # Retorna um (Container) com o conteúdo (content)
    #  definitivo que será exibido ma barra de progresso
    return ft.Container(
        margin=ft.margin.only(top=30),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            controls=[content]
        )
    )


# FUNÇÃO QUE ATUALIZA O ESTADO DA BARRA DE PROGRESSO
def update_progress(
        progress_bar: ft.ProgressBar,
        control_count_down: ft.Control,
        total_time: float,
        message: str | None,
        status: bool,
):
    # Importa função (progress_control) do módulo controls
    # from controls.components import progress_control

    # Atribui à variável (control) a função (progress_control)
    # que retorna um controle com a barra de progresso
    container = progress_control(
        progress_bar=progress_bar,
        control_count_down=control_count_down,
        message=message,
    )

    # Exibe o controle com a barra de progresso na página
    PageManager.get_page().overlay.append(container)

    # Atribui à variável (start) o tempo atual do sistema
    start = time()

    # Até que o argumento (status) no índice (0) seja
    # falso, atualiza a barra de progresso
    while not status[0]:
        # Calcula o tempo decorrido e atualiza o progresso da barra na página
        elapsed = time() - start
        progress = min(elapsed / total_time, 1)
        progress_bar.value = progress
        PageManager.get_page().update()
        sleep(0.15)

    # Quando o (status) no índice (0) é igual a verdadeiro, atribui
    # o valor de 100% ao progresso da bara e atualiza a página
    progress_bar.value = 1
    PageManager.get_page().update()

    # Remove o controle da barra de progresso e atualiza a página
    PageManager.get_page().overlay.remove(container)
    PageManager.get_page().update()
