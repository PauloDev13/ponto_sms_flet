import flet as ft
from datetime import datetime

from services.authenticate_service import login
from utils.extractor_data import data_fetch
from utils.share_model import data_progress_bar


def file_generate(*args):
    from utils.validators import (
        validate_cpf, validate_dates, format_cpf
    )
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

    # Define o dicionário (data_dict)
    data_dict: dict = {}

    # Desempacota os argumentos enviados através do (*args)
    e, cpf_field, start_date_field, end_date_field = args

    cpf_is_valid = validate_cpf(e, cpf_field)

    # Valida o CPF
    if cpf_is_valid:
        # Valida as datas
        dates_is_valid = validate_dates(
            e,
            start_date_field,
            end_date_field
        )

    # Se Datas e CPF forem válidas, pega os valores de data inicial e final
    if cpf_is_valid and dates_is_valid:
        #  Se o CPF for válido, formata aplicando uma máscara
        cpf = format_cpf(cpf_field)

        start_date = start_date_field.value
        end_date = end_date_field.value

        # Transforma as datas do formato (MM/yyyy) para o formato (yyyy-MM-dd)
        start_date = datetime.strptime(start_date, '%m/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%Y').date()

        # Extrai o mês e o ano das datas inicial e final
        month_start = start_date.month
        year_start = start_date.year
        month_end = end_date.month
        year_end = end_date.year

        # Atribui a variável driver o valor do argumento
        # driver guardado na session do Flet.
        driver = e.page.session.get('driver')

        # Verifica se existe o argumento driver na sessão do Flet.
        # Se NÃO, chama a função 'login' do módulo 'authenticate'
        # que retorna uma instância do driver do navegador e
        # armazena a instância retornada na sessão do Flet
        if driver is None:
            if driver := login(e):
                driver.minimize_window()
                e.page.session.set('driver', driver)

                data_dict = {
                    'page': e.page,
                    'cpf': cpf,
                    'month_start': month_start,
                    'year_start': year_start,
                    'month_end': month_end,
                    'year_end': year_end,
                    'driver': driver,
                    'cpf_field': cpf_field,
                    'start_date_field': start_date_field,
                    'end_date_field': end_date_field
                }

                # Chama a função local (get_data)
                get_data(**data_dict)

        else:
            get_data(**data_dict)


def get_data(**kwargs):
    from utils.validators import clear_form
    from controls.components import snack_show

    dic_data_fetch = {
        k: v for k, v in kwargs.items() if k in [
            'page', 'cpf', 'month_start', 'year_start', 'month_end', 'year_end', 'driver'
        ]
    }

    dic_clear_form = {
        k: v for k, v in kwargs.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field'
        ]
    }

    page = dic_data_fetch.get('page')
    tuple_data_fetch = tuple(dic_data_fetch.values())

    data_progress_bar(page=page)

    result = data_fetch(
        *tuple_data_fetch,
    )

    if result:
        page.overlay.pop()
        page.update()

        # Limpa o formulário
        clear_form(
            dic_clear_form.get('cpf_field'),
            dic_clear_form.get('start_date_field'),
            dic_clear_form.get('end_date_field')
        )

        # Se não houver erros no processamento, exibe mensagem de sucesso
        snack_show(
            page=page,
            message='Arquivo criado com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )
