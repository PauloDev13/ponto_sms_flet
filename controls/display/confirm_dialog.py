import flet as ft

# Importação dos módulos locais
from controls.inputs.input_text import cpf_field
from models.page_manager import PageManager
from utils.share_model import button_style


# FUNÇÃO PARA O CLICK NO BOTÃO 'SIM' DA CAIXA DE DIÁLOGO
def yes_click(_):
    # Atribui a variável (page) uma instância da página
    page = PageManager.get_page()

    # pega a instância do navegador na sessão do Flet
    driver = page.session.get('driver')

    # Se existir a instância, encerra a instância
    if driver is not None:
        driver.quit()

    # Fecha a janela da aplicação
    page.window.destroy()


# FUNÇÃO PARA O CLICK NO BOTÃO 'NÃO' DA CAIXA DE DIÁLOGO
def no_click(_):
    # Atribui a variável (page) uma instância da página
    page = PageManager.get_page()

    # Fecha a caixa de diálogo e atribui o foco para o campo CPF
    page.close(confirm_dialog)

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
            on_click=lambda e: yes_click(e),
            style=button_style('OK')
        ),
        ft.ElevatedButton(
            content=ft.Text(value='NÃO', size=12),
            on_click=lambda e: no_click(e),
            style=button_style()
        ),
    ],

    elevation=20,
    surface_tint_color='#2b2d30',
    actions_alignment=ft.MainAxisAlignment.END,
)
