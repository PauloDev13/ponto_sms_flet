"""Geração e formatação de arquivos Excel do ponto digital.

Port de services/data/generate_excel_file.py + utils/format_excel_file.py
sem dependências de UI. A senha de proteção da planilha vem de
backend.core.settings (environment PASSWORD), não de config.config_env.
"""
from pathlib import Path
from typing import Dict

import pandas as pd
import xlsxwriter

from .settings import settings


def define_formats(workbook) -> Dict[str, any]:  # noqa: ANN001, ANN401
    """Dicionário com as formatações das células do arquivo Excel."""
    return {
        'header': workbook.add_format({
            'bold': True,
            'bg_color': '#B0C4DE',
            'align': 'center',
            'border': 1,
        }),
        'green_bold': workbook.add_format({
            'bold': True,
            'bg_color': 'green',
            'font_color': 'white',
            'align': 'center',
            'border': 1,
        }),
        'blue_bold': workbook.add_format({
            'bold': True,
            'bg_color': 'blue',
            'font_color': 'white',
            'align': 'center',
            'border': 1,
        }),
        'red_bold': workbook.add_format({
            'bold': True,
            'bg_color': 'red',
            'font_color': 'white',
            'align': 'center',
            'border': 1,
        }),
        'custom_1': workbook.add_format({
            'top': 1,
            'bottom': 1,
            'left': 1,
            'bold': True,
            'bg_color': '#F0E68C',
            'align': 'center',
            'valign': 'vcenter',
        }),
        'custom_2': workbook.add_format({
            'top': 1,
            'bottom': 1,
            'right': 1,
            'text_wrap': True,
            'bold': True,
            'bg_color': '#F0E68C',
            'align': 'justify',
            'valign': 'vcenter',
        }),
        'all_borders': workbook.add_format({
            'border': 1,
            'bg_color': '#F0F8FF',
        }),
        'warning': workbook.add_format({
            'bg_color': '#FF8C00',
            'align': 'center',
            'valign': 'center',
            'font_size': 20,
            'border': 1,
        }),
        'col_center': workbook.add_format({
            'align': 'center',
            'locked': False
        }),
        'results': workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_color': 'red',
            'border': 1,
        }),
        'col_total': workbook.add_format({
            'bold': True,
            'align': 'right',
            'font_color': 'red',
            'border': 1,
        }),
        'single_border': workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        }),
        'test': workbook.add_format({
            'align': 'right',
        }),
        'cell_unblocked': workbook.add_format({'locked': False}),
    }


def count_markers(df_year, start_index: int, end_index: int, col: int) -> int:
    """Soma os marcadores (1) das colunas derivadas HT/HJ/ST/ADN no intervalo.

    Usado para gravar o valor calculado junto da fórmula de TOTAIS: sem o
    valor em cache, o LibreOffice (que não recalcula xlsx ao abrir) exibe
    a célula vazia — agravado pelo Modo de Exibição Protegido de arquivos
    baixados da internet.
    """
    total = 0
    for value in df_year.iloc[start_index:end_index + 1, col]:
        if value == 1 or value == '1':
            total += 1
    return total


