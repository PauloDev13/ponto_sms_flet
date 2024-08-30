import os
import shlex
import subprocess
import threading
from time import sleep, time

import flet as ft
import pythoncom
import winshell
from dotenv import load_dotenv

# Importações dos módulos locais
from models.page_manager import PageManager

load_dotenv()
name_folder = os.getenv('NAME_FOLDER')

if not name_folder:
    raise ValueError("A chave (NAME_FOLDER) não está definido no .env")


# FUNÇÃO QUE LIMPA OS CONTROLES DO FORMULÁRIO
def clear_form(**kwargs) -> None:
    # Desestrutura o argumento (**kwargs) e atribui o resultado
    # à variável (dict_controls) dicionário
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

    # se o evento disparado for (close), abre a caixa de diálogo de confirmação
    if e.data == 'close':
        e.page.open(confirm_dialog)


# FUNÇÃO QUE CAPTURA QUANDO A TECLA (ENTER) É PRESSIONADA
def on_key_enter_event(e):
    # Importa o controle (generate_button)
    from controls.components import generate_button

    # Se a tecla pressionada for 'Enter', simula o click no botão
    if e.key == 'Enter':
        generate_button.on_click(e)


# FUNÇÃO QUE EXIBE A CAIXA DE DIÁLOGO PARA CONFIRMAR A SAÍDA DO APLICATIVO
def close_app(_):
    # Importa do módulo (controls) o controle (confirm_dialog)
    from controls.components import confirm_dialog

    # Abre a caixa de diálogo
    PageManager.get_page().open(confirm_dialog)


# FUNÇÃO PARA ABRIR A PASTA ONDE ESTÃO OS ARQUIVOS EXCEL GERADOS
def open_folder(_):
    from controls.components import snack_show

    # Atribui à variável (folder_path) o caminho do diretório onde são salvos os arquivos Excel
    folder_path = os.path.join(os.path.expanduser('~'), 'Documents', name_folder)

    # Se o diretório existir...
    if os.path.exists(folder_path):
        try:
            # Usa o subprocesso do windows para abrir o 'explorer' no diretório
            subprocess.Popen(f'explorer {folder_path}')
        except Exception as e_:
            print(e_)
            snack_show(
                message=f'Erro ao abrir a pasta {folder_path}',
                icon=ft.icons.RULE_FOLDER,
                icon_color=ft.colors.ERROR
            )

# FUNÇÃO QUE CRIA UM ATALHO NA ÁREA DE TRABALHO PARA
# A PASTA ONDE OS ARQUIVOS DO EXCEL SÃO SALVOS
def create_shortcut_to_desktop_folder(folder_path):
    # Inicializa o COM
    pythoncom.CoInitialize()

    try:
        # Define o nome do atalho
        shortcut_name = 'PLANILHAS_SMS'
        # Define que o atalho será criado em C:/users/<user windows>/Desktop
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        # Define o link do atalho
        shortcut_link = os.path.join(desktop_path, f'{shortcut_name}.lnk')

        with winshell.shortcut(shortcut_link) as shortcut:
            shortcut.path = folder_path
            shortcut.working_directory = folder_path
    finally:
        # Desinicializa o COM
        pythoncom.CoUninitialize()


# FUNÇÃO QUE ABRE O ARQUIVO EXCEL NO OS
def open_file_excel(path_file_excel):
    # Importa a função (snack_show) do módulo (controls.components) que exibe mensagens
    from controls.components import snack_show

    # Se o caminho para o arquivo existe...
    if os.path.exists(path_file_excel):

        # Abre o arquivo Excel
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


# FUNÇÃO QUE CUSTOMIZA O ESTILHO E AS CORES DOS BOTÕES DA APLICAÇÃO
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
    PageManager.get_page().overlay.remove(control)
    PageManager.get_page().update()


# FUNÇÃO QUE CONTROLA A BARRA DE PROGRESSO DURANTE A OPERAÇÃO DE LOGIN

def login_progess_bar(
        total_time: float = 0,
        message: str = '',
):
    # Atribui a variável (progress_bar) uma instância da barra de progresso
    progress_bar = ft.ProgressBar(width=600, color='#5a90fc', value=0.0)

    # Cria um array booleano co o valor False no seu
    # índice [0] e atribui à variável (status)
    status = [False]

    # Cria uma (Thread) para executar em paralelo a função (update_progress)
    threading.Thread(target=update_progress, args=(
        progress_bar,
        total_time,
        message,
        status
    )).start()

    # Espera o tempo setado na variável (total_time). Esse é o tempo
    # total que a barra de progresso ficará sendo exibida na página
    sleep(total_time)
    # Depois desse tmepo, Atribui ao índice [0] do array (status) o valor TRUE
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
