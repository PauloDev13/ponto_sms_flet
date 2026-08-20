"""Testes unitários do backend.core.validators (validação pura do formulário).

Espelha a lógica de utils/validators.py (CPF com dígitos verificadores,
datas MM/yyyy, unidade e tipo de arquivo) mas sem dependência de UI/Flot:
cada função retorna dicionários JSON-friendly.
"""
import pytest

from backend.core.validators import (
    validate_cpf,
    validate_dates,
    validate_file_types,
    validate_form,
    validate_month_year,
    validate_unit,
)

CPF_VALIDO = '52998224725'
XLSX_NAME = 'MARIA SOUZA - CPF_529.982.247-25.xlsx'


class TestValidateCpf:

    def test_cpf_valido(self):
        assert validate_cpf(CPF_VALIDO) == {'ok': 'true'}

    def test_cpf_vazio_obrigatorio(self):
        assert validate_cpf('') == {'ok': 'false', 'message': 'O CPF é obrigatório!'}

    def test_cpf_com_espacos_e_limpo(self):
        assert validate_cpf('  ' + CPF_VALIDO + ' ') == {'ok': 'true'}

    def test_cpf_soletras_rejeitado(self):
        assert validate_cpf('abc')['ok'] == 'false'
        assert validate_cpf('abc')['message'] == 'O CPF deve conter somente números!'

    def test_cpf_tamanho_diferente_rejeitado(self):
        assert validate_cpf('123')['ok'] == 'false'
        assert validate_cpf('123456789012')['ok'] == 'false'

    def test_cpf_digitos_repetidos_rejeitado(self):
        assert validate_cpf('11111111111')['ok'] == 'false'

    def test_cpf_com_digito_verificador_errado(self):
        assert validate_cpf('52998224726')['ok'] == 'false'

    def test_cpf_formatado_com_pontuacao_rejeitado(self):
        res = validate_cpf('529.982.247-25')
        assert res['ok'] == 'false'
        assert res['message'] == 'O CPF deve conter somente números!'

    def test_cpf_com_espacos_internos_rejeitado(self):
        res = validate_cpf('529 982 247 25')
        assert res['ok'] == 'false'
        assert res['message'] == 'O CPF deve conter somente números!'

    def test_cpf_com_caractere_invisivel_rejeitado(self):
        res = validate_cpf('\u200b' + CPF_VALIDO)
        assert res['ok'] == 'false'
        assert res['message'] == 'O CPF deve conter somente números!'


class TestValidateMonthYear:

    def test_formato_valido(self):
        dt = validate_month_year('03/2024')
        assert dt is not None
        assert dt.month == 3 and dt.year == 2024

    def test_formato_invalido(self):
        assert validate_month_year('2024/03') is None
        assert validate_month_year('13/2024') is None
        assert validate_month_year('março') is None
        assert validate_month_year('') is None
        assert validate_month_year(None) is None


class TestValidateDates:

    def test_intervalo_valido(self):
        assert validate_dates('01/2024', '03/2024') == {'ok': 'true'}

    def test_periodo_inicial_obrigatorio(self):
        res = validate_dates('', '03/2024')
        assert res == {'ok': 'false', 'message': 'O Período Inicial é obrigatório!'}

    def test_periodo_inicial_invalido(self):
        res = validate_dates('abc', '03/2024')
        assert res['message'] == 'O Período Inicial (abc) é inválido!'

    def test_ano_inicial_antes_de_2000(self):
        res = validate_dates('01/1999', '03/2024')
        assert res['message'] == 'O Ano do Período Inicial deve ser igual ou maior que 2000!'

    def test_periodo_final_obrigatorio(self):
        res = validate_dates('01/2024', '')
        assert res == {'ok': 'false', 'message': 'O Período Final é obrigatório!'}

    def test_periodo_final_invalido(self):
        res = validate_dates('01/2024', 'zzz')
        assert res['message'] == 'O Período Final (zzz) é inválido!'

    def test_ano_final_antes_de_2000(self):
        res = validate_dates('01/2024', '03/1999')
        assert res['message'] == 'O Ano do Período Final deve ser igual ou maior que 2000!'

    def test_periodo_invertido_rejeitado(self):
        res = validate_dates('05/2024', '01/2024')
        assert res['ok'] == 'false'
        assert 'deve ser posterior' in res['message']

    def test_virada_de_ano_valida(self):
        res = validate_dates('11/2024', '02/2025')
        assert res == {'ok': 'true'}

    def test_virada_de_ano_invertida_rejeitada(self):
        res = validate_dates('01/2025', '12/2024')
        assert res['ok'] == 'false'
        assert 'deve ser posterior' in res['message']

    def test_ano_bissexto_fevereiro_aceito(self):
        assert validate_month_year('02/2024') is not None
        assert validate_month_year('02/2024').year == 2024

    def test_ano_nao_bissexto_tambem_aceito(self):
        assert validate_month_year('02/2023') is not None


class TestValidateUnit:

    def test_unidade_obrigatoria(self):
        assert validate_unit('') == {'ok': 'false', 'message': 'Informe o Código da Unidade!'}

    def test_unidade_so_espacos_rejeitada(self):
        assert validate_unit('   ')['ok'] == 'false'

    def test_unidade_informada(self):
        assert validate_unit('7') == {'ok': 'true'}


class TestValidateFileTypes:

    def test_ao_menos_um_tipo_obrigatorio(self):
        assert validate_file_types(False, False) == {
            'ok': 'false',
            'message': 'Escolha pelo menos um tipo de arquivo a ser gerado!'}

    def test_excel_sozinho_valido(self):
        assert validate_file_types(True, False) == {'ok': 'true'}

    def test_pdf_sozinho_valido(self):
        assert validate_file_types(False, True) == {'ok': 'true'}

    def test_ambos_validos(self):
        assert validate_file_types(True, True) == {'ok': 'true'}


class TestValidateForm:

    def test_form_valido_monta_campos(self):
        res = validate_form(
            cpf=CPF_VALIDO, unit='1', date_start='01/2024', date_end='03/2024',
            excel=True, pdf=False)
        assert res['valid'] is True
        assert res['errors'] == {}
        assert res['fields']['cpf'] == CPF_VALIDO
        assert res['fields']['unit'] == '1'

    def test_form_invalido_agrupa_erros(self):
        res = validate_form(cpf='123', unit='', date_start='', date_end='',
                            excel=False, pdf=False)
        assert res['valid'] is False
        assert 'cpf' in res['errors']
        assert 'unit' in res['errors']
        assert 'start_date' in res['errors']
        assert 'file_types' in res['errors']

    def test_erro_de_datas_mapeado_para_campo(self):
        res = validate_form(
            cpf=CPF_VALIDO, unit='1', date_start='05/2024', date_end='01/2024',
            excel=True, pdf=False)
        assert res['valid'] is False
        assert 'end_date' in res['errors']