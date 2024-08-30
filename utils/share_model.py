import os
import shlex
import subprocess
import threading
from time import sleep, time

import flet as ft
from dotenv import load_dotenv

from models.page_manager import PageManager

load_dotenv()
name_folder = os.getenv('NAME_FOLDER')


# FUNÇÃO QUE LIMPA OS CONTROLES DO FORMULÁRIO
def clear_form(**kwargs) -> None:
    # Desestrutura o argumento (**kwargs) e atribui o resultado a um dicionário
    dict_controls: dict = {
        k: v for k, v in kwargs.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field',
        ]
    }
    # Loop que limpa e atualiza todos os controles do formulário
    for key in dict_controls:
        if isinstance(dict_controls[key], ft.Control):
            dict_controls[key].value = ''
            dict_controls[key].update()

    # Seta o focus para o controle CPF no formulário
    dict_controls['cpf_field'].focus()


# FUNÇÃO QUE CAPTURA O EVENTO DISPARADO QUANDO A JANELA DA APLICAÇÃO É FECHADA
def window_event(e):
    # Importa do módulo (controls) o controle (confirm_dialog)
    from controls.components import confirm_dialog

    # se o evento disparado for (close), abre a caixa de diálogo
    if e.data == 'close':
        e.page.open(confirm_dialog)


# FUNÇÃO QUE CAPTURA QUANDO A TECLA (ENTER) É PRESSIONADA
def on_key_enter_event(e):
    from controls.components import generate_button
    if e.key == 'Enter':
        generate_button.on_click(e)


# FUNÇÃO QUE EXIBE A CAIXA DE DIÁLOGO PARA CONFIRMAR A SAÍDA DO APLICATIVO
def close_app(_):
    from controls.components import confirm_dialog

    PageManager.get_page().open(confirm_dialog)


# FUNÇÃO PARA ABRIR A PASTA ONDE ESTÃO OS ARQUIVOS EXCEL GERADOS
def open_folder(_):
    from controls.components import snack_show

    folder_path = os.path.join(os.path.expanduser('~'), 'Documents', name_folder)

    if os.path.exists(folder_path):
        try:
            subprocess.Popen(f'explorer {folder_path}')
        except Exception as e_:
            print(e_)
            snack_show(
                message=f'Erro ao abrir a pasta {folder_path}',
                icon=ft.icons.RULE_FOLDER,
                icon_color=ft.colors.ERROR
            )


def open_file_excel(path_file_excel):
    from controls.components import snack_show

    if os.path.exists(path_file_excel):
        quoted_path = shlex.quote(path_file_excel)
        command = ['powershell.exe', '-Command', f'Start-Process -FilePath {quoted_path}']

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            snack_show(
                message=f'Erro ao abrir o arquivo {path_file_excel}',
                icon=ft.icons.RULE_FOLDER,
                icon_color=ft.colors.ERROR
            )
            print(f'Erro ao abrir o arquivo {path_file_excel}: {e} ')


# FUNÇÃO QUE FORMATA O NÚMERO DO CPF INSERINDO '.' e '-'
# RETORNANDO O NÚMERO NO FORMATO ###.###.###-##
def format_cpf(cpf_field: ft.TextField) -> str:
    # Remove os espaços em branco, caso existam,
    # no número do CPF e atribui a string à variável CPF
    cpf = cpf_field.value.strip()
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


# FUNÇÃO QUE CUSTOMIZA O ESTILHO DE CORES DOS BOTÕES DA APLICAÇÃO
def button_style(btn_name: str = '') -> ft.ButtonStyle:
    # Se o argumento nome for igual a 'OK', aplica uma formatação
    if btn_name == 'OK':
        return ft.ButtonStyle(
            shape={
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=5)
            },
            bgcolor={
                ft.ControlState.DEFAULT: '#5a90fc',
                ft.ControlState.HOVERED: ft.colors.BLUE_ACCENT_400,
            },
            color={
                ft.ControlState.DEFAULT: '#abb2bf',
                ft.ControlState.HOVERED: ft.colors.WHITE
            },
        )
    # Se não, aplica outra formatação
    else:
        return ft.ButtonStyle(
            shape={
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=5)
            },
            bgcolor={
                ft.ControlState.DEFAULT: '#2b2d30',
                ft.ControlState.HOVERED: '#aac0d5',
            },
            color={
                ft.ControlState.DEFAULT: '#abb2bf',
                ft.ControlState.HOVERED: ft.colors.WHITE
            }
        )


# FUNÇÃO QUE ATUALIZA O ESTADO DA BARRA DE PROGRESSO
def update_progress(
        # page: ft.Page,
        progress_bar: ft.ProgressBar,
        total_time: float,
        message: str,
        status: bool,
):
    # Importa função (progress_control) do módulo controls
    from controls.components import progress_control

    # Atribui à variável (control) a função (progress_control)
    # que retorna um controle com a barra de progresso
    control = progress_control(
        progress_bar=progress_bar,
        message=message
    )

    # Exibe o controle com a barra de progresso na página
    PageManager.get_page().overlay.append(control)

    # Atribui à variável (start) o tempo atual do sistema
    start = time()

    # Até que o argumento (status) no índice (0) seja
    # falso, atualiza a barra de progresso
    while not status[0]:
        elapsed = time() - start
        progress = min(elapsed / total_time, 1)
        progress_bar.value = progress
        PageManager.get_page().update()
        sleep(0.15)

    progress_bar.value = 1
    PageManager.get_page().update()

    # Remove o controle da barra de progresso e atualiza a página
    PageManager.get_page().overlay.remove(control)
    PageManager.get_page().update()


# FUNÇÃO QUE CONTROLA A BARRA DE PROGRESSO DURANTE A OPERAÇÃO DE LOGIN
def start_login(
        # page: ft.Page,
        total_time: float = 0,
        message: str = '',
):
    # Atribui a variável (progress_bar) uma instância da barra de progresso
    progress_bar = ft.ProgressBar(width=600, color='#5a90fc', value=0.0)
    # Cria um array booleano, atribui o valor
    # false e atribui à variável (status)
    status = [False]

    # Cria uma (Thread) para chamar a função (update_progress) em paralelo
    threading.Thread(target=update_progress, args=(
        # page,
        progress_bar,
        total_time,
        message,
        status
    )).start()

    # Espera o tempo setado na variável (total_time)
    sleep(total_time)
    # Atribui ao índice '0' do array (status) o valor TRUE
    status[0] = True


# FUNÇÃO QUE EXIBE A BARRA DE PROGRESSO DURANTE A
# OPERAÇÃO DE SCRAPING (LEITURA DOS DADOS) NO HTML
# def data_progress_bar(page: ft.Page):
def data_progress_bar():
    # Importa a função (progress_control) do módulo controls
    from controls.components import progress_control, snack_show

    try:
        # Atribui a variável (progress_bar) uma instância da barra de progresso
        progress_bar = ft.ProgressBar(width=600, color='#5a90fc')

        # Atribui à variável (control) a função (progress_control)
        # que retorna um controle com a barra de progresso
        control = progress_control(
            progress_bar=progress_bar,
            message='Gerando arquivo. AGUARDE...',
        )

        # Exibe a barra de progresso e atualiza a página
        PageManager.get_page().overlay.append(control)
        PageManager.get_page().update()

    except Exception as e_:
        snack_show(
            message='Erro ao exibir a barra de progresso!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao exibir a barra de progresso: {e_}')
