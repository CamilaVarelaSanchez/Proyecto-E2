"""
SUITE DE PRUEBAS DE ASEGURAMIENTO DE CALIDAD (QA) Y MANEJO DEFENSIVO DE ERRORES
E2 SAS — Manufactura de Mobiliario Metálico para Oficina

Verifica la resiliencia del sistema ante intentos deliberados de inducir fallos:
  1. Archivos CSV vacíos, corruptos o con líneas malformadas.
  2. Columnas cambiadas de orden, espacios y columnas faltantes.
  3. Fechas imposibles (mes 13: '2026-13-05', 30 de febrero, años lejanos como 1800 o 2099).
  4. Resiliencia contra divisiones por cero en métricas sin histórico o DataFrames vacíos.
  5. Endpoints HTTP blindados: ausencia de parámetros obligatorios, JSON malformado y modo resiliente (CERO 500).
"""

import unittest
import os
import tempfile
import json
import io
import urllib.request
import urllib.error
import threading
import time
from http.server import HTTPServer
from unittest.mock import patch
import pandas as pd
import numpy as np

from app import EnterpriseRequestHandler
from nucleo import base_datos, datos, ingesta, bom, abc, reposicion, eri

QA_PORT = 8504

class TestQAManejoDefensivo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path_original = base_datos.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        base_datos.DB_PATH = os.path.join(cls.temp_dir.name, 'kardex_e2.db')
        cls.supabase_patcher = patch(
            'nucleo.datos.supabase_upsert',
            return_value={'status': 'success', 'filas_sincronizadas': 0, 'filas_pendientes': 0}
        )
        cls.supabase_patcher.start()
        base_datos.poblar_estado_inicial_si_vacio()
        cls.server = HTTPServer(('127.0.0.1', QA_PORT), EnterpriseRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.supabase_patcher.stop()
        base_datos.DB_PATH = cls.db_path_original
        cls.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. ARCHIVOS CSV VACÍOS Y CORRUPTOS
    # -------------------------------------------------------------
    def test_01_csv_vacio_0_bytes(self):
        """Previsualizar y cargar un archivo de 0 bytes debe responder limpio sin traceback ni error 500."""
        prev = ingesta.previsualizar_archivo("vacio.csv", b"", "movimientos_inventario")
        self.assertFalse(prev['valido'])
        self.assertIn("vacío", prev['mensaje'].lower())
        self.assertEqual(prev['filas_total'], 0)

        carga = ingesta.ejecutar_carga_cinco_pasos("vacio.csv", b"", "movimientos_inventario")
        self.assertEqual(carga['estado_carga'], 'Rechazado')
        self.assertEqual(carga['filas_leidas'], 0)
        self.assertIn("vacío", carga['mensaje'].lower())

    def test_02_csv_espacios_en_blanco(self):
        """CSV con solo espacios y saltos de línea debe ser rechazado defensivamente."""
        contenido = "   \n\n\t  \n"
        prev = ingesta.previsualizar_archivo("blancos.csv", contenido.encode('utf-8'), "movimientos_inventario")
        self.assertFalse(prev['valido'])
        
        carga = ingesta.ejecutar_carga_cinco_pasos("blancos.csv", contenido, "movimientos_inventario")
        self.assertEqual(carga['estado_carga'], 'Rechazado')

    def test_03_csv_corrupto_o_malformado(self):
        """CSV binario corrupto o con comillas rotas no debe arrojar excepción no controlada."""
        contenido_corrupto = b"\x00\x01\x02\xff\xfe\x00'\"linea_incompleta,1,2,3\n\"sin_cerrar"
        prev = ingesta.previsualizar_archivo("corrupto.bin", contenido_corrupto, "movimientos_inventario")
        self.assertFalse(prev['valido'])
        self.assertIn("no se pudo estructurar", prev['mensaje'].lower())

        carga = ingesta.ejecutar_carga_cinco_pasos("corrupto.bin", contenido_corrupto, "movimientos_inventario")
        self.assertEqual(carga['estado_carga'], 'Rechazado')

    # -------------------------------------------------------------
    # 2. COLUMNAS CAMBIADAS DE ORDEN Y ESPACIOS
    # -------------------------------------------------------------
    def test_04_csv_columnas_desordenadas(self):
        """Columnas en orden diferente deben ser aceptadas y procesadas correctamente."""
        # Orden invertido: cantidad, documento, tipo_movimiento, sku, fecha
        csv_desordenado = (
            "cantidad,documento,tipo_movimiento,sku,fecha\n"
            "5,DOC-QA-01,salida,MP-0001,2026-03-10\n"
        )
        prev = ingesta.previsualizar_archivo("desorden.csv", csv_desordenado.encode('utf-8'), "movimientos_inventario")
        self.assertTrue(prev['valido'])
        self.assertEqual(len(prev['columnas_faltantes']), 0)

        carga = ingesta.ejecutar_carga_cinco_pasos("desorden.csv", csv_desordenado, "movimientos_inventario")
        self.assertIn(carga['estado_carga'], ['Exitoso', 'Parcial'])
        self.assertEqual(carga['filas_leidas'], 1)

    def test_05_csv_columnas_con_espacios_y_mayusculas(self):
        """Nombres de columnas con espacios y mayúsculas deben ser normalizados."""
        csv_espacios = (
            " FECHA , SKU , TIPO_MOVIMIENTO , CANTIDAD \n"
            "2026-03-10,MP-0001,salida,2\n"
        )
        prev = ingesta.previsualizar_archivo("espacios.csv", csv_espacios.encode('utf-8'), "movimientos_inventario")
        self.assertTrue(prev['valido'])
        self.assertIn('fecha', prev['columnas_encontradas'])

    def test_06_csv_columnas_faltantes(self):
        """CSV al que le falta una columna obligatoria debe ser rechazado con mensaje explícito."""
        csv_incompleto = (
            "fecha,cantidad,tipo_movimiento\n"
            "2026-03-10,5,salida\n"
        )
        prev = ingesta.previsualizar_archivo("incompleto.csv", csv_incompleto.encode('utf-8'), "movimientos_inventario")
        self.assertFalse(prev['valido'])
        self.assertIn('sku', prev['columnas_faltantes'])

        carga = ingesta.ejecutar_carga_cinco_pasos("incompleto.csv", csv_incompleto, "movimientos_inventario")
        self.assertEqual(carga['estado_carga'], 'Rechazado')
        self.assertEqual(carga['status'], 'error_validacion')

    # -------------------------------------------------------------
    # 3. FECHAS INVÁLIDAS, MES 13 Y AÑOS LEJANOS
    # -------------------------------------------------------------
    def test_07_fechas_invalidas_especificas(self):
        """Detecta mes 13 (2026-13-05), 30 de febrero y años lejanos (1800, 2099)."""
        # Mes 13
        f, err = ingesta.validar_y_normalizar_fecha("2026-13-05")
        self.assertIsNone(f)
        self.assertIn("13 fuera de rango", err)

        # 30 de febrero
        f, err = ingesta.validar_y_normalizar_fecha("2026-02-30")
        self.assertIsNone(f)
        self.assertIn("inexistente o inválida", err)

        # Año lejano pasado (1800)
        f, err = ingesta.validar_y_normalizar_fecha("1800-05-15")
        self.assertIsNone(f)
        self.assertIn("fuera del horizonte", err)

        # Año lejano futuro (2099)
        f, err = ingesta.validar_y_normalizar_fecha("2099-01-01")
        self.assertIsNone(f)
        self.assertIn("fuera del horizonte", err)

        # Fecha válida
        f, err = ingesta.validar_y_normalizar_fecha("2026-03-15")
        self.assertEqual(f, "2026-03-15")
        self.assertIsNone(err)

    def test_08_carga_parcial_aislamiento_fila_invalida(self):
        """
        Si un lote contiene 3 filas y la fila 2 tiene fecha inválida ('2026-13-05'):
        las filas 1 y 3 deben asentarse y la fila 2 debe ser rechazada con mensaje explicativo.
        """
        lote_mixto = (
            "fecha,sku,tipo_movimiento,cantidad,documento\n"
            "2026-03-01,MP-0001,salida,1,DOC-QA-VAL-01\n"
            "2026-13-05,MP-0001,salida,2,DOC-QA-INV-02\n"
            "2026-03-03,MP-0001,salida,3,DOC-QA-VAL-03\n"
        )
        carga = ingesta.ejecutar_carga_cinco_pasos("lote_mixto.csv", lote_mixto, "movimientos_inventario")
        self.assertEqual(carga['filas_leidas'], 3)
        self.assertEqual(carga['filas_rechazadas'], 1)
        self.assertEqual(carga['estado_carga'], 'Parcial')
        self.assertIn("No fue posible procesar la fila 2", carga['resumen_ejecutivo'])
        self.assertIn("resto de los datos se procesó correctamente", carga['resumen_ejecutivo'])

    # -------------------------------------------------------------
    # 4. RESILIENCIA CONTRA DIVISIONES POR CERO Y DATAFRAMES VACÍOS
    # -------------------------------------------------------------
    def test_09_resiliencia_division_por_cero(self):
        """Módulos matemáticos deben soportar DataFrames vacíos o valores en cero sin error."""
        # 1. ABC con demanda cero o DataFrame vacío
        df_vacio = pd.DataFrame(columns=['sku', 'descripcion', 'categoria', 'costo_unitario', 'demanda_anual_d'])
        res_abc = abc.clasificar_abc(df_vacio)
        self.assertEqual(res_abc['valor_total_anual'], 0.0)
        self.assertEqual(res_abc['resumen_clases']['A']['skus'], 0)

        # 2. Reposición con DataFrame vacío
        res_rep = reposicion.calcular_parametros_reposicion(df_vacio, {})
        self.assertEqual(res_rep['total_evaluados'], 0)

        # 3. ERI con estado vacío
        res_eri = eri.auditar_eri({})
        self.assertEqual(res_eri['eri_global_pct'], 0.0)
        self.assertEqual(res_eri['total_auditados'], 0)

        # 4. BOM con estado vacío
        res_bom = bom.explotar_bom({})
        self.assertEqual(res_bom['total_insumos_activos'], 0)

    # -------------------------------------------------------------
    # 5. ENDPOINTS HTTP Y BLINDAJE DEFENSIVO (CERO 500)
    # -------------------------------------------------------------
    def test_10_endpoint_decidir_sin_sku(self):
        """GET /api/decidir sin parámetro sku debe responder 200 con mensaje de error controlado, jamás 500."""
        url = f"http://127.0.0.1:{QA_PORT}/api/decidir"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data.get('status'), 'error')
            self.assertIn('sku', data.get('mensaje', '').lower())

    def test_11_endpoint_previsualizar_payload_vacio(self):
        """POST /api/previsualizar con payload vacío debe responder ordenadamente."""
        url = f"http://127.0.0.1:{QA_PORT}/api/previsualizar"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertFalse(data.get('valido'))

    def test_12_endpoint_ruta_inexistente_404_json(self):
        """Ruta inexistente debe retornar 404 estructurado en JSON sin pantalla de error nativa."""
        url = f"http://127.0.0.1:{QA_PORT}/api/ruta_no_existente"
        try:
            urllib.request.urlopen(url, timeout=5)
            self.fail("Se esperaba código 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            body = json.loads(e.read().decode('utf-8'))
            self.assertEqual(body.get('status'), 'error')
            self.assertIn('no encontrada', body.get('mensaje', '').lower())


if __name__ == '__main__':
    unittest.main()
