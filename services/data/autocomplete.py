import flet as ft
import csv
from typing import List


def read_csv(file_csv) -> List[ft.AutoCompleteSuggestion]:
    suggestions: List[ft.AutoCompleteSuggestion] = []

    with open(file_csv, newline='') as csvfile:
        reader_csv = csv.reader(csvfile, delimiter=',')
        for row in reader_csv:
            code, description = row
            suggestions.append(ft.AutoCompleteSuggestion(key=description, value=f'{code} - {description}'))

    return suggestions


def read_csv_dropdown(file_csv) -> List[ft.dropdown]:
    dropdown_items: List[ft.dropdown] = []

    with open(file_csv, newline='') as csvfile:
        reader_csv = csv.reader(csvfile, delimiter=',')
        for row in reader_csv:
            code, description = row
            dropdown_items.append(ft.dropdown.Option(key=code, text=description))

    return dropdown_items
