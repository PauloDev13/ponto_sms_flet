from datetime import datetime

import flet as ft

from services.generate_service import file_generate
from utils.share_model import format_cpf, clear_form


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
    # Importa a função (snack_show) do módulo (controls.components)
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

