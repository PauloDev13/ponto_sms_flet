import flet as ft
from time import sleep
from datetime import datetime

# Variável global
container_snackbar = None


# Função que insere '.' e '-' no número do CPF, caso tenha sido
# informado somente números.
def format_cpf(cpf: str) -> str:
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def validate_date_format(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%m/%Y')
        return date_obj
    except ValueError:
        return None


# Função para validar as datas
def validate_dates(e, date_start, date_end):
    try:
        start_date = validate_date_format(date_start)
        end_date = validate_date_format(date_end)

        if not date_start:
            snack_show(e.page, 'A data inicial é obrigatória!')
            return False
        elif start_date is None:
            snack_show(e.page, f'A data inicial ({date_start})  é inválida!')
            return False

        if not date_end:
            snack_show(e.page, 'A data final é obrigatória!')
            return False
        elif end_date is None:
            snack_show(e.page, f'A data final ({date_end})  é inválida!')
            return False

        if start_date > end_date:
            snack_show(e.page,
                       f'A data inicial {start_date.date().strftime('%d/%m/%Y')} deve ser \n'
                       f'anterior a data final {end_date.date().strftime('%d/%m/%Y')}')
            return False
        return True
    except Exception as ex:
        print(f'Erro stacktrace: {ex}')


# Função para validar o CPF
def validate_cpf(e, cpf):
    try:
        if not cpf:
            snack_show(e.page, 'O CPF é obrigatório!')
            return False

        if not cpf.isdigit():
            snack_show(e.page, 'O CPF deve conter somente números!')
            return False

        if len(cpf) != 11:
            snack_show(e.page, 'CPF inválido!', ft.icons.WARNING)
            return False

        if cpf == cpf[0] * 11:
            snack_show(e.page, 'CPF inválido!', ft.icons.WARNING)
            return False

        # Calcula o primeiro dígito verificador
        sum_ = sum(int(cpf[i]) * (10 - i) for i in range(9))
        first_digit = (sum_ * 10 % 11) % 10

        # Calcula o segundo dígito verificador
        sum_ = sum(int(cpf[i]) * (11 - i) for i in range(10))
        second_digit = (sum_ * 10 % 11) % 10

        # Verifica se os dígitos calculados são iguais aos dígitos verificadores do CPF
        if first_digit == int(cpf[9]) and second_digit == int(cpf[10]):
            return True
        else:
            snack_show(e.page, 'CPF inválido!', ft.icons.WARNING, ft.colors.RED)
            return False
    except Exception as ex:
        print(f'Erro stacktrace: {ex}')


# def validate_form(e, cpf_field, start_date_field, end_date_field) -> None:
def validate_form(e, cpf_field, start_date_field, end_date_field) -> None:
    cpf = cpf_field.value
    start_date = start_date_field.value
    end_date = end_date_field.value

    cpf_is_valid = validate_cpf(e, cpf)

    if cpf_is_valid:
        cpf = format_cpf(cpf)
        dates_is_valid = validate_dates(e, start_date, end_date)

    if cpf_is_valid and dates_is_valid:
        start_date = f'01/{start_date}'
        end_date = f'01/{end_date}'
        print(cpf, start_date, end_date)

        clear_form(cpf_field, start_date_field, start_date_field)


def snack_show(
    page: ft.Page,
    message: str,
    icon_name=ft.icons.INFO_ROUNDED,
    bg_color=ft.colors.AMBER_200,
) -> None:

    global container_snackbar

    if container_snackbar is None:
        container_snackbar = message_snackbar(icon_name, bg_color)
        page.add(container_snackbar)

    container_snackbar.content.controls[0].name = icon_name
    container_snackbar.content.controls[1].value = message
    container_snackbar.bgcolor = bg_color
    container_snackbar.visible = True
    container_snackbar.opacity = 0.6
    container_snackbar.update()

    sleep(3)
    hide_snackbar()


def hide_snackbar() -> None:
    if container_snackbar is not None:
        container_snackbar.opacity = 0.0
        container_snackbar.update()
        sleep(0.3)
        container_snackbar.visible = False,
        container_snackbar.update()


def clear_form(cpf_field, start_date_field, end_date_field) -> None:
    cpf_field.value = ''
    start_date_field.value = ''
    end_date_field.value = ''

    cpf_field.update()
    start_date_field.update()
    end_date_field.update()


def message_snackbar(icon_name: str, bg_color: str):
    return ft.Container(
        content=ft.Row([
            ft.Icon(
                name=icon_name,
                size=40,
                color=ft.colors.BLUE
            ),
            ft.Text(
                size=20,
                expand=True,
                color=ft.colors.BLACK,
            )
        ]),
        width=600,
        bgcolor=bg_color,
        padding=10,
        border_radius=5,
        visible=False,
        opacity=0.0,
        animate_opacity=300,
    )
