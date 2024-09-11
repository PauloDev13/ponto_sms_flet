import os
import sys
from dotenv import load_dotenv

# Função para carregar o .env e definir o caminho base corretamente
def initalize_enviroment():
    # Verifica se a aplicação está empacotada com PyInstaller
    if getattr(sys, 'frozen', False):
        # Caminho para o diretório onde o PyInstaller coloca os arquivos
        base_path = sys._MEIPASS
    else:
        # Caminho no desenvolvimento (IDE)
        base_path = os.path.abspath(".")

    # Define o caminho absoluto para o arquivo .env
    env_path = os.path.join(base_path, '.env')

    # Carrega o arquivo .env
    load_dotenv(env_path)

    return base_path

# Inicializa o ambiente e obtém o caminho base
BASE_PATH = initalize_enviroment()

# Função para construir o caminho absoluto para variáveis
# que são caminhos de arquivos ou diretórios
def get_absolute_path(env_variable_name):
    relative_path = os.getenv(env_variable_name)

    if not relative_path:
        raise ValueError(f'A variável {env_variable_name} não foi definida no arquivo .env')

    # Retorna o caminho absoluto com base no caminho relativo definido no .env
    return os.path.join(BASE_PATH, relative_path)

# Variáveis que são caminhos de arquivos ou diretórios
PATH_LOGO = get_absolute_path('PATH_LOGO')

# Outras variáveis do .env que não são caminhos de arquivos
USER = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
URL_BASE = os.getenv('URL_BASE')
URL_DATA = os.getenv('URL_DATA')
URL_INIT = os.getenv('URL_INIT')
NAME_FOLDER = os.getenv('NAME_FOLDER')

required_variable: list[str] | None = [
    USER, PASSWORD, URL_BASE, URL_DATA, URL_INIT, NAME_FOLDER
]

if None in required_variable:
    raise ValueError('Uma ou mais variáveis necessárias não estão declaradas no arquivo .env')
