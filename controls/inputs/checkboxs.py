import flet as ft


def checkbox_changed(e, checkbox):
    return checkbox.value


checkbox_excel_field = ft.Checkbox(
    label='Gerar arquivo com planilhas',
    value=True,
    on_change=lambda e: checkbox_changed(e, checkbox_excel_field)
)

checkbox_pdf_field = ft.Checkbox(
    label='Gerar arquivo PDF',
    on_change=lambda e: checkbox_changed(e, checkbox_excel_field)
)
