import flet as ft


# Função que limpa os controles do formulário
def clear_form(
        cpf_field: ft.TextField,
        start_date_field: ft.TextField,
        end_date_field: ft.TextField
) -> None:
    cpf_field.value = ''
    start_date_field.value = ''
    end_date_field.value = ''

    cpf_field.update()
    start_date_field.update()
    end_date_field.update()


# Função que captura o evento quando a janela principal do
# aplicativo é fechada, encerrando o drive do navegador
def on_close(e):
    driver = e.page.session.get('driver')
    if driver is not None:
        driver.quit()


# Função que fecha a aplicação e
# encerra o driver após click no botão sair
def close_app(e):
    driver = e.page.session.get('driver')
    if driver is not None:
        driver.quit()
    e.page.window_close()


# Função que insere '.' e '-' no número do CPF, caso tenha sido
# informado somente números.
def format_cpf(cpf_field: ft.TextField) -> str:
    cpf = cpf_field.value
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
