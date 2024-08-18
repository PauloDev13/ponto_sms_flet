import flet as ft
from time import sleep
from datetime import datetime

from services.generate_service import file_generate


# Função que insere '.' e '-' no número do CPF, caso tenha sido
# informado somente números.
def format_cpf(cpf_field: ft.TextField) -> str:
    cpf = cpf_field.value
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def validate_date_format(date_str: str) -> datetime | None:
    try:
        date_obj = datetime.strptime(date_str, '%m/%Y')
        return date_obj
    except ValueError:
        return None


# Função para validar as datas
def validate_dates(e, date_start_field: ft.TextField, date_end_field: ft.TextField):
    from controls.components import snack_show
    try:
        date_start = date_start_field.value
        date_end = date_end_field.value

        start_date = validate_date_format(date_start_field.value)
        end_date = validate_date_format(date_end_field.value)

        if not date_start:
            date_start_field.focus()
            snack_show(e.page, 'A Data Inicial é obrigatória!')
            return False
        elif start_date is None:
            date_start_field.focus()
            snack_show(e.page, f'A Data Inicial ({date_start}) é inválida!')
            return False

        start_year = start_date.year

        if start_year < 2000:
            date_start_field.focus()
            snack_show(e.page, f'O Ano da Data Inicial deve ser igual ou maior que 2000')
            return False

        if not date_end:
            date_end_field.focus()
            snack_show(e.page, 'A Data Final é obrigatória!')
            return False
        elif end_date is None:
            date_end_field.focus()
            snack_show(e.page, f'A Data Final ({date_end}) é inválida!')
            return False

        end_year = end_date.year

        if end_year < 2000:
            date_end_field.focus()
            snack_show(e.page, f'O Ano da Data Final deve ser igual ou maior que 2000')
            return False

        if start_date > end_date:
            date_start_field.focus()
            snack_show(
                e.page,
                f'A services inicial {start_date.date().strftime('%d/%m/%Y')} deve ser \n'
                f'anterior a services final {end_date.date().strftime('%d/%m/%Y')}')
            return False
        return True
    except Exception as ex:
        print(f'Erro stacktrace: {ex}')


# Função para validar o CPF
def validate_cpf(e, cpf_field: ft.TextField):
    from controls.components import snack_show
    cpf = cpf_field.value

    try:
        if not cpf:
            cpf_field.focus()
            snack_show(e.page, 'O CPF é obrigatório!')
            return False

        if not cpf.isdigit():
            cpf_field.focus()
            snack_show(e.page, 'O CPF deve conter somente números!')
            return False

        if len(cpf) != 11:
            cpf_field.focus()
            snack_show(e.page, 'CPF inválido!', ft.icons.WARNING)
            return False

        if cpf == cpf[0] * 11:
            cpf_field.focus()
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
            cpf_field.focus()
            snack_show(e.page, 'CPF inválido!', ft.icons.WARNING, ft.colors.RED)
            return False
    except Exception as ex:
        print(f'Erro stacktrace: {ex}')


# def validate_form(e, cpf_field, start_date_field, end_date_field) -> None:
def validate_form(
        e,
        cpf_field: ft.TextField,
        start_date_field: ft.TextField,
        end_date_field: ft.TextField
) -> None:
    cpf_is_valid = validate_cpf(e, cpf_field)

    if cpf_is_valid:
        cpf = format_cpf(cpf_field)
        dates_is_valid = validate_dates(
            e,
            start_date_field,
            end_date_field
        )

    if cpf_is_valid and dates_is_valid:
        start_date = start_date_field.value
        end_date = end_date_field.value

        start_date = datetime.strptime(start_date, '%m/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%Y').date()

        month_start = start_date.month
        year_start = start_date.year
        month_end = end_date.month
        year_end = end_date.year

        file_generate(e, cpf, month_start, year_start, month_end, year_end)

        # print(f'CPF: {cpf}\nMÊS INICIO: {month_start}\nANO INICIO: {year_start}')
        # print(F'MÊS FINAL: {month_end}\nANO FINAL: {year_end}')

        clear_form(cpf_field, start_date_field, end_date_field)

def clear_form(
        cpf_field: ft.TextField,
        start_date_field: ft.TextField,
        end_date_field: ft.TextField
) -> None:
    cpf_field.value = ''
    start_date_field.value = ''
    end_date_field.value = ''

    cpf_field.update()
    start_date_field.update()
    end_date_field.update()

