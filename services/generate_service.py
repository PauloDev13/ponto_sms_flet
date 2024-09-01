from datetime import datetime

import flet as ft

from models.page_manager import PageManager
# Importações dos módulos locais
from services.authenticate_service import login
from utils.extractor_data import data_fetch
from utils.share_model import (
    data_progress_bar, open_file_excel, format_cpf, clear_form
)


# FUNÇÃO QUE CHAMA O INÍCIO DO SCRAPING NA PÁGINA DO PONTO PARA BUSCAR OS DADOS
def file_generate(*args):

    # Importa as funções (validate_cpf, validate_dates) do módulo (utils.validators)
    from utils.validators import (
        validate_cpf, validate_dates
    )

    # Desempacota os argumentos enviados através do argumento (*args)
    cpf_field, start_date_field, end_date_field = args

    # Valida o CPF e atribui o resulta (booleano) à variável (cpf_is_valid)
    cpf_is_valid = validate_cpf(cpf_field)

    # Declara a variável local (dates_is_valid) com valor inicial False
    dates_is_valid: bool = False

    # Se o CPF for válido
    if cpf_is_valid:

        # Valida as datas inicial e final  e atribui o resultado
        # (booleano) à variável local (dates_is_valid)
        dates_is_valid = validate_dates(
            start_date_field,
            end_date_field
        )

    # Se as datas e o CPF forem válidas, pega os valores das datas inicial e final
    if cpf_is_valid and dates_is_valid:
        #  Usa a função (format_cpf) para formatar o CPF aplicando a máscara (###.###.###-##)
        cpf = format_cpf(cpf_field)

        # Atribui às variáveis (start_date e end_date) os valores dos
        # controles (start_date_field e end_date_field) do formulário
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

        # Atribui à variável driver o valor do argumento
        # driver guardado na session do Flet.
        driver = PageManager.get_page().session.get('driver')

        # Atribui à variável (data_dict), um dicionário, as chaves
        # e valores que serão repassados para a função (get_data)
        data_dict: dict = {
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
        # Se não existir, chama a função 'login()' do módulo 'authenticate'
        # que retorna uma instância do driver do navegador e
        # armazena a instância retornada na sessão do Flet
        if driver is None:
            if driver := login():
                PageManager.get_page().session.set('driver', driver)

                # Seta o valor do driver no dicionário (data_dict)
                data_dict['driver'] = driver

                # Chama a função local (get_data) passando o dicionário como argumento.
                # Se não houver erros, a função retorna o caminho completo onde o arquivo
                # do Excel foi criado e atribui o resultado à variável (path_file)
                path_file = get_data(**data_dict)

                # Chama a função (open_file_excel) passando como argumento o
                # caminho do arquivo Excel. Essa função abre o arquivo com o
                #  programa padrão para arquivos .xlsx configurado no Windows
                open_file_excel(path_file)

        # Se já existir uma instância do navegador (driver) na sessão
        # do Flet, repete o mesmo processo realizado na instrução IF anterior
        else:
            data_dict['driver'] = driver
            path_file = get_data(**data_dict)
            open_file_excel(path_file)


# FUNÇÃO QUE INICIA A BUSCA DOS DADOS NO HTML DO SISTEMA DE PONTO
def get_data(**kwargs):
    # Importa a função (snack_show) do módulo
    # (controls.components) para exibir mensagens
    from controls.display.snack_bar import snack_show

    # Desempacota parte dos dados vindos no atributo (**kwargs) através de
    # um loop e atribui os valores à variável (dic_data_fetch), um dicionário
    dic_data_fetch: dict = {
        k: v for k, v in kwargs.items() if k in [
            'cpf', 'month_start', 'year_start', 'month_end', 'year_end', 'driver'
        ]
    }

    # Desempacota o restante dos dados vindos no atributo (**kwargs) através de
    # um loop e atribui os valores à variável (dic_clear_form), um dicionário
    dic_clear_form = {
        k: v for k, v in kwargs.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field'
        ]
    }

    # Transforma o dicionário (dic_data_fetch) numa tupla apenas
    # com os valores, sem as chaves, e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dic_data_fetch.values())

    # Chama a função (data_progress_bar()) que exibe a barra de
    # progresso até que função (data_fetch) retorne o resultado
    data_progress_bar()

    # Chama a função (data_fetch) que busca os dados passando a tupla (tuple_data_fetch)
    #  como argumento e atribui o retorno (str ou None) à variável result
    result = data_fetch(*tuple_data_fetch)

    # Se result for diferente de None..
    if result:
        # Remove da página a barra de progresso e atualiza a página
        PageManager.get_page().overlay.pop()
        PageManager.get_page().update()

        # Chama a função (clear_form) passando a tupla (dic_clear_form).
        # Essa função limpa os controles do formulário
        clear_form(**dic_clear_form)

        # Se não houver erros no processamento, exibe mensagem de sucesso
        snack_show(
            message='Arquivo criado com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    # Retornar a variável (result)
    return result
