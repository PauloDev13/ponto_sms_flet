import os
import shlex
import subprocess
import threading
from time import sleep
from typing import Dict

import flet as ft
import pythoncom
import winshell

# Importações dos módulos locais
from config.config_env import NAME_FOLDER
from controls.display.progress_bar import progress_control
from controls.display.progress_bar import update_progress
from models.alert_snackbar import AlertSnackbar
from models.page_manager import PageManager


# FUNÇÃO QUE LIMPA OS CONTROLES DO FORMULÁRIO
def clear_form(dict_form_controls: Dict[str, ft.Control]) -> None:
    # Loop que limpa e atualiza todos os controles do formulário
    for key in dict_form_controls:
        if isinstance(dict_form_controls[key], ft.TextField):
            dict_form_controls[key].value = ''
            dict_form_controls[key].update()

        if isinstance(dict_form_controls[key], ft.Checkbox):
            dict_form_controls[key].value = False
            dict_form_controls[key].update()

    # Seta o focus para o controle CPF no formulário
    dict_form_controls.get('cpf_field').focus()


# FUNÇÃO QUE CAPTURA O EVENTO DISPARADO QUANDO A JANELA DA APLICAÇÃO É FECHADA
def window_event(e) -> None:
    # Importa do módulo (controls) o controle (confirm_dialog)
    from controls.display.confirm_dialog import confirm_dialog

    # se o evento disparado for (close), abre a caixa de diálogo de confirmação
    if e.data == 'close':
        e.page.open(confirm_dialog)


# FUNÇÃO QUE CAPTURA QUANDO A TECLA (ENTER) É PRESSIONADA
def on_key_enter_event(e) -> None:
    # Importa o controle (generate_button)
    from controls.buttons.elevated_button import generate_button

    # Se a tecla pressionada for 'Enter', simula o click no botão
    if e.key == 'Enter':
        generate_button.on_click(e)


# FUNÇÃO QUE EXIBE A CAIXA DE DIÁLOGO PARA CONFIRMAR A SAÍDA DO APLICATIVO
def close_app(_) -> None:
    # Atribui à variável (page) uma instância da página retornada pela classe (PageManager)
    page = PageManager.get_page()

    # Importa do módulo (controls) o controle (confirm_dialog)
    from controls.display.confirm_dialog import confirm_dialog

    # Abre a caixa de diálogo
    page.open(confirm_dialog)


# FUNÇÃO LOCAL PARA CRIAR O DIRETÓRIO ONDE SERÃO
# SALVOS OS ARQUIVOS DO EXCEL QUE SERÃO GERADOS
def create_folder(name_file: str) -> str:
    try:
        # Monta a caminho do diretório que será criado e atribui à variável (folder_path).
        # O caminho é: C:/users/<user do windows>/Documents/PLANILHAS_SMS
        folder_path = os.path.join(os.path.expanduser('~'), 'Documents', NAME_FOLDER)

        # Se o diretório não existir...
        if not os.path.exists(folder_path):
            # Cria o diretório
            os.makedirs(folder_path)

        # Monta o caminho completo para salvar o arquivo Excel.
        # C:/users/<user_do_windows>/Documents/PLANILHAS_SMS/<nome_arquivo.xlsx>
        # e atribui à variável (path_file_excel)
        path_file_excel = os.path.join(folder_path, name_file)

        # Chama a função que cria um atalho do diretório
        # na área de trabalho do usuário logado no OS
        create_shortcut_to_desktop_folder(folder_path)

        # Retorna o caminho completo do diretório com o nome do arquivo
        return path_file_excel

    except Exception as e:
        AlertSnackbar.show(
            message=f'Erro ao criar o arquivo {name_file}',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )

        print(f'Erro ao criar o arquivo {name_file} - {e}')


