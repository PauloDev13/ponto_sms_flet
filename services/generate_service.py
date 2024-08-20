import flet as ft
from datetime import datetime

from services.authenticate_service import login
from utils.extractor_data import data_fetch


def file_generate(*args):
    from utils.validators import (
        validate_cpf, validate_dates, format_cpf, clear_form
    )
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

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
                #
                #         # Exibe um spinner até que a funçao 'data_fetch'
                #         # do módulo 'extrator_data' conclua a execução
                #         # with st.spinner(f'Processamento em andamento, AGUARDE...'):
                #
                # Chama a função (data_fetch) do módulo (extract_data)
                result = data_fetch(
                    e, cpf, month_start, year_start, month_end, year_end, driver
                )
                #
                if result:
                    clear_form(cpf_field, start_date_field, end_date_field)
                    # Se não houver erros no processamento, exibe mensagem de sucesso
                    snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)

        else:
            # Se já existir uma sessão aberta no Streamlit, repete o processo de geração do arquivo
            # with st.spinner('Processamento em andamento, AGUARDE...'):
            result = data_fetch(
                e, cpf, month_start, year_start, month_end, year_end, driver
            )

            if result:
                clear_form(cpf_field, start_date_field, end_date_field)
                # Se não houver erros no processamento, exibe mensagem de sucesso
                snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)


# def file_generate(*args):
#     # Importa a função (show_snackbar) do módulo (controls)
#     from controls.components import snack_show
#
#     e, cpf, month_start, year_start, month_end, year_end = args
#
#     # Atribui a variável driver o valor do argumento
#     # driver guardado na session do Flet.
#     driver = e.page.session.get('driver')
#
#     # Verifica se existe o argumento driver na sessão.
#     # Se NÃO, chama a função 'login' do módulo 'authenticate'
#     # que retorna uma instância do driver do navegador e
#     # armazena a instância retornada na sessão do Flet
#     if driver is None:
#         if driver := login(e):
#             driver.minimize_window()
#             e.page.session.set('driver', driver)
#     #
#     #         # Exibe um spinner até que a funçao 'data_fetch'
#     #         # do módulo 'extrator_data' conclua a execução
#     #         # with st.spinner(f'Processamento em andamento, AGUARDE...'):
#     #
#             result = data_fetch(
#                 e, cpf, month_start, year_start, month_end, year_end, driver
#             )
#     #
#             if result:
#                 # Se não houver erros no processamento, exibe mensagem de sucesso
#                 snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)
#
#     else:
#         # Se já existir uma sessão aberta no Streamlit, repete o processo de geração do arquivo
#         # with st.spinner('Processamento em andamento, AGUARDE...'):
#         result = data_fetch(
#             e, cpf, month_start, year_start, month_end, year_end, driver
#         )
#
#         if result:
#             # Se não houver erros no processamento, exibe mensagem de sucesso
#             snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)
