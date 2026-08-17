"""Testes da API FastAPI (FASE 0) usando TestClient.

Cobre: health, validação do formulário (válido/inválido) e autocomplete
de unidades. Não requer navegador ou rede externa.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.main import app


class ApiTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _validate(self, **kwargs):
        payload = {
            'cpf': '52998224725',  # CPF válido para testes
            'unit': '1',
            'date_start': '01/2024',
            'date_end': '03/2024',
            'excel': True,
            'pdf': False,
        }
        payload.update(kwargs)
        return self.client.post('/api/v1/validate', json=payload)

    def test_health(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('env_ok', data)

    def test_validate_valid(self):
        res = self._validate()
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['errors'], {})

    def test_validate_invalid_cpf(self):
        res = self._validate(cpf='123')
        data = res.json()
        self.assertFalse(data['valid'])
        self.assertIn('cpf', data['errors'])

    def test_validate_missing_file_type(self):
        res = self._validate(excel=False, pdf=False)
        data = res.json()
        self.assertFalse(data['valid'])
        self.assertIn('file_types', data['errors'])

    def test_validate_reversed_period(self):
        res = self._validate(date_start='05/2024', date_end='01/2024')
        data = res.json()
        self.assertFalse(data['valid'])
        self.assertIn('end_date', data['errors'])

    def test_unidades_valid_cpf(self):
        res = self.client.get('/api/v1/unidades?q=UBS')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertGreater(data['count'], 0)

    def test_unidades_short_query_returns_limited(self):
        res = self.client.get('/api/v1/unidades?q=P')
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertLessEqual(data['count'], 50)

    def test_index_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/html', res.headers['content-type'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
