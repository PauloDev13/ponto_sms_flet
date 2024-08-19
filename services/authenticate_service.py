import os
from time import sleep

import flet as ft
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchWindowException,
    ElementClickInterceptedException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Carrega o arquivo .env
load_dotenv()

# Atribuições das variáveis declaradas no .env
url_login = os.getenv("URL_BASE")
url_init = os.getenv("URL_INIT")
username = os.getenv("USER")
password = os.getenv("PASSWORD")


# FUNÇÃO LOGIN
def login(e):
    # Importa a função (snack_show) do módulo (controls)
    from controls.components import snack_show

    # Configuração do WebDriver
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    try:
        # Acessa a URL que exibe a página de login
        driver.get(url_login)

        # Verifica se a página HTML carregou os campos de login e senha
        load_login = WebDriverWait(driver, 10).until(
            ec.presence_of_element_located((By.XPATH, "//*[@id='cpf']"))
        )
        load_senha = WebDriverWait(driver, 10).until(
            ec.presence_of_element_located((By.XPATH, "//*[@id='senha']"))
        )

        if load_login and load_senha:
            # Acessa o campo de login, insere o login, espera 1 segundo, acessa o campo senha e insere a senha
            driver.find_element(By.XPATH, '//*[@id="cpf"]').send_keys(username)
            sleep(1)
            driver.find_element(By.XPATH, "//*[@id='senha']").send_keys(password)
        else:
            snack_show(e.page, 'Erro ao identificar TAGs de login', ft.icons.ERROR, ft.colors.RED)

        # Localiza o primeiro Iframe da página, entra nele, espera 1 segundo
        # Localiza dentro Iframe o elemento o box do recaptcha e clica
        # Sai do Iframe e volta para o html principal
        # Espera 30 segundos para que o usuário digite o captcha, se aparecer
        driver.switch_to.frame(0)
        driver.find_element(by=By.XPATH, value="//*[@id='recaptcha-anchor']").click()
        driver.switch_to.default_content()
        sleep(60)

        # Localiza o botão de login e clica
        button_login = driver.find_element(by=By.XPATH, value="//*[@id='form']/input")
        button_login.click()

        sleep(1)
        # Checa se a URL da página inicial foi carregada no navegador
        load_page = WebDriverWait(driver, 10).until(
            ec.url_contains(url_init)
        )

        # Se a página inicial carregou, exibe mensagem de sucesso
        # Se não, exibe mensagem de alerta
        if load_page:
            snack_show(e.page, 'Login realizado com sucesso!', ft.icons.CHECK, ft.colors.GREEN)

        else:
            snack_show(e.page, 'Falha no login! Tente novamente.', ft.icons.INFO)

        # Retorna uma instância do navegador.
        return driver

    # Se ocorrer erros no processo de login exibe mensagens
    except ElementClickInterceptedException as e_:
        snack_show(
            e.page,
            'Erro ao clicar num elemento da página! Tente novamente',
            ft.icons.ERROR,
            ft.colors.RED
        )
        print(f'Erro stacktrace: {e_}')
        return None
    except TimeoutException as ex:
        snack_show(
            e.page,
            'A pagina demorou a responder! Tente novamente')
        print(f'Erro stacktrace: {ex}')
        return None

    except NoSuchWindowException as ex_:
        snack_show(
            e.page,
            'Falha no login! Tente novamente')
        print(f'Erro stacktrace: {ex_}')
        return None
