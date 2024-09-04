from datetime import datetime

import flet as ft

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from models.page_manager import PageManager
from services.authenticate_service import login
from services.create_pdf_service import generate_pdf
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
    # cpf_field, start_date_field, end_date_field = args

    (checkbox_excel_field,
     checkbox_pdf_field,
     cpf_field,
     start_date_field,
     end_date_field
     ) = args

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
            'end_date_field': end_date_field,
            'checkbox_excel': checkbox_excel_field,
            'checkbox_pdf': checkbox_pdf_field,
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

                create_pdf_and_excel_files(**data_dict)

        # Se já existir uma instância do navegador (driver) na sessão
        # do Flet, repete o mesmo processo realizado na instrução IF anterior
        else:
            data_dict['driver'] = driver
            create_pdf_and_excel_files(**data_dict)
            # path_file = get_data(**data_dict)
            # open_file_excel(path_file)


def create_pdf_and_excel_files(**kwargs):

    checkbox_excel = kwargs['checkbox_excel'].value
    checkbox_pdf = kwargs['checkbox_pdf'].value

    # Desempacota parte dos dados vindos no atributo (**kwargs) através de
    # um loop e atribui os valores à variável (dic_data_fetch), um dicionário
    dict_data_fetch: dict = {
        k: v for k, v in kwargs.items() if k in [
            'cpf',
            'month_start',
            'year_start',
            'month_end',
            'year_end',
            'driver'
        ]
    }

    # Desempacota o restante dos dados vindos no atributo (**kwargs) através de
    # um loop e atribui os valores à variável (dic_clear_form), um dicionário
    dict_clear_form = {
        k: v for k, v in kwargs.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field'
        ]
    }

    if checkbox_excel and not checkbox_pdf:
        # path_file = get_data(dict_data_fetch, dict_clear_form)
        path_file = get_data(dict_data_fetch, dict_clear_form)

        # Chama a função (open_file_excel) passando como argumento o
        # caminho do arquivo Excel. Essa função abre o arquivo com o
        #  programa padrão para arquivos .xlsx configurado no Windows
        open_file_excel(path_file)

    if checkbox_excel and checkbox_pdf:
        get_data_pdf(dict_data_fetch)
        get_data(dict_data_fetch, dict_clear_form)

    if not checkbox_excel and checkbox_pdf:
        get_data_pdf(dict_data_fetch, dict_clear_form)

    if not checkbox_excel and not checkbox_pdf:
        AlertSnackbar.show(
            message='Selecione o tipo de arquivo a ser gerado',
        )


def get_data_pdf(dict_data: dict, dict_clear: dict = None):
    print('CHEGOU NO GET DATA PDF')
    # Transforma o dicionário (dic_data_fetch) numa tupla apenas
    # com os valores, sem as chaves, e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dict_data.values())

    data_progress_bar('Gerando arquivo em PDF. AGUARDE...')

    result = generate_pdf(*tuple_data_fetch)

    if result:
        # Remove da página a barra de progresso e atualiza a página
        PageManager.get_page().overlay.pop()
        PageManager.get_page().update()

        # Chama a função (clear_form) passando a tupla (dic_clear_form).
        # Essa função limpa os controles do formulário
        if dict_clear:
            clear_form(**dict_clear)

        # Se não houver erros no processamento, exibe mensagem de sucesso
        AlertSnackbar.show(
            message='Arquivo PDF criado com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    # return result


# FUNÇÃO QUE INICIA A BUSCA DOS DADOS NO HTML DO SISTEMA DE PONTO
def get_data(dict_data: dict, dict_clear: dict):
    print('CHEGOU NO GET DATA EXCEL')

    # Transforma o dicionário (dic_data_fetch) numa tupla apenas
    # com os valores, sem as chaves, e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dict_data.values())

    # Chama a função (data_progress_bar()) que exibe a barra de
    # progresso até que função (data_fetch) retorne o resultado
    data_progress_bar('Gerando planilhas. AGUARDE...')

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
        clear_form(**dict_clear)

        # Se não houver erros no processamento, exibe mensagem de sucesso
        AlertSnackbar.show(
            message='Planilhas criadas com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    # Retornar a variável (result)
    return result
