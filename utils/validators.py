from datetime import datetime

import flet as ft


# FUNÇÃO QUE FORMATA AS DATAS PARA 'MM/yyyy'
def validate_date_format(date_str: str) -> datetime | None:
    try:
        date_obj = datetime.strptime(date_str, '%m/%Y')
        return date_obj
    except ValueError:
        return None


# FUNÇÃO QUE VALIDA AS DATAS
def validate_dates(date_start_field: ft.TextField, date_end_field: ft.TextField):
    # Importa a função (snack_show) do módulo (controls) para exibir mensagens
    from controls.components import snack_show

    try:
        # Atribui às variáveis (date_start e date_end) o valor dos controles
        # (date_start_field e date_end_field) do formulário
        date_start = date_start_field.value
        date_end = date_end_field.value

        # Atribui às variáveis () o resultado da função ()
        # que verifica se o formato das datas é (MM/yyyy)
        start_date = validate_date_format(date_start_field.value)
        end_date = validate_date_format(date_end_field.value)

        # APLICA VALIDAÇÕES NOS CAMPOS DATAS
        if not date_start:
            date_start_field.focus()
            snack_show(message='A Data Inicial é obrigatória!')
            return False
        elif start_date is None:
            date_start_field.focus()
            snack_show(message=f'A Data Inicial ({date_start}) é inválida!')
            return False

        # Atribui à variável (start_year) o valor do ano extraído da variável (start_date)
        start_year = start_date.year

        if start_year < 2000:
            date_start_field.focus()
            snack_show(message=f'O Ano da Data Inicial deve ser igual ou maior que 2000')
            return False

        if not date_end:
            date_end_field.focus()
            snack_show(message='A Data Final é obrigatória!')
            return False
        elif end_date is None:
            date_end_field.focus()
            snack_show(message=f'A Data Final ({date_end}) é inválida!')
            return False

        # Atribui à variável (end_year) o valor do ano extraído da variável (end_date)
        end_year = end_date.year

        if end_year < 2000:
            date_end_field.focus()
            snack_show(message=f'O Ano da Data Final deve ser igual ou maior que 2000')
            return False

        if start_date > end_date:
            date_start_field.focus()
            snack_show(
                container_height=70,
                message=f'A Data Inicial {start_date.date().strftime('%d/%m/%Y')} deve ser '
                f'anterior a Data Final {end_date.date().strftime('%d/%m/%Y')}')
            return False
        return True
    except Exception as ex:
        snack_show(
            message='Erro ao validar datas!',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED,
            text_color=ft.colors.RED
        )
        print(f'Erro stacktrace: {ex}')


# FUNÇÃO QUE VALIDA O NÚMERO DO CPF
def validate_cpf(cpf_field: ft.TextField):
    # Importa a função (snack_show) do módulo (controls.components)
    from controls.components import snack_show

    # usa o método (strip()) para desconsiderar espaços em branco
    # no início e final digitados no controle CPF do formulário
    cpf = cpf_field.value.strip()

    # FAZ A VALIDAÇÃO DO NÚMERO DO CPF
    try:
        if not cpf:
            cpf_field.focus()
            snack_show(message='O CPF é obrigatório!')
            return False

        if not cpf.isdigit():
            cpf_field.focus()
            snack_show(message='O CPF deve conter somente números!')
            return False

        if len(cpf) != 11:
            cpf_field.focus()
            snack_show(
                message='CPF inválido!',
                icon=ft.icons.ERROR,
                icon_color=ft.colors.RED,
                text_color=ft.colors.RED
            )
            return False

        if cpf == cpf[0] * 11:
            cpf_field.focus()
            snack_show(
                message='CPF inválido!',
                icon=ft.icons.ERROR,
                icon_color=ft.colors.RED,
                text_color=ft.colors.RED
            )
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
            snack_show(
                message='CPF inválido!',
                icon=ft.icons.ERROR,
                icon_color=ft.colors.RED,
                text_color=ft.colors.RED
            )
            return False
    except Exception as ex:
        print(f'Erro stacktrace: {ex}')
