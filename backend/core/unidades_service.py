"""Catálogo de unidades a partir do data/unidades.csv (desacoplado de Flet)."""
import csv
from pathlib import Path
from typing import Dict, List

from backend.core.settings import settings


def load_unidades(path: Path | None = None) -> List[Dict[str, str]]:
    """Lê o CSV de unidades e retorna uma lista de {code, description}."""
    path = path or settings.path_csv
    unidades: List[Dict[str, str]] = []

    try:
        with open(path, newline='', mode='r', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for row in reader:
                if len(row) >= 2:
                    unidades.append({'code': row[0].strip(), 'description': row[1].strip()})
    except FileNotFoundError as e:
        print(f'Erro ao abrir a lista de unidades: {e}')
    return unidades


def search_unidades(query: str = '', limit: int = 50) -> List[Dict[str, str]]:
    """Filtra unidades pela descrição (case-insensitive), com limite."""
    query = (query or '').strip().lower()
    unidades = load_unidades()

    if len(query) < 2:
        return unidades[:limit]

    filtered = [
        u for u in unidades
        if query in u['description'].lower() or query in u['code'].lower()
    ]
    return filtered[:limit]