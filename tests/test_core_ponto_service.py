"""Testes unitários das funções auxiliares de backend.app.ponto_service.

Cobre a E1 do inventário: normalize_cpf, format_cpf_br e parse_br_month
(CPF, máscaras e datas) sem subir o servidor nem tocar Selenium.
"""
import pytest

from backend.app.ponto_service import (
    PontoRequestError,
    format_cpf_br,
    normalize_cpf,
    parse_br_month,
)


class TestNormalizeCpf:

    def test_cpf_so_digitos(self):
        assert normalize_cpf('52998224725') == '52998224725'

    def test_cpf_com_pontuacao(self):
        assert normalize_cpf('529.982.247-25') == '52998224725'

    def test_cpf_com_espacos(self):
        assert normalize_cpf(' 529.982.247-25 ') == '52998224725'

    def test_cpf_vazio_erro(self):
        with pytest.raises(PontoRequestError, match='11 dígitos'):
            normalize_cpf('')

    def test_cpf_curto_erro(self):
        with pytest.raises(PontoRequestError, match='11 dígitos'):
            normalize_cpf('123')

    def test_cpf_letras_removidas_mas_digitos_12(self):
        with pytest.raises(PontoRequestError, match='11 dígitos'):
            normalize_cpf('529.982.247-251')


class TestFormatCpfBr:

    def test_formata_padrao(self):
        assert format_cpf_br('52998224725') == '529.982.247-25'

    def test_formata_outro_cpf(self):
        assert format_cpf_br('06511122233') == '065.111.222-33'


class TestParseBrMonth:

    def test_formato_valido_primeiro_dia(self):
        result = parse_br_month('03/2024', 'date_start')
        assert result.day == 1
        assert result.month == 3
        assert result.year == 2024

    def test_valor_com_espacos(self):
        assert parse_br_month('  01/2024 ', 'date_start').year == 2024

    def test_formato_invalido_erro(self):
        with pytest.raises(PontoRequestError, match='MM/yyyy'):
            parse_br_month('2024/03', 'date_start')

    def test_mes_invalido_erro(self):
        with pytest.raises(PontoRequestError, match='MM/yyyy'):
            parse_br_month('13/2024', 'date_start')

    def test_vazio_erro(self):
        with pytest.raises(PontoRequestError, match='MM/yyyy'):
            parse_br_month('', 'date_end')

    def test_none_erro(self):
        with pytest.raises(PontoRequestError, match='MM/yyyy'):
            parse_br_month(None, 'date_end')