import flet as ft


def checkbox_changed(e, checkbox):
    if checkbox.value:
        checkbox.fill_color = 'a0cafd'
        e.page.update()
    else:
        checkbox.fill_color = '2e2f31'
        e.page.update()


checkbox_excel_field = ft.Checkbox(
    label='Gerar arquivo com planilhas',
    value=True,
    on_change=lambda e: checkbox_changed(e, checkbox_excel_field)
)

checkbox_pdf_field = ft.Checkbox(
    label='Gerar arquivo PDF',
    on_change=lambda e: checkbox_changed(e, checkbox_pdf_field)
)
