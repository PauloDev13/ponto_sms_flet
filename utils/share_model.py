import flet as ft
from time import sleep, time
import threading


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


# FUNÇÃO QUE EXIBE A CAIXA DE DIÁLOGO PARA CONFIRMAR A SAÍDA DO APLICATIVO
def close_app(e):
    from controls.components import confirm_dialog

    e.page.open(confirm_dialog)


# FUNÇÃO QUE FORMATA O NÚMERO DO CPF INSERINDO '.' e '-'
# RETORNANDO O NÚMERO NO FORMATO ###.###.###-##
def format_cpf(cpf_field: ft.TextField) -> str:
    cpf = cpf_field.value
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
                ft.ControlState.DEFAULT:ft.RoundedRectangleBorder(radius=5)
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
        page: ft.Page,
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
    page.overlay.append(control)

    # Atribui à variável (start) o tempo atual do sistema
    start = time()

    # Até que o argumento (status) no índice (0) seja
    # falso, atualiza a barra de progresso
    while not status[0]:
        elapsed = time() - start
        progress = min(elapsed / total_time, 1)
        progress_bar.value = progress
        page.update()
        sleep(0.15)

    progress_bar.value = 1
    page.update()

    # Remove o controle da barra de progresso e atualiza a página
    page.overlay.remove(control)
    page.update()


# FUNÇÃO QUE CONTROLA A BARRA DE PROGRESSO DURANTE A OPERAÇÃO DE LOGIN
def start_login(
        page: ft.Page,
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
        page,
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
def data_progress_bar(page: ft.Page):
    # Importa a função (progress_control) do módulo controls
    from controls.components import progress_control

    # Atribui a variável (progress_bar) uma instância da barra de progresso
    progress_bar = ft.ProgressBar(width=600, color='#5a90fc')

    # Atribui à variável (control) a função (progress_control)
    # que retorna um controle com a barra de progresso
    control = progress_control(
        progress_bar=progress_bar,
        message='Gerando arquivo. AGUARDE...',
    )

    # Exibe a barra de progresso e atualiza a página
    page.overlay.append(control)
    page.update()



