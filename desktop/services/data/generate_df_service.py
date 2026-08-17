from typing import Dict

import pandas as pd

# Importações dos módulos locais
from desktop.models.alert_snackbar import AlertSnackbar

from backend.core.dataframe import generate_dataframe as _generate_dataframe


# FUNÇÃO QUE CRIA TODA A ESTRUTURA DO DATAFRAME QUE VAI GERAR O ARQUIVO EXCEL
def generate_dataframe(
        df_table: pd.DataFrame,
        data_by_year: Dict[int, pd.DataFrame],
        cpf: str,
        month_name: str,
        year: int,
        employee_name: str,
) -> None:
    # Delega a montagem do dataframe ao backend.core (sem UI)
    try:
        _generate_dataframe(
            df_table=df_table,
            data_by_year=data_by_year,
            cpf=cpf,
            month_name=month_name,
            year=year,
            employee_name=employee_name,
        )
    except Exception as e:
        AlertSnackbar.show('Ocorreu um erro inesperado. Tente novamente.')
        print('Erro inesperado', e)


# FUNÇÃO LOCAL QUE RETORNA UM DATAFRAME COM A LINHA DE TOTAIS
def df_total_row(columns: any) -> pd.DataFrame:
    # Linha com a string 'TOTAIS' na primeira célula e
    # vazia nas demais (array ['TOTAIS'], [''], [''], ['']...
    totals_row = ['TOTAIS'] + [''] * (len(columns) - 1)

    # Cria Dataframe com a linha onde será impresso 'TOTAIS'
    df_totals = pd.DataFrame([totals_row], columns=columns)

    return df_totals
