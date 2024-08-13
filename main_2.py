import flet as ft
from data import data_array


def main(page: ft.Page):
    page.title = "Seleção de Mês e Ano com Dropdown"

    # Lista de meses
    # meses = [
    #     ft.dropdown.Option("Janeiro"),
    #     ft.dropdown.Option("Fevereiro"),
    #     ft.dropdown.Option("Março"),
    #     ft.dropdown.Option("Abril"),
    #     ft.dropdown.Option("Maio"),
    #     ft.dropdown.Option("Junho"),
    #     ft.dropdown.Option("Julho"),
    #     ft.dropdown.Option("Agosto"),
    #     ft.dropdown.Option("Setembro"),
    #     ft.dropdown.Option("Outubro"),
    #     ft.dropdown.Option("Novembro"),
    #     ft.dropdown.Option("Dezembro"),
    # ]
    # meses_array = [
    #     'Janeiro', 'Fevereiro', 'Março',
    #     'Abril', 'Maio', 'Junho', 'Julho',
    #     'Agosto', 'Setembro', 'Outubro',
    #     'Novembro', 'Dezembro'
    # ]

    # Lista de anos
    meses = [
        ft.dropdown.Option(mes) for mes in data_array.months
    ]

    anos = [
        ft.dropdown.Option(str(ano)) for ano in range(2020, 2031)
    ]

    def on_selection_change(e):
        # Exibir a combinação de mês e ano selecionados
        selected_date.value = f"Mês: {mes_picker.value}, Ano: {ano_picker.value}"
        selected_date.update()

    # Dropdown para selecionar o mês
    mes_picker = ft.Dropdown(
        label="Selecione o mês",
        options=meses,
        on_change=on_selection_change,
        width=150
    )

    # Dropdown para selecionar o ano
    ano_picker = ft.Dropdown(
        label="Selecione o ano",
        options=anos,
        on_change=on_selection_change,
        width=100
    )

    # Label para mostrar a seleção de mês e ano
    selected_date = ft.Text(value="Nenhuma data selecionada")

    # Layout da página
    page.add(
        ft.Column(
            [
                mes_picker,
                ano_picker,
                selected_date,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )


ft.app(target=main)