def apply_formatting(worksheet, df_year, formats, password: str | None = None) -> None:  # noqa: ANN001
    """Aplica condicionais e formatação nas células de cada planilha."""
    worksheet.set_column(0, 0, 25)
    worksheet.set_column(1, 1, 20, formats['col_center'])
    worksheet.set_column(2, 2, 25)
    worksheet.set_column(3, 6, 20, formats['col_center'])
    worksheet.set_column(7, 10, 5, formats['col_center'])

    last_header_index = -1

    for row_index, row in df_year.iterrows():
        if row.iloc[0] == 'DATA ENTRADA':
            last_header_index = row_index
        elif row.iloc[1] and 0 < len(row.iloc[1]) <= 8:
            worksheet.write(row_index, 1, row.iloc[1], formats['single_border'])
        elif row.iloc[0] not in ['JUSTIFICATIVA', 'AVISO', 'AFASTAMENTO', 'FERIADO']:
            worksheet.write(row_index, 0, row.iloc[0], formats['single_border'])
        elif row.iloc[0] in ['JUSTIFICATIVA', 'AVISO', 'AFASTAMENTO', 'FERIADO']:
            worksheet.write(row_index, 0, row.iloc[0], formats['custom_1'])
            if 145 <= len(row.iloc[1]) <= 380:
                worksheet.set_row(row_index, 35)
            elif len(row.iloc[1]) >= 381:
                worksheet.set_row(row_index, 50)
            worksheet.merge_range(
                row_index, 1, row_index, 6, row.iloc[1], formats['custom_2'])

        for col_index, value in enumerate(row):
            if col_index == 0 and value.startswith('PONTO DIGITAL'):
                worksheet.merge_range(
                    row_index, 0, row_index, 10, value, formats['header'])
            elif 'DATA ENTRADA' in row.values:
                worksheet.write(row_index, col_index, row.iloc[col_index], formats['header'])
            elif col_index == 0 and value.startswith('SERVIDOR EM'):
                worksheet.set_row(row_index, 30)
                worksheet.merge_range(
                    row_index, 0, row_index, 10, value, formats['warning'])
            elif 1 < col_index < 4:
                worksheet.write(row_index, col_index, value, formats['single_border'])
            elif col_index == 4 and isinstance(value, str) and value >= '12:00:00':
                worksheet.write(row_index, col_index, value, formats['green_bold'])
            elif (col_index == 4 and isinstance(value, str)
                  and value < '12:00:00' and value not in ['---', '']):
                worksheet.write(row_index, col_index, value, formats['blue_bold'])
            elif col_index == 5:
                worksheet.write(row_index, col_index, value, formats['single_border'])
            elif col_index == 6 and value == 'APROVADO':
                worksheet.write(row_index, col_index, value, formats['green_bold'])
            elif col_index == 6 and value == 'REPROVADO' or value == 'ESPERA':
                worksheet.write(row_index, col_index, value, formats['red_bold'])
            elif col_index == 6:
                worksheet.write(row_index, col_index, value, formats['single_border'])
            elif col_index > 6:
                worksheet.conditional_format(f'H{row_index}:K{row_index}', {
                    'type': 'cell',
                    'criteria': '>=',
                    'value': 0,
                    'format': formats['all_borders']
                })
            elif value == 'TOTAIS':
                worksheet.merge_range(
                    row_index, 0, row_index, 6, row.iloc[0], formats['col_total'])

                merged_cells = 7
                formula_col = merged_cells

                if last_header_index >= 0:
                    start_row = last_header_index + 1
                else:
                    start_row = 1

                end_row = row_index - 1

                if start_row <= end_row:
                    for index in range(0, 4):
                        start_cell = xlsxwriter.utility.xl_rowcol_to_cell(
                            start_row, formula_col + index)
                        end_cell = xlsxwriter.utility.xl_rowcol_to_cell(
                            end_row, formula_col + index)
                        formula = f'=SUM({start_cell}:{end_cell})'
                        total = count_markers(
                            df_year, start_row, end_row, formula_col + index)
                        worksheet.write_array_formula(
                            end_row + 1,
                            formula_col + index,
                            end_row + 1,
                            formula_col + index,
                            formula,
                            formats['results'],
                            total)
                else:
                    worksheet.write(row_index, formula_col, 0)

    # Bloqueia a planilha para edição (apenas as células liberadas são editáveis)
    worksheet.protect(password if password is not None else settings.password)


def generate_excel_file(
        data_dic: Dict[int, pd.DataFrame],
        employee_name: str,
        cpf: str,
        output_path: str | Path,
        password: str | None = None,
) -> Path:
    """Cria o arquivo Excel a partir do dicionário de anos (data_dic).

    Retorna o caminho do arquivo gerado. Não abre o arquivo nem cria
    atalhos (responsabilidade da camada de apresentação).
    """
    path_file = Path(output_path)
    path_file.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path_file, engine='xlsxwriter') as writer:
        for year, df_year in data_dic.items():
            df_year.to_excel(
                writer,
                sheet_name=str(year),
                startrow=0,
                index=False,
                header=False
            )
            workbook = writer.book
            worksheet = writer.sheets[str(year)]

            formats = define_formats(workbook)
            apply_formatting(worksheet, df_year, formats, password=password)

    return path_file