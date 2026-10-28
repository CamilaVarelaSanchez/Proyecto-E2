"""
Pruebas de Integración de Endpoints HTTP — E2 SAS
Verifica que el servidor web responda correctamente a todas las rutas de la API:
  - GET  /
  - GET  /api/correr
  - GET  /api/demanda
  - GET  /api/decidir
  - GET  /api/instrumentacion
  - POST /api/previsualizar
  - POST /api/importar
"""

import sys
import os
import json
import time
import tempfile
import unittest
import threading
import urllib.request
from unittest.mock import patch
from http.server import HTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import EnterpriseRequestHandler, PORT
from nucleo import base_datos

TEST_PORT = 8502

class TestHttpEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path_original = base_datos.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        base_datos.DB_PATH = os.path.join(cls.temp_dir.name, 'kardex_e2.db')
        base_datos.poblar_estado_inicial_si_vacio()
        cls.server = HTTPServer(('127.0.0.1', TEST_PORT), EnterpriseRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        base_datos.DB_PATH = cls.db_path_original
        cls.temp_dir.cleanup()

    def test_01_get_home_html(self):
        url = f"http://127.0.0.1:{TEST_PORT}/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode('utf-8')
            self.assertIn("E2 SAS", body)
            self.assertIn("Tablero de Control", body)
            self.assertIn("Ingesta de Datos", body)

    @patch('nucleo.datos.guardar_propuestas')
    def test_02_get_api_correr(self, guardar_propuestas):
        url = f"http://127.0.0.1:{TEST_PORT}/api/correr"
        with urllib.request.urlopen(url, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data.get('status'), 'completado')
            self.assertIn('kpis', data)
            self.assertIn('propuestas_compra', data)

    def test_03_get_api_demanda(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/demanda"
        with urllib.request.urlopen(url, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertIn('resumen_abc', data)
            self.assertIn('materiales', data)
            self.assertEqual(data.get('total_skus'), 440)

    @patch('nucleo.datos.supabase_post', return_value={'status': 'success'})
    def test_04_get_api_decidir(self, supabase_post):
        url = f"http://127.0.0.1:{TEST_PORT}/api/decidir?sku=MP-0001&accion=APROBADA"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data.get('status'), 'registrado')
            self.assertEqual(data.get('decision'), 'APROBADA')

    def test_05_get_api_instrumentacion(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/instrumentacion"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertIn('instrumento_1_carga', data)
            self.assertIn('instrumento_2_corrida', data)
            self.assertIn('bitacora_corridas', data)

    def test_06_post_api_previsualizar(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/previsualizar"
        payload = {
            'nombre_archivo': 'prueba_lote.csv',
            'tipo_documento': 'movimientos_inventario',
            'contenido': 'fecha,sku,tipo_movimiento,cantidad,documento\n2026-03-01,MP-0001,salida,10,DOC-01\n'
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get('valido'))
            self.assertEqual(data.get('filas_total'), 1)

    @patch(
        'nucleo.datos.supabase_upsert',
        return_value={'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
    )
    def test_07_post_api_importar(self, supabase_upsert):
        url = f"http://127.0.0.1:{TEST_PORT}/api/importar"
        payload = {
            'nombre_archivo': 'prueba_lote_import.csv',
            'tipo_documento': 'movimientos_inventario',
            'contenido': 'fecha,sku,tipo_movimiento,cantidad,documento\n2026-03-01,MP-0001,salida,10,DOC-ENDPOINT-TEST\n'
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data.get('status'), 'completado')
            self.assertIn('trazabilidad_filas', data)

    def test_08_get_api_reconciliacion(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/reconciliacion"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertIn('eri_global_pct', data)
            self.assertIn('auditados', data)
            self.assertGreater(len(data['auditados']), 0)

if __name__ == '__main__':
    unittest.main()
