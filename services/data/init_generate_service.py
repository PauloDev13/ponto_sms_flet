from datetime import datetime

import flet as ft
from selenium.webdriver.chrome import webdriver

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from models.page_manager import PageManager
from services.authenticate_service import login
from services.data.data_search_service import search_data
from utils.share_model import (
    data_progress_bar, clear_form
)
from utils.validators import (
    validate_form
)


# FUNÇÃO QUE APLICA VALIDAÇÃO DOS CONTROLES DO FORMULÁRIO, CHAMA O PROCESSO DE LOGIN
# E CHAMA A FUNÇÃO QUE INICIA A BUSCA DE DADOS E CRIAÇÃO DOS ARQUIVOS EXCEL E PDF
def init_generate_files(dict_search_data: dict):
    # Atribui à variável (page) uma instância da página
    page = PageManager.get_page()

    # Desempacota os argumentos enviados através do dicionário (dict_search_data)
    (
        cpf_field,
        unit_field,
        start_date_field,
        end_date_field,
        checkbox_excel_field,
        checkbox_pdf_field,
    ) = dict_search_data.values()

    # Se todos controles do formulário estão válidos
    if validate_form(page=page, form_fields=dict_search_data):
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
        driver: webdriver = page.session.get('driver')

        # Atribui à variável (data_dict), um dicionário, valores
        # atribuídos às variáveis após as validações
        data_dict: dict = {
            # 'cpf': cpf,
            'cpf_field': cpf_field,
            'unit_field': unit_field,
            'month_start': month_start,
            'year_start': year_start,
            'month_end': month_end,
            'year_end': year_end,
            'start_date_field': start_date_field,
            'end_date_field': end_date_field,
            'checkbox_excel_field': checkbox_excel_field,
            'checkbox_pdf_field': checkbox_pdf_field,
            'driver': driver,
        }

        try:
            # Verifica se existe o argumento driver na sessão do Flet.
            # Se não existir, chama a função 'login()' do módulo 'authenticate'
            # que retorna uma instância do driver do navegador e
            if driver is None:
                if driver := login():
                    # Armazena a instância retornada na sessão do Flet
                    page.session.set('driver', driver)

                    # Seta o valor do driver no dicionário (data_dict)
                    data_dict['driver'] = driver

                    # Chama a função (init_search_files) responsável iniciar a busca de dados
                    init_search_data(
                        checkbox_excel_field.value,
                        checkbox_pdf_field.value,
                        data_dict
                    )

            # Se já existir uma instância do navegador (driver) na sessão
            # do Flet, repete o mesmo processo realizado na instrução IF anterior
            else:
                data_dict['driver'] = driver

                init_search_data(
                    checkbox_excel_field.value,
                    checkbox_pdf_field.value,
                    data_dict
                )

        except Exception as e:
            page.overlay.pop()
            page.update()

            AlertSnackbar.show('Ocorreu um erro inesperado. Tente novamente')
            print('Erro inesperado', e)


# FUNÇÃO QUE CONTROLA A EXIBIÇÃO DA BARRA DE PROGRESSO
# DURANTE O PROCESSO DE CRIAÇÃO DOS ARQUIVOS EXCEL E PDF
def init_search_data(file_excel: bool, file_pdf: bool, data_dict: dict):
    # Importa a variável (array_pdf_files) dp módulo (create_pdf_service)
    from services.data.generate_pdf_service import array_pdf_files

    # Cria um dicionário com parte dos dados do dicionário (data_dict)
    dict_clear_form = {
        k: v for k, v in data_dict.items() if k in [
            'cpf_field', 'unit_field', 'start_date_field', 'end_date_field'
        ]
    }

    # Atribui a variável (page) uma instância da página
    page = PageManager.get_page()

    # Se a opção (gerar planilha) está MARCADA
    # e (gerar arquivo PDF) está DESMARCADA
    if file_excel and not file_pdf:
        # Exibe a barra de progresso com mensagem específica
        data_progress_bar('Criando planilhas. AGUARDE...')

    # Se a opção (gerar arquivo PDF) está MARCADA
    #  e (gerar planilha) está DEMARCADA
    if file_pdf and not file_excel:
        # Exibe a barra de progresso com mensagem específica
        data_progress_bar('Criando arquivo PDF. AGUARDE...')

    # Se as opções (gerar planilha) e (gerar arquivo PDF) estão MARCADAS
    if file_excel and file_pdf:
        # Exibe a barra de progresso com mensagem específica
        data_progress_bar('Criando planilha e arquivo PDF. AGUARDE...')

    # Atribui a variável (result) o retorno da função (search_data). Esta
    # função é responsável por retorna uma tupla (string, bool) | None e
    result = search_data(dict_search_data=data_dict)

    # Se result for diferente de None
    if result:
        # Exclui a barra de progresso e atualiza a página
        page.overlay.pop()
        page.update()

        # Se a opção (gerar planilha) está MARCADA
        # e (gerar arquivo PDF) está DESMARCADA
        if file_excel and not file_pdf:
            # Exibe mensagem de sucesso específica
            AlertSnackbar.show(
                message='Planilhas criadas com sucesso!',
                icon=ft.icons.CHECK_CIRCLE_SHARP,
                icon_color=ft.colors.GREEN
            )

            # Minimiza a janela da aplicação e atualiza a página
            page.window.minimized = True
            page.update()

            # print('PASSOU PELO MINIMIZED')

        # Se a opção (gerar arquivo PDF) está MARCADA
        #  e (gerar planilha) está DEMARCADA
        if file_pdf and not file_excel:
            # Exibe mensagem de sucesso específica
            AlertSnackbar.show(
                message='Arquivo PDF criado com sucesso!',
                icon=ft.icons.CHECK_CIRCLE_SHARP,
                icon_color=ft.colors.GREEN
            )

        # Se as opções (gerar planilha) e (gerar arquivo PDF) estão MARCADAS
        if file_excel and file_pdf:
            # Exibe mensagem de sucesso específica
            AlertSnackbar.show(
                message='Planilhas e arquivo PDF criados com sucesso!',
                icon=ft.icons.CHECK_CIRCLE_SHARP,
                icon_color=ft.colors.GREEN
            )

            # Minimiza a janela da aplicação e atualiza a página
            page.window.minimized = True
            page.update()

        # Limpa os controles do formulário após concluído o processo de gerar arquivos
        clear_form(dict_controls_fields=dict_clear_form)

        # Limpa o array que contém os arquivos PDF em formato binário.
        # O array está no módulo (create_pdf_service)
        array_pdf_files.clear()
    else:
        # Exclui a barra de progresso e atualiza a página
        page.overlay.pop()
        page.update()
