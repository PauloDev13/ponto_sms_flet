import os
import xlsxwriter
from dotenv import load_dotenv

load_dotenv()
file_path = os.getenv('PATH_FILE_BASE')
password_workbook = os.getenv('PASSWORD')

if not file_path or not password_workbook:
    raise ValueError("O caminho do arquivo base não está definido no .env")


# Função que retorna um dicionário com a formatação
# para células individuais do arquivo Excel
def define_formats(workbook):
    formats = {
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
            'valign': 'top',
        }),
        'custom_2': workbook.add_format({
            'top': 1,
            'bottom': 1,
            'right': 1,
            'text_wrap': True,
            'bold': True,
            'bg_color': '#F0E68C',
            'align': 'justify',
            'valign': 'top',
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
        # Formata as células com alinhamento centralizado e desbloqueia
        # para edição as células que recebem a formatação
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
        }),
        'test': workbook.add_format({
            'align': 'right',
        }),
        'cell_unblocked': workbook.add_format({'locked': False}),
    }
    return formats


# Função que implementa condicionais e formatação
# (usando a função define_formats), em células individuais do arquivo Excel
def apply_formatting(worksheet, df_year, formats):
    # Formata as larguras das colunas e aplica em algumas
    # delas a formatação que centraliza o conteúdo
    worksheet.set_column(0, 0, 25)
    worksheet.set_column(1, 1, 20, formats['col_center'])
    worksheet.set_column(2, 2, 25)
    worksheet.set_column(3, 6, 20, formats['col_center'])
    worksheet.set_column(7, 10, 5, formats['col_center'])

    # Define a variável (last_header_index) com valor -1.
    # Essa variável vai pegar o número da linha imediatamente
    # após a linha do cabeçalho
    last_header_index = -1

    # Itera sobre as linhas do Dataframe (df_year) criando
    #  uma (Series) com os índices e o conteúdo de cada linha
    for row_index, row in df_year.iterrows():
        # Se o conteúdo da coluna índice 0 for igual à string 'DATA ENTRADA',
        # atribui a variável (last_header_index) o valor do índice da
        # última linha de cada mês
        if row.iloc[0] == 'DATA ENTRADA':
            last_header_index = row_index

        # Se o tamanho do conteúdo das células da coluna 1 for maior que zero
        # e menor ou igual a 8, aplica bordas em todas as células da coluna
        elif row.iloc[1] and 0 < len(row.iloc[1]) <= 8:
            worksheet.write(row_index, 1, row.iloc[1], formats['single_border'])

        # Se na coluna índice 0 o conteúdo da célula for diferente de 'JUSTIFICATIVA', 'AVISO'
        # 'AFASTAMENTO' ou 'FERIADO', aplica bordas customizadas em todas as células da coluna
        elif row.iloc[0] not in ['JUSTIFICATIVA', 'AVISO', 'AFASTAMENTO', 'FERIADO']:
            worksheet.write(row_index, 0, row.iloc[0], formats['single_border'])

        # Se na coluna índice 0 o conteúdo da célula for igual a 'JUSTIFICATIVA', 'AVISO'
        # 'AFASTAMENTO' ou 'FERIADO', aplica bordas customizadas em todas as células da coluna
        elif row.iloc[0] in ['JUSTIFICATIVA', 'AVISO', 'AFASTAMENTO', 'FERIADO']:
            worksheet.write(row_index, 0, row.iloc[0], formats['custom_1'])
            # Se na coluna índice 1 o conteúdo da célula for >= a 145
            # e <= 380 caracteres, aumenta a altura da linha para 30
            if 145 <= len(row.iloc[1]) <= 380:
                worksheet.set_row(row_index, 35)
            # Se na mesma coluna o conteúdo da célula for,
            #  >= a 381, aumenta a altura da linha para 50
            elif len(row.iloc[1]) >= 381:
                worksheet.set_row(row_index, 50)
            # Mescla as células da linha entre as colunas com índices de 1 a 6 e
            # aplica bordas customizadas em todas as células da coluna
            worksheet.merge_range(
                row_index, 1, row_index, 6, row.iloc[1], formats['custom_2'])

        # Itera sobre as linhas criando uma (Series) que
        # contém o índice e os valores em cada coluna por linha
        for col_index, value in enumerate(row):
            # Se o índice da coluna for == a 0 e o valor da célula começar com a
            #  string 'PONTO DIGITAL', mescla as células da coluna em toda a linha
            if col_index == 0 and value.startswith('PONTO DIGITAL'):
                worksheet.merge_range(
                    row_index, 0, row_index, 10, value, formats['header'])

            # Se a string 'DATA ENTRADA' estiver em alguma
            #  célula da coluna, aplica a formatação 'header'
            elif 'DATA ENTRADA' in row.values:
                worksheet.write(row_index, col_index, row.iloc[col_index], formats['header'])

            # Se o índice da coluna for == a 0 e o valor da célula começar com a
            # string 'NÃO HÁ REGISTRO', mescla as células da coluna em toda a linha
            elif col_index == 0 and value.startswith('NÃO HÁ REGISTRO'):
                worksheet.set_row(row_index, 30)
                worksheet.merge_range(
                    row_index, 0, row_index, 10, value, formats['warning'])

            # Insere bordas nas células das colunas com índices
            # maior que 1 e menor que 4 (colunas 2 e 3)
            elif 1 < col_index < 4:
                worksheet.write(row_index, col_index, value, formats['single_border'])

            # Se o índice da coluna for == a 4 e o valor da célula for >=
            #  a '12:00:00', aplica formatação background verde e fonte branca.
            elif col_index == 4 and isinstance(value, str) and value >= '12:00:00':
                worksheet.write(row_index, col_index, value, formats['green_bold'])

            # Se na coluna índice 4 o valor da célula for < '12:00:00'
            # e != da string ('---') ou vazia (''), aplica formatação
            # background azul e fonte branca.
            elif (col_index == 4 and isinstance(value, str)
                  and value < '12:00:00' and value not in ['---', '']):
                worksheet.write(row_index, col_index, value, formats['blue_bold'])

            # Se o índice da coluna é igual 6, aplica formatação
            # que insere bordas em todas as células da coluna
            elif col_index == 5:
                worksheet.write(row_index, col_index, value, formats['single_border'])

            # Se o índice da coluna é igual 6 e o valor da célula for == a
            # 'APROVADO', aplica formatação background verde e fonte branca.
            elif col_index == 6 and value == 'APROVADO':
                worksheet.write(row_index, col_index, value, formats['green_bold'])

            # Se o índice da coluna é igual 6 e o valor da célula for == 'REPROVADO'
            #  ou 'ESPERA', aplica formatação background vermelho e fonte branca.
            elif col_index == 6 and value == 'REPROVADO' or value == 'ESPERA':
                worksheet.write(row_index, col_index, value, formats['red_bold'])

            # Se o índice da coluna é igual 6, aplica formatação
            # que insere bordas em todas as células da coluna
            elif col_index == 6:
                worksheet.write(row_index, col_index, value, formats['single_border'])

            # Se o índice da coluna for > 6 e < 11, aplica a formação que
            # insere bordas em todas as células do intervalo em cada coluna
            elif col_index > 6:
                worksheet.conditional_format(f'H{row_index}:K{row_index}', {
                    'type': 'cell',
                    'criteria': '>=',
                    'value': 0,
                    'format': formats['all_borders']
                })

            # Se nas colunas existir uma célula com valor igual a 'TOTAIS'...
            elif value == 'TOTAIS':
                # mescla as células das colunas de 0 a 6 e aplica formatação
                worksheet.merge_range(
                    row_index, 0, row_index, 6, row.iloc[0], formats['col_total'])

                # Pega o número de colunas mescladas e atribui a variável (formula_col)
                merged_cells = 7
                formula_col = merged_cells

                # Se a variável (last_header_index) definida anteriormente no início da função
                # for >= 0, seta a variável (start_row) com o valor de (last_header_index) + 1,
                # se não, seta (start_row) = 1

                # start_row = last_header_index + 1 if last_header_index >= 0 else 1
                if last_header_index >= 0:
                    start_row = last_header_index + 1
                else:
                    start_row = 1

                # Define que a variável (end_row) é igual ao índice da linha atual menos 1
                end_row = row_index - 1

                # Se a (start_row) for <= (end_row)
                if start_row <= end_row:
                    # Itera sobre o número de colunas que contém as células a serem somadas
                    for index in range(0, 4):
                        # Cria os intervalos inicial e final com as células que
                        # terão seus conteúdos somados
                        start_cell = xlsxwriter.utility.xl_rowcol_to_cell(start_row, formula_col + index)
                        end_cell = xlsxwriter.utility.xl_rowcol_to_cell(end_row, formula_col + index)

                        # Monta a fórmula que será usada para a soma com os intervalos de células
                        # definidos nas linhas de código anteriores
                        formula = f'=SUM({start_cell}:{end_cell})'

                        # Aplica a fórmula na célula de cada coluna onde ficará o
                        # resultado com o total da soma dos intervalos de células
                        worksheet.write_array_formula(
                            end_row + 1,
                            formula_col + index,
                            end_row + 1,
                            formula_col + index,
                            formula,
                            formats['results']
                        )

                else:
                    worksheet.write(row_index, formula_col, 0)

    # Bloqueia toda a planilha para edição. Somente as
    # células liberadas poderão ser editas
    worksheet.protect(password_workbook)
