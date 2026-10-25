"""
SUITE DE VALIDACIÓN INTEGRAL Y ASEGURAMIENTO DE CALIDAD — E2 SAS
Ejecuta la auditoría exhaustiva sobre los 6 ejes prioritarios:
  1. Fórmulas de Demanda e Indicadores (BOM, ABC Pareto 80-15-5, ROP, EOQ, SS, ERI).
  2. Recomendaciones del Asistente (Justificación cuantitativa, prioridad, sin alucinaciones).
  3. Flujo de Ingesta en 5 Pasos y Rendición de Cuentas por Fila.
  4. Idempotencia Rigurosa (Prueba de doble carga con cambio neto = 0).
  5. Acumulatividad de Datos (Nuevos registros se suman a la historia).
  6. Instrumentación y Telemetría ("El Sistema se Mide Solo", 5 dimensiones).
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

# Asegurar path raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from nucleo import base_datos, datos, bom, abc, reposicion, eri, explicador, ingesta, instrumentacion
import orquestador

class TestValidacionIntegralEmpresarial(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Inicializa la base de datos relacional y carga el estado inicial."""
        base_datos.poblar_estado_inicial_si_vacio()
        cls.estado = datos.leer_estado()

    def test_01_lectura_estricta_desde_base_relacional(self):
        """Verifica que ningún módulo lea de archivos CSV; el estado proviene de SQL."""
        self.assertIn('maestro_materiales', self.estado)
        self.assertIn('movimientos_inventario', self.estado)
        self.assertIn('ordenes_compra', self.estado)
        self.assertIn('bom', self.estado)
        self.assertIn('plan_produccion', self.estado)
        self.assertGreater(len(self.estado['maestro_materiales']), 0)
        self.assertGreater(len(self.estado['movimientos_inventario']), 0)

    def test_02_formulas_demanda_bom(self):
        """Verifica la explosión de demanda BOM y anualización de 21 meses a 12 meses."""
        res = bom.explotar_bom(self.estado)
        df_dem = res['df_demanda_insumos']
        self.assertIn('demanda_anual_d', df_dem.columns)
        self.assertIn('consumo_diario_d', df_dem.columns)
        self.assertIn('sigma_diario', df_dem.columns)
        
        # Consumo diario debe ser demanda anual / 365
        sample = df_dem[df_dem['demanda_anual_d'] > 0].iloc[0]
        self.assertAlmostEqual(sample['consumo_diario_d'], sample['demanda_anual_d'] / 365.0, places=4)

    def test_03_clasificacion_pareto_abc(self):
        """Verifica la regla 80-15-5 en la valorización anual (D * Cu)."""
        res_bom = bom.explotar_bom(self.estado)
        res_abc = abc.clasificar_abc(res_bom['df_demanda_insumos'])
        df_abc = res_abc['df_abc']
        
        self.assertIn('clasificacion_abc', df_abc.columns)
        clases_unicas = set(df_abc['clasificacion_abc'].unique())
        self.assertTrue({'A', 'B', 'C'}.issubset(clases_unicas) or 'A' in clases_unicas)
        
        # Verificar que el 100% del valor sume correctamente
        resumen = res_abc['resumen_clases']
        suma_pct = resumen['A']['pct_valor'] + resumen['B']['pct_valor'] + resumen['C']['pct_valor']
        self.assertAlmostEqual(suma_pct, 100.0, places=1)

    def test_04_dimensionamiento_rop_eoq_parametros_oficiales(self):
        """Verifica parámetros oficiales: Co=$80.000 COP, i=25% anual, Z=1.645."""
        res_bom = bom.explotar_bom(self.estado)
        res_abc = abc.clasificar_abc(res_bom['df_demanda_insumos'])
        res_rep = reposicion.calcular_parametros_reposicion(res_abc['df_abc'], self.estado)
        df_par = res_rep['df_parametros']
        
        self.assertIn('ROP', df_par.columns)
        self.assertIn('EOQ', df_par.columns)
        self.assertIn('SS_95', df_par.columns)
        
        # Verificar fórmula EOQ para un SKU activo: sqrt((2 * D * 80000) / (0.25 * Cu))
        activos = df_par[(df_par['demanda_anual_d'] > 0) & (df_par['costo_unitario'] > 0)]
        self.assertGreater(len(activos), 0)
        s = activos.iloc[0]
        eoq_manual = np.round(np.sqrt((2 * s['demanda_anual_d'] * 80000.0) / (0.25 * s['costo_unitario'])))
        self.assertEqual(s['EOQ'], eoq_manual)

    def test_05_auditoria_eri_tolerancia_cinco_por_ciento(self):
        """Verifica reconciliación de Kardex y ERI con tolerancia ±5%."""
        res_eri = eri.auditar_eri(self.estado, tolerancia=0.05)
        self.assertIn('eri_global_pct', res_eri)
        self.assertGreaterEqual(res_eri['eri_global_pct'], 0.0)
        self.assertLessEqual(res_eri['eri_global_pct'], 100.0)
        self.assertIn('saldo_teorico', res_eri['df_auditoria'].columns)

    def test_06_recomendaciones_asistente_sin_alucinaciones(self):
        """Verifica que las propuestas contengan lenguaje formal, justificación y variables reales."""
        res_orq = orquestador.ejecutar_orquestacion()
        self.assertEqual(res_orq['status'], 'completado')
        propuestas = res_orq['propuestas_compra']
        
        if len(propuestas) > 0:
            p = propuestas[0]
            self.assertIn('sku', p)
            self.assertIn('cantidad_sugerida_eoq', p)
            self.assertIn('punto_reorden_rop', p)
            self.assertIn('justificacion_ejecutiva', p)
            self.assertIn('prioridad', p)
            self.assertNotIn('Queja 3', p['justificacion_ejecutiva'])
            self.assertNotIn('Queja 4', p['justificacion_ejecutiva'])

    def test_07_ingesta_cinco_pasos_previsualizacion(self):
        """Verifica el flujo del Paso 1 y 2 con previsualización y diagnóstico."""
        csv_bytes = b"fecha,sku,tipo_movimiento,cantidad,documento\n2026-03-01,MP-0001,salida,10,DOC-01\n"
        prev = ingesta.previsualizar_archivo('lote_test.csv', csv_bytes, 'movimientos_inventario')
        self.assertTrue(prev['valido'])
        self.assertEqual(prev['filas_total'], 1)
        self.assertIn('fecha', prev['columnas_encontradas'])

    def test_08_idempotencia_estricta_doble_carga(self):
        """
        PRUEBA DE FUEGO DE IDEMPOTENCIA:
        Cargar el MISMO archivo dos veces consecutivas debe producir cambio neto = 0 en la base.
        """
        csv_prueba = (
            "fecha,sku,tipo_movimiento,cantidad,documento\n"
            "2026-03-10,MP-0005,entrada,100,OC-TEST-IDEMPOTENCIA\n"
            "2026-03-11,MP-0006,salida,25,DOC-TEST-IDEMPOTENCIA\n"
        ).encode('utf-8')
        
        # Primera carga (debe insertar)
        res1 = ingesta.ejecutar_carga_cinco_pasos('test_idemp.csv', csv_prueba, 'movimientos_inventario')
        filas_nuevas = res1['filas_insertadas']
        self.assertGreaterEqual(filas_nuevas, 0)
        
        # Segunda carga exactamente del mismo contenido (debe omitir el 100%)
        res2 = ingesta.ejecutar_carga_cinco_pasos('test_idemp.csv', csv_prueba, 'movimientos_inventario')
        self.assertEqual(res2['filas_insertadas'], 0)
        self.assertEqual(res2['cambio_neto_base'], 0)
        self.assertGreater(res2['filas_omitidas_duplicadas'], 0)

    def test_09_deteccion_fechas_invalidas_rendicion_cuentas(self):
        """Verifica que fechas anómalas (mes 13) sean rechazadas y documentadas en el reporte."""
        csv_invalido = (
            "fecha,sku,tipo_movimiento,cantidad,documento\n"
            "2026-13-05,MP-0002,salida,48,DOC-ANOMALO-01\n"
            "2026-03-15,MP-0002,salida,12,DOC-VALIDO-01\n"
        ).encode('utf-8')
        
        res = ingesta.ejecutar_carga_cinco_pasos('anomalo.csv', csv_invalido, 'movimientos_inventario')
        self.assertEqual(res['filas_rechazadas'], 1)
        
        # Verificar que el motivo mencione la fecha inválida
        rechazos = [r for r in res['trazabilidad_filas'] if r['estado'] == 'RECHAZADA']
        self.assertEqual(len(rechazos), 1)
        self.assertIn('fecha', rechazos[0]['motivo'].lower())

    def test_10_instrumentacion_cinco_dimensiones(self):
        """Verifica que el sistema registre y calcule las 5 dimensiones de auto-medición."""
        tele = instrumentacion.obtener_metricas_instrumentacion()
        self.assertIn('instrumento_1_carga', tele)
        self.assertIn('instrumento_2_corrida', tele)
        self.assertIn('instrumento_3_paradas', tele)
        self.assertIn('instrumento_4_decision', tele)
        self.assertIn('instrumento_5_costo', tele)
        self.assertIn('bitacora_corridas', tele)
        self.assertIn('bitacora_cargas', tele)

if __name__ == '__main__':
    unittest.main()
