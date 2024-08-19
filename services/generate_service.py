import flet as ft

from services.authenticate_service import login
from utils.extractor_data import data_fetch


def file_generate(*args):
    # Importa a função (show_snackbar) do módulo (controls)
    from controls.components import snack_show

    e, cpf, month_start, year_start, month_end, year_end = args

    # snack_show(args[0], 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)
    # Verifica se existe uma sessão no Streamlit para o usuário logado
    # Se NÃO, chama a função 'login' do módulo 'authenticate'
    # que retorna uma instância do navegador e armazena a instância
    # retornada na sessão do Streamlit
    if driver := login(e):
        driver.minimize_window()

        # Exibe um spinner até que a funçao 'data_fetch'
        # do módulo 'extrator_data' conclua a execução
        # with st.spinner(f'Processamento em andamento, AGUARDE...'):

        result = data_fetch(
            e, cpf, month_start, year_start, month_end, year_end, driver
        )

        if result:
            # Se não houver erros no processamento, exibe mensagem de sucesso
            snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)

    else:
        # Se já existir uma sessão aberta no Streamlit, repete o processo de geração do arquivo
        # with st.spinner('Processamento em andamento, AGUARDE...'):
        result = data_fetch(
            e, cpf, month_start, year_start, month_end, year_end, driver
        )

        if result:
            # Se não houver erros no processamento, exibe mensagem de sucesso
            snack_show(e.page, 'Arquivo criado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)
