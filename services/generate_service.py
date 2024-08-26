from datetime import datetime

import flet as ft

from services.authenticate_service import login
from utils.extractor_data import data_fetch
from utils.share_model import data_progress_bar


def file_generate(*args):
    from utils.validators import (
        validate_cpf, validate_dates, format_cpf
    )

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

        # Extrai o mês e o ano das datas inicial e final atribuindo os
        # resultados às variáveis (month_start, year_start, month_end, year_end)
        month_start = start_date.month
        year_start = start_date.year
        month_end = end_date.month
        year_end = end_date.year

        # Atribui a variável driver o valor do argumento
        # driver guardado na session do Flet.
        driver = e.page.session.get('driver')

        # Atribui à variável (data_dict), um dicionário com as chaves
        # e valores que serão repassados para a função (get_data)
        data_dict: dict = {
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

        # Verifica se existe o argumento driver na sessão do Flet.
        # Se NÃO, chama a função 'login' do módulo 'authenticate'
        # que retorna uma instância do driver do navegador e
        # armazena a instância retornada na sessão do Flet
        if driver is None:
            if driver := login(e):
                # driver.minimize_window()
                e.page.session.set('driver', driver)

                # Seta o valor do driver no dicionário (data_dict)
                data_dict['driver'] = driver

                # Chama a função local (get_data) passando
                # o dicionário como argumento
                get_data(**data_dict)

        else:
            # Seta o valor do driver no dicionário (data_dict)
            data_dict['driver'] = driver

            # Chama a função local (get_data) passando
            # o dicionário como argumento
            get_data(**data_dict)


# FUNÇÃO QUE CHAMA O 'SCRAPING' NO HTML
def get_data(**kwargs):
    # Importa as funções dos módulos utils e controls
    from utils.validators import clear_form
    from controls.components import snack_show

    # Cria um dicionário com parte dos dados vindos no atributo **kwargs
    dic_data_fetch: dict = {
        k: v for k, v in kwargs.items() if k in [
            'page', 'cpf', 'month_start', 'year_start', 'month_end', 'year_end', 'driver'
        ]
    }

    # Cria outro dicionário com os dados restantes vindos no atributo **kwargs
    dic_clear_form = {
        k: v for k, v in kwargs.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field'
        ]
    }

    # Atribui a variável (page) o valor da chave 'page' do dicionário (dic_data_fetch)
    page = dic_data_fetch.get('page')

    # Transforma o dicionário (dic_data_fetch) numa tupla apenas
    # com os valores e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dic_data_fetch.values())

    # Chama a função que exibe a barra de progresso
    data_progress_bar(page=page)

    # Chama a função que busca os dados passando a tupla como
    # argumento e atribui o retorno (um booleano) à variável result
    result = data_fetch(*tuple_data_fetch)

    # Se resulto for TRUE, remove da página a barra de progresso e atualiza a página
    if result:
        page.overlay.pop()
        page.update()

        # Limpa o formulário
        clear_form(**dic_clear_form)

        # Se não houver erros no processamento, exibe mensagem de sucesso
        snack_show(
            page=page,
            message='Arquivo criado com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )
