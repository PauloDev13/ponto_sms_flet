from datetime import datetime

import flet as ft

# Importações dos módulos locais
from services.data.data_service import search_data
from models.alert_snackbar import AlertSnackbar
from models.page_manager import PageManager
from services.authenticate_service import login
from services.create_pdf_service import generate_pdf
from utils.extractor_data import data_fetch
from utils.share_model import (
    data_progress_bar, open_file_excel, format_cpf, clear_form
)


# FUNÇÃO QUE CHAMA O INÍCIO DO SCRAPING NA PÁGINA DO PONTO PARA BUSCAR OS DADOS
def file_generate(dict_search_data: dict):
    # Importa as funções (validate_cpf, validate_dates) do módulo (utils.validators)
    from utils.validators import (
        validate_cpf, validate_dates, validate_type_file
    )

    # Atribui à variável (page) uma instância da página
    page = PageManager.get_page()

    # Desempacota os argumentos enviados através do dicionário (dict_search_data)
    (
        cpf_field,
        start_date_field,
        end_date_field,
        checkbox_excel_field,
        checkbox_pdf_field,
    ) = dict_search_data.values()

    # Valida o CPF e atribui o resulta (booleano) à variável (cpf_is_valid)
    cpf_is_valid = validate_cpf(cpf_field)

    # Declara a variável local (dates_is_valid) com valor inicial False
    dates_is_valid: bool = False
    type_file_valid: bool = False

    # Se o CPF for válido
    if cpf_is_valid:
        # Valida as datas inicial e final  e atribui o resultado
        # (booleano) à variável local (dates_is_valid)
        dates_is_valid = validate_dates(
            start_date_field,
            end_date_field
        )
        type_file_valid = validate_type_file(
            page=page,
            excel_field=checkbox_excel_field,
            pdf_field=checkbox_pdf_field
        )

    # Se as datas e o CPF forem válidas, pega os valores das datas inicial e final
    if cpf_is_valid and dates_is_valid and type_file_valid:
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

        # Atribui à variável (data_dict), um dicionário, chaves e valores
        data_dict: dict = {
            'cpf': cpf,
            'month_start': month_start,
            'year_start': year_start,
            'month_end': month_end,
            'year_end': year_end,
            'cpf_field': cpf_field,
            'start_date_field': start_date_field,
            'end_date_field': end_date_field,
            'checkbox_excel_field': checkbox_excel_field,
            'checkbox_pdf_field': checkbox_pdf_field,
            'driver': driver,
        }

        # Verifica se existe o argumento driver na sessão do Flet.
        # Se não existir, chama a função 'login()' do módulo 'authenticate'
        # que retorna uma instância do driver do navegador e
        if driver is None:
            if driver := login():
                # Armazena a instância retornada na sessão do Flet
                page.session.set('driver', driver)

                # Seta o valor do driver no dicionário (data_dict)
                data_dict['driver'] = driver

                show_progress_bar(
                    checkbox_excel_field.value,
                    checkbox_pdf_field.value,
                    data_dict
                )

        # Se já existir uma instância do navegador (driver) na sessão
        # do Flet, repete o mesmo processo realizado na instrução IF anterior
        else:
            data_dict['driver'] = driver

            show_progress_bar(
                checkbox_excel_field.value,
                checkbox_pdf_field.value,
                data_dict
            )


def show_progress_bar(file_excel: bool, file_pdf: bool, data_dict: dict):
    from services.create_pdf_service import array_pdf_files

    # Cria um dicionário com parte dos dados do dicionário (data_dict)
    dict_clear_form = {
        k: v for k, v in data_dict.items() if k in [
            'cpf_field', 'start_date_field', 'end_date_field'
        ]
    }

    # Atribui a variável (page) uma instância da página
    page = PageManager.get_page()

    if file_excel and not file_pdf:
        data_progress_bar('Criando planilhas. AGUARDE...')

    if file_pdf and not file_excel:
        data_progress_bar('Criando arquivo PDF. AGUARDE...')

    if file_excel and file_pdf:
        data_progress_bar('Criando planilha e arquivo PDF. AGUARDE...')

    result = search_data(dict_search_data=data_dict)

    if result:
        page.overlay.pop()
        page.update()

        TODO: 'VER ESSE CÓDIGO'
        array_pdf_files.clear()

    if file_excel and not file_pdf:
        # Se não houver erros no processamento, exibe mensagem de sucesso
        AlertSnackbar.show(
            message='Planilhas criadas com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    if file_pdf and not file_excel:
        # Se não houver erros no processamento, exibe mensagem de sucesso
        AlertSnackbar.show(
            message='Arquivo PDF criado com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    if file_excel and file_pdf:
        # Se não houver erros no processamento, exibe mensagem de sucesso
        AlertSnackbar.show(
            message='Planilhas e arquivo PDF criados com sucesso!',
            icon=ft.icons.CHECK_CIRCLE_SHARP,
            icon_color=ft.colors.GREEN
        )

    clear_form(dict_controls_fields=dict_clear_form)


# FUNÇÃO QUE CRIA OS ARQUIVOS EXCEL E PDF
def create_pdf_and_excel_files(**kwargs):
    # Atribui as variáveis (checkbox_excel e checkbox_pdf) o
    # valor das chaves passadas no argumento (**kwargs)
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

    # Se o checkbox (gerar planilha) foi marcado e o
    # checkbox (gerar arquivo PDF) NÃO foi marcado
    if checkbox_excel and not checkbox_pdf:
        # Chama a função que gera somente o arquivo Excel
        path_file = get_data_excel(dict_data_fetch, dict_clear_form)

        # Chama a função (open_file_excel) passando como argumento o
        # caminho do arquivo Excel. Essa função abre o arquivo com o
        #  programa padrão para arquivos .xlsx configurado no Windows
        open_file_excel(path_file)

    # Se os checkbox (gerar planilha e gerar arquivo PDF) foram marcados
    elif checkbox_excel and checkbox_pdf:
        # Chama as funções que geram os arquivos PDF e Excel
        get_data_pdf(dict_data_fetch)
        get_data_excel(dict_data_fetch, dict_clear_form)

    # Se apenas o checkbox (gerar aquivo PDF) foi marcado,
    elif not checkbox_excel and checkbox_pdf:
        # Chama a função que gera o arquivo PDF
        get_data_pdf(dict_data_fetch, dict_clear_form)

    # Se nenhum checkbox foi marcado, exibe mensagem de alerta
    # para que seja selecionado pelo menos um checkbox
    else:
        AlertSnackbar.show(
            message='Selecione o(s) arquivo(s) a ser(em) gerado(s)',
        )


# FUNÇÃO QUE INICIA O PROCESSO PARA CRIAR O ARQUIVO PDF
def get_data_pdf(dict_data: dict, dict_clear: dict = None):
    # Atribui à variável (page) uma instância da página
    page = PageManager.get_page()

    # Transforma o dicionário (dic_data) passado como argumento numa tupla apenas
    # com os valores, sem as chaves, e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dict_data.values())

    # Chama a função que exibe a barra de progresso
    data_progress_bar('Criando arquivo em PDF. AGUARDE...')

    # Chama a função que gera o PDF e atribui o
    # retorno (um booleano) á variável (result)
    result = generate_pdf(*tuple_data_fetch)

    # Se result for verdadeiro
    if result:
        # Remove a barra de progresso e atualiza a página
        page.overlay.pop()
        page.update()

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


# FUNÇÃO QUE INICIA O PROCESSO PARA CRIAR O ARQUIVO EXCEL
def get_data_excel(dict_data: dict, dict_clear: dict):
    # Atribui à variável (page) uma instância da página
    page = PageManager.get_page()

    # Transforma o dicionário (dic_data_fetch) numa tupla apenas
    # com os valores, sem as chaves, e atribui à variável (tuple_data_fetch)
    tuple_data_fetch = tuple(dict_data.values())

    # Chama a função que exibe a barra de progresso até
    # que função (data_fetch) retorne o resultado
    data_progress_bar('Criando planilhas. AGUARDE...')

    # Chama a função (data_fetch) que busca os dados passando a tupla (tuple_data_fetch)
    #  como argumento e atribui o retorno (str ou None) à variável result
    result = data_fetch(tuple_data_fetch)

    # Se result for diferente de None..
    if result:
        # Remove a barra de progresso e atualiza a página
        page.overlay.pop()
        page.update()

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