# FUNÇÃO PARA ABRIR A PASTA ONDE ESTÃO OS ARQUIVOS EXCEL GERADOS
def open_folder(_) -> None:
    # Atribui à variável (folder_path) o caminho do diretório onde são salvos os arquivos Excel
    folder_path = os.path.join(os.path.expanduser('~'), 'Documents', NAME_FOLDER)

    # Se o diretório existir...
    if os.path.exists(folder_path):
        try:
            # Usa o subprocesso do windows para abrir o 'explorer' no diretório
            subprocess.Popen(f'explorer {folder_path}')
        except Exception as e_:
            print(e_)
            AlertSnackbar.show(
                message=f'Erro ao abrir a pasta {folder_path}',
                icon=ft.icons.RULE_FOLDER,
                icon_color=ft.colors.ERROR
            )


# FUNÇÃO QUE CRIA UM ATALHO NA ÁREA DE TRABALHO PARA
# A PASTA ONDE OS ARQUIVOS DO EXCEL SÃO SALVOS
def create_shortcut_to_desktop_folder(folder_path) -> None:
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
def open_file_excel(path_file_excel) -> None:
    # Se o caminho para o arquivo existe...
    if os.path.exists(path_file_excel):

        # Abre o arquivo Excel
        quoted_path = shlex.quote(path_file_excel)
        command = ['powershell.exe', '-Command', f'Start-Process -FilePath {quoted_path}']

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            AlertSnackbar.show(
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
                ft.ControlState.DEFAULT: 'black',
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


# FUNÇÃO QUE CONTROLA A BARRA DE PROGRESSO DURANTE A OPERAÇÃO DE LOGIN
def login_progress_bar(
        total_time: float = 0,
        message: str | None = None,
) -> None:
    # Atribui a variável (progress_bar) uma instância da barra de progresso
    progress_bar = ft.ProgressBar(width=600, color='#5a90fc', value=0.0)
    countdown_text = ft.Text(value='', color='#abb2bf', size=20)

    # Cria um array booleano com o valor False no seu
    # índice [0] e atribui à variável (status)
    status = [False]

    # Cria uma (Thread) para executar em paralelo a função (update_progress)
    threading.Thread(target=update_progress, args=(
        progress_bar,
        countdown_text,
        total_time,
        message,
        status
    )).start()

    if message is None:
        control_count_down(
            total_time=total_time,
            control=countdown_text,
            status=status,
        )


# FUNÇÃO QUE CRIA UM CONTADOR PARA ESPECIFICAR O TEMPO QUE RESTA PARA O LOGIN
def control_count_down(total_time: float, control: ft.Control, status: bool) -> None:
    # Atribui à variável (page) uma instância da página retornada pela classe (PageManager)
    page = PageManager.get_page()

    for i in range(1, total_time + 1):

        elapsed_time = (total_time - i)

        if elapsed_time > 1:
            control.value = f'O login será concluído em {elapsed_time} segundos. AGUARDE...'
        else:
            control.value = f'O login será concluído em {elapsed_time} segundo. AGUARDE...'

        page.update()
        sleep(1)

    status[0] = True


# FUNÇÃO QUE EXIBE A BARRA DE PROGRESSO DURANTE A OPERAÇÃO DE
# SCRAPING (LEITURA DOS DADOS) NO HTML
def data_progress_bar(message: str) -> None:
    # Define a variável container como vazia
    container = ft.Container()
    # Importa a função (progress_control) do módulo controls
    # from controls.display.progress_bar import progress_control

    # Atribui à variável (page) uma instância da página retornada pela classe (PageManager)
    page = PageManager.get_page()

    try:
        # Atribui a variável (progress_bar) uma instância da barra de progresso
        progress_bar = ft.ProgressBar(width=600, color='#5a90fc')

        # Atribui à variável (control) a função (progress_control)
        # que retorna um controle com a barra de progresso
        container = progress_control(
            progress_bar=progress_bar,
            control_count_down= ft.Text(value=''),
            message=message,
        )

        # Exibe a barra de progresso e atualiza a página
        page.overlay.append(container)
        page.update()

    except Exception as e_:
        # # Exibe a barra de progresso e atualiza a página
        page.overlay.remove(container)
        page.update()

        AlertSnackbar.show(
            message='Erro ao exibir a barra de progresso!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao exibir a barra de progresso: {e_}')
