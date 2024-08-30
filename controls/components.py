from time import sleep

import flet as ft

from models.page_manager import PageManager
from services.generate_service import file_generate
from utils.share_model import clear_form, close_app, button_style, open_folder
from utils.share_model import create_shortcut_to_desktop_folder

# CONTROLES DE ENTRADA DE TEXTO
cpf_field = ft.TextField(
    label='CPF',
    col={'md': 12},
    hint_text='Digite um CPF',
    border_color='#5a90fc',
    autofocus=True,
    expand=True,
)

start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 6},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)

# Dicionário com os controles do formulário
dict_controls: dict = {
    'cpf_field': cpf_field,
    'start_date_field': start_date_field,
    'end_date_field': end_date_field
}

# CONTROLES DE BOTÕES
generate_button = ft.ElevatedButton(
    on_click=lambda _: file_generate(
        cpf_field,
        start_date_field,
        end_date_field,
    ),
    col={'md': 4},
    text='GERAR AQUIVO',
    style=button_style('OK'),
    expand=True,
)

cancel_button = ft.ElevatedButton(
    on_click=lambda _: clear_form(
        **dict_controls
    ),
    col={'md': 4},
    text='CANCELAR',
    style=button_style(),
    expand=True,
)

exit_button = ft.ElevatedButton(
    on_click=close_app,
    col={'md': 4},
    text='FECHAR',
    style=button_style(),
    expand=True
)

open_folder_button = ft.TextButton(
    on_click=open_folder,
    text='ABRIR PASTA DE ARQUIVOS',
    style=button_style(),
    expand=True
)


# FUNÇÃO QUE EXIBE O CONTROLE QUE SIMULA UMA SNACKBAR DE MENSAGENS
def snack_show(
        message: str,
        icon=ft.icons.INFO_ROUNDED,
        icon_color='#4dd0e1',
        text_color='#abb2bf',
        container_height=50,
) -> None:
    content = [
        ft.Icon(icon, color=icon_color, size=30),
        ft.Text(
            message,
            color=text_color,
            size=18,
            width=500,
            weight=ft.FontWeight.W_500
        ),
    ]

    # Atribui a variável (container_snackbar) o resultado da
    # função (message_snackbar) que recebe como argumento o
    # conteúdo que será exibido
    container_snackbar = message_snackbar(
        content=content,
        container_height=container_height
    )

    # Atribui a variável (column_snackbar) uma linha com o
    # (container_snackbar) para deixar conteúdo centralizado
    column_snackbar = ft.Row(
        controls=[container_snackbar],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
    )
    # Adiciona o snack bar e atualiza a página
    PageManager.get_page().overlay.append(column_snackbar)
    PageManager.get_page().update()

    container_snackbar.opacity = 0.8
    container_snackbar.visible = True
    container_snackbar.update()

    # Espera 3 segundos para retirar
    # snackbar da tela com efeito de fade
    sleep(2)
    container_snackbar.opacity = 0.0
    container_snackbar.update()
    sleep(0.5)
    container_snackbar.visible = False,
    container_snackbar.update()

    # Remove da página o snackbar de mensagem e atualiza a página
    PageManager.get_page().overlay.remove(column_snackbar)
    PageManager.get_page().update()


# FUNÇÃO QUE CRIA O CONTROLE PARA SIMULAR UMA SNACKBAR DE MENSAGENS
def message_snackbar(content: list[ft.Control], container_height: int):
    # Customiza o valor da margem superior dependendo da altura do controle
    margin = ft.margin.only(top=30) if container_height <= 50 else ft.margin.only(top=10)

    return ft.Container(
        content=ft.Row(
            controls=content
        ),
        margin=margin,
        height=container_height,
        width=600,
        bgcolor='#21252b',
        padding=10,
        border=ft.border.all(width=2, color='#5a90fc'),
        border_radius=10,
        visible=False,
        opacity=0.0,
        animate_opacity=ft.animation.Animation(
            500, ft.AnimationCurve.EASE_IN_OUT
        ),
    )


# FUNÇÃO PARA O CLICK NO BOTÃO 'SIM' DA CAIXA DE DIÁLOGO
def yes_click(_):
    # pega a instância do navegador na sessão do Flet
    driver = PageManager.get_page().session.get('driver')

    # Se existir a instância, encerra a instância
    if driver is not None:
        driver.quit()

    # Fecha a janela da aplicação
    PageManager.get_page().window.destroy()


# FUNÇÃO PARA O CLICK NO BOTÃO 'SIM' DA CAIXA DE DIÁLOGO
def no_click(_):
    # Fecha a caixa de diálogo e atribui o foco para o campo CPF
    PageManager.get_page().close(confirm_dialog)

    # Passa o foco para o controle CPF
    cpf_field.focus()


# CRIA CAIXA DE DIÁLOGO DE CONFIRMAÇÃO PARA SAIR DA APLICAÇÃO
confirm_dialog = ft.AlertDialog(
    title=ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            col=6,
                            name=ft.icons.QUESTION_MARK,
                            color='#4dd0e1',
                            size=30
                        ),
                        ft.Text(
                            col=6,
                            value='Confirmar saída',
                            color='#abb2bf',
                            size=20
                        ),
                    ]
                )
            ),
            ft.Divider(color=ft.colors.GREY_700, thickness=1),
        ]
    ),
    modal=True,
    content=ft.Container(
        width=350,
        height=30,
        content=ft.Row(
            controls=[
                ft.Text(
                    value='Tem certeza de que deseja sair?',
                    color='#abb2bf',
                    size=18
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )),

    content_padding=ft.padding.only(bottom=20),
    shape=ft.RoundedRectangleBorder(radius=10),

    actions=[
        ft.ElevatedButton(
            content=ft.Text(value='SIM', size=12),
            on_click=lambda _: yes_click(_),
            style=button_style('OK')
        ),
        ft.ElevatedButton(
            content=ft.Text(value='NÃO', size=12),
            on_click=lambda _: no_click(_),
            style=button_style()
        ),
    ],

    elevation=20,
    surface_tint_color='#2b2d30',
    actions_alignment=ft.MainAxisAlignment.END,
)


# FUNÇÃO QUE CRIA UM CONTROLE PARA EXIBIR A BARRA DE PROGRESSO
def progress_control(
    progress_bar: ft.ProgressBar,
    message: str,
):
    # Cria uma linha com os controles de ícone e de texto e atribui à variável (content_row)
    content_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.icons.INFO, color='#4dd0e1', size=30),
            ft.Text(value=message, color='#abb2bf', size=20),
        ]
    )

    # Cria uma coluna que recebe a barra de progresso e
    # atribui à variável (content_progress_bar)
    content_progress_bar = ft.Column(
        controls=[
            progress_bar,
        ]
    )

    # Cria uma coluna que recebe o (content_row) com o ícone e a mensagem, o
    # (content_progress_bar) com a barra de progresso e atribui à variável (content)
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
