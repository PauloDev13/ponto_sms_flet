import flet as ft


def checkbox_pdf_changed(e):
    # Importa (generate_button) do módulo (elevated_button)
    from controls.buttons.elevated_button import generate_button

    # Formata a cor de fundo do checkbox
    if checkbox_pdf_field.value and checkbox_excel_field.fill_color == ft.colors.AMBER:
        checkbox_excel_field.fill_color = 'a0cafd'
        checkbox_pdf_field.fill_color = 'a0cafd'
    else:
        checkbox_excel_field.fill_color = '2e2f31'
        checkbox_pdf_field.fill_color = '2e2f31'

    # Formata o texto do botão
    if checkbox_pdf_field.value and checkbox_excel_field.value:
        generate_button.text = 'GERAR PLANILHAS E ARQUIVO PDF'

    elif checkbox_pdf_field.value and not checkbox_excel_field.value:
        generate_button.text = 'GERAR ARQUIVO PDF'

    elif not checkbox_pdf_field.value and checkbox_excel_field.value:
        generate_button.text = 'GERAR PLANILHAS'

    else:
        generate_button.text = 'GERAR ARQUIVO'

    e.page.update()

def checkbox_excel_checked(e):
    # Importa (generate_button) do módulo (elevated_button)
    from controls.buttons.elevated_button import generate_button

    # Formata a cor de fundo do checkbox
    if checkbox_excel_field.value and checkbox_pdf_field.fill_color == ft.colors.AMBER:
        checkbox_excel_field.fill_color = 'a0cafd'
        checkbox_pdf_field.fill_color = 'a0cafd'
    else:
        checkbox_excel_field.fill_color = '2e2f31'
        checkbox_pdf_field.fill_color = '2e2f31'

    # Formata o texto do botão
    if checkbox_pdf_field.value and checkbox_excel_field.value:
        generate_button.text = 'GERAR PLANILHAS E ARQUIVO PDF'

    elif checkbox_pdf_field.value and not checkbox_excel_field.value:
        generate_button.text = 'GERAR ARQUIVO PDF'

    elif not checkbox_pdf_field.value and checkbox_excel_field.value:
        generate_button.text = 'GERAR PLANILHAS'

    else:
        generate_button.text = 'GERAR ARQUIVO'

    e.page.update()

checkbox_excel_field = ft.Checkbox(
    label='Gerar arquivo com planilhas',
    value=True,
    on_change=lambda e: checkbox_excel_checked(e)
)

checkbox_pdf_field = ft.Checkbox(
    label='Gerar arquivo PDF',
    on_change=lambda e: checkbox_pdf_changed(e)
)
