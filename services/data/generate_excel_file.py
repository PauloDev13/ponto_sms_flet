from typing import Dict

import flet as ft
import pandas as pd

# Importações dos módulos locais
from models.alert_snackbar import AlertSnackbar
from utils.share_model import open_file_excel, create_folder

from backend.core.excel_service import generate_excel_file as _generate_excel_file


# FUNÇÃO QUE CRIA O ARQUIVO EXCEL
def generate_excel_file(
        data_dic: Dict[int, pd.DataFrame],
        employee_name: str,
        cpf: str
) -> None:
    # Chama a função local (create_folder) passando o nome do arquivo
    # do Excel e atribui o retorno à variável (path_file_name)
    path_file_name = create_folder(name_file=f'{employee_name} - CPF_{cpf}.xlsx')

    try:
        # Delega a criação/formatação do arquivo ao backend.core (sem UI)
        _generate_excel_file(
            data_dic=data_dic,
            employee_name=employee_name,
            cpf=cpf,
            output_path=path_file_name,
        )
    except Exception as e:
        AlertSnackbar.show(
            message='Erro ao gerar a planilha {path_file_name}',
            icon=ft.icons.ERROR,
            icon_color=ft.colors.RED
        )
        print(f'Erro ao gerar a planilha {e}')

        return

    open_file_excel(path_file_excel=path_file_name)
