"""Validação pura dos campos do formulário, desacoplada de Flet.

Espelha a lógica de utils/validators.py (CPF com dígitos verificadores,
datas MM/yyyy, unidade e tipo de arquivo) mas sem dependência de UI:
retorna dicionários JSON-friendly em vez de manipular controles e snackbars.

Usado pela API web /api/v1/validate e futuramente pelo frontend.
"""
from datetime import datetime


def validate_cpf(cpf: str) -> dict[str, str]:
    """Valida um CPF puro (11 dígitos + dígitos verificadores).

    Retorna {'ok': 'true'} ou {'ok': 'false', 'message': ...}.
    """
    cpf = (cpf or '').strip()

    if not cpf:
        return {'ok': 'false', 'message': 'O CPF é obrigatório!'}
    if not cpf.isdigit():
        return {'ok': 'false', 'message': 'O CPF deve conter somente números!'}
    if len(cpf) != 11:
        return {'ok': 'false', 'message': 'CPF inválido!'}
    if cpf == cpf[0] * 11:
        return {'ok': 'false', 'message': 'CPF inválido!'}

    sum_ = sum(int(cpf[i]) * (10 - i) for i in range(9))
    first_digit = (sum_ * 10 % 11) % 10
    sum_ = sum(int(cpf[i]) * (11 - i) for i in range(10))
    second_digit = (sum_ * 10 % 11) % 10

    if first_digit == int(cpf[9]) and second_digit == int(cpf[10]):
        return {'ok': 'true'}
    return {'ok': 'false', 'message': 'CPF inválido!'}


def validate_month_year(value: str) -> datetime | None:
    """Valida formato MM/yyyy. Retorna datetime ou None."""
    try:
        return datetime.strptime((value or '').strip(), '%m/%Y')
    except ValueError:
        return None


def validate_dates(date_start: str, date_end: str) -> dict[str, str]:
    """Valida o intervalo de períodos (MM/yyyy, ano >= 2000, início <= fim)."""
    start = validate_month_year(date_start)
    end = validate_month_year(date_end)

    if not (date_start or '').strip():
        return {'ok': 'false', 'message': 'O Período Inicial é obrigatório!'}
    if start is None:
        return {'ok': 'false', 'message': f'O Período Inicial ({date_start}) é inválido!'}
    if start.year < 2000:
        return {'ok': 'false', 'message': 'O Ano do Período Inicial deve ser igual ou maior que 2000!'}

    if not (date_end or '').strip():
        return {'ok': 'false', 'message': 'O Período Final é obrigatório!'}
    if end is None:
        return {'ok': 'false', 'message': f'O Período Final ({date_end}) é inválido!'}
    if end.year < 2000:
        return {'ok': 'false', 'message': 'O Ano do Período Final deve ser igual ou maior que 2000!'}

    if start > end:
        return {
            'ok': 'false',
            'message': (f'O Período Final {end.strftime("%d/%m/%Y")} deve ser posterior ao '
                        f'Período Inicial {start.strftime("%d/%m/%Y")}!'),
        }
    return {'ok': 'true'}


def validate_unit(unit: str) -> dict[str, str]:
    """Valida o código da unidade (obrigatório)."""
    if not (unit or '').strip():
        return {'ok': 'false', 'message': 'Informe o Código da Unidade!'}
    return {'ok': 'true'}


def validate_file_types(excel: bool, pdf: bool) -> dict[str, str]:
    """Valida que ao menos um tipo de arquivo foi selecionado."""
    if not excel and not pdf:
        return {'ok': 'false', 'message': 'Escolha pelo menos um tipo de arquivo a ser gerado!'}
    return {'ok': 'true'}


def validate_form(
        cpf: str,
        unit: str,
        date_start: str,
        date_end: str,
        excel: bool = False,
        pdf: bool = False,
) -> dict[str, object]:
    """Valida todas as entradas de uma só vez.

    Retorna {'valid': bool, 'errors': {campo: mensagem}, 'fields': {...}}.
    """
    errors: dict[str, str] = {}

    cpf_result = validate_cpf(cpf)
    if cpf_result.get('ok') == 'false':
        errors['cpf'] = cpf_result['message']

    unit_result = validate_unit(unit)
    if unit_result.get('ok') == 'false':
        errors['unit'] = unit_result['message']

    dates_result = validate_dates(date_start, date_end)
    if dates_result.get('ok') == 'false':
        message = dates_result['message']
        # Mapeia a mensagem única para o campo que a gerou
        if 'Inicial' in message and 'Final' not in message:
            errors['start_date'] = message
        elif 'Final' in message and 'Inicial' not in message:
            errors['end_date'] = message
        else:
            errors['end_date'] = message

    file_result = validate_file_types(excel, pdf)
    if file_result.get('ok') == 'false':
        errors['file_types'] = file_result['message']

    return {
        'valid': not errors,
        'errors': errors,
        'fields': {
            'cpf': cpf,
            'unit': unit,
            'date_start': date_start,
            'date_end': date_end,
            'excel': excel,
            'pdf': pdf,
        },
    }