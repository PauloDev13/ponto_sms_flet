import csv
from typing import List

# Importação dos módulos locais
from models.alert_snackbar import AlertSnackbar


# # Função para ler o arquivo CSV e carregar os dados em memória
def read_csv_text_field(file_csv: str):
    # Cria a variável (data), uma lista de dicionários com
    # chave e valor do tipo string inicialmente vazia
    data: List[dict[str, str]] = []

    try:
        # Abre o arquivo .CSV sem quebra de linha e no modo leitura
        with open(file_csv, newline='', mode='r') as csvfile:
            # Atribui à variável (read) os dados do arquivo .csv
            reader = csv.reader(csvfile, delimiter=',')

            for row in reader:
                # Desempacota os atributos (code e description)
                code, description = row

                # Adiciona ao dicionário (data) os valores das variáveis (code e description)
                data.append({'code': code, 'description': description})

        # Retorna a variável (data)
        return data

    except FileNotFoundError as e:
        AlertSnackbar.show(message='Ocorreu um erro ao abrir a lista de unidades')
        print('Ocorreu um erro ao abrir a lista de unidades', e)


