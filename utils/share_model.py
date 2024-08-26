import flet as ft
from time import sleep, time
import threading


# Função que limpa os controles do formulário
def clear_form(
        cpf_field: ft.TextField,
        start_date_field: ft.TextField,
        end_date_field: ft.TextField
) -> None:
    cpf_field.value = ''
    start_date_field.value = ''
    end_date_field.value = ''

    cpf_field.focus()
    cpf_field.update()
    start_date_field.update()
    end_date_field.update()


# Função que captura o evento quando a janela principal do aplicativo é fechada
def window_event(e):
    from controls.components import confirm_dialog

    if e.data == 'close':
        e.page.open(confirm_dialog)


# Função que fecha a aplicação e
# encerra o driver após click no botão sair
def close_app(e):
    from controls.components import confirm_dialog
    e.page.open(confirm_dialog)


# Função que insere '.' e '-' no número do CPF, caso tenha sido
# informado somente números.
def format_cpf(cpf_field: ft.TextField) -> str:
    cpf = cpf_field.value
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def button_style(btn_name: str = '') -> ft.ButtonStyle:
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


def update_progress(
        page: ft.Page,
        progress_bar: ft.ProgressBar,
        total_time: float,
        message: str,
        status: bool,
):
    from controls.components import progress_control

    control = progress_control(
        progress_bar=progress_bar,
        message=message
    )

    page.overlay.append(control)

    start = time()

    while not status[0]:
        elapsed = time() - start
        progress = min(elapsed / total_time, 1)
        progress_bar.value = progress
        page.update()
        sleep(0.15)

    progress_bar.value = 1
    page.update()

    page.overlay.remove(control)
    page.update()


def start_login(
        page: ft.Page,
        total_time: float = 0,
        message: str = '',
):
    progress_bar = ft.ProgressBar(width=600, color='#5a90fc', value=0.0)
    status = [False]

    threading.Thread(target=update_progress, args=(
        page,
        progress_bar,
        total_time,
        message,
        status
    )).start()

    sleep(total_time)
    status[0] = True


def data_progress_bar(page: ft.Page):
    from controls.components import progress_control

    progress_bar = ft.ProgressBar(width=600, color='#5a90fc')

    control = progress_control(
        message='Gerando arquivo. AGUARDE...',
        progress_bar=progress_bar
    )

    page.overlay.append(control)
    page.update()



