import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from nucleo import base_datos, datos, ingesta


class TestSincronizacionSupabaseIngesta(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path_original = base_datos.DB_PATH
        base_datos.DB_PATH = os.path.join(self.temp_dir.name, 'kardex_e2.db')
        base_datos.poblar_estado_inicial_si_vacio()

    def tearDown(self):
        base_datos.DB_PATH = self.db_path_original
        self.temp_dir.cleanup()

    def test_selector_acepta_las_doce_tablas_de_supabase(self):
        self.assertEqual(len(ingesta.TIPOS_DOCUMENTO_SOPORTADOS), 12)
        preview = ingesta.previsualizar_archivo(
            'bodega.csv',
            b'codigo,conteo_jefe_limpio\nMP-0001,12\n',
            'Inventario_bodega_JEFE'
        )
        self.assertTrue(preview['valido'])

    @patch('nucleo.ingesta_supabase.datos.supabase_sync_bom')
    def test_bom_usa_clave_compuesta_y_omite_id_generado(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        result = ingesta.ejecutar_carga_cinco_pasos(
            'bom.csv',
            'producto,sku_material,cantidad_por_unidad,unidad,id_bom\n'
            'PT-ESC-STD,MP-0001,2.5,unidad,ID-IGNORADO\n',
            'bom'
        )

        self.assertEqual(result['estado_carga'], 'Exitoso')
        upsert.assert_called_once_with([{
                'producto': 'PT-ESC-STD',
                'sku_material': 'MP-0001',
                'cantidad_por_unidad': 2.5,
                'unidad': 'unidad'
            }])

    @patch('nucleo.ingesta_supabase.datos.supabase_upsert')
    def test_inventario_jefe_mapea_conteo_limpio_a_columna_remota(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        result = ingesta.ejecutar_carga_cinco_pasos(
            'bodega.csv',
            'material,codigo,conteo_jefe,conteo_jefe_limpio,observacion\n'
            'Lamina,MP-0001,12,42,ok\n',
            'Inventario_bodega_JEFE'
        )

        self.assertEqual(result['sincronizacion_supabase']['status'], 'success')
        upsert.assert_called_once_with(
            'Inventario_bodega_JEFE',
            [{'codigo': 'MP-0001', 'conteo_jefe': 42, 'material': 'Lamina', 'observacion': 'ok'}],
            on_conflict_col=('codigo',),
            do_update=True
        )

    @patch('nucleo.ingesta_supabase.datos.supabase_insert')
    def test_decisiones_omiten_id_identity_y_no_reinsertan_archivo_igual(self, insert):
        insert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        csv = 'id,sku,decision,planeador,motivo\n1,MP-0001,APROBAR,QA,Prueba\n'
        primera = ingesta.ejecutar_carga_cinco_pasos(
            'decisiones.csv', csv, 'registro_decisiones_compras'
        )
        segunda = ingesta.ejecutar_carga_cinco_pasos(
            'decisiones.csv', csv, 'registro_decisiones_compras'
        )

        self.assertEqual(primera['sincronizacion_supabase']['status'], 'success')
        self.assertEqual(segunda['filas_cargadas'], 0)
        self.assertTrue(segunda['sincronizacion_supabase']['archivo_duplicado'])
        insert.assert_called_once_with(
            'registro_decisiones_compras',
            [{'sku': 'MP-0001', 'decision': 'APROBAR', 'planeador': 'QA', 'motivo': 'Prueba'}]
        )

    @patch('nucleo.ingesta_supabase.datos.supabase_upsert')
    def test_plan_produccion_se_sincroniza_con_conflicto_compuesto(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        result = ingesta.ejecutar_carga_cinco_pasos(
            'plan.csv',
            'periodo,producto,cantidad_planeada,cantidad_real\n'
            '2026-10-01,PT-ESC-EJE,5,4\n',
            'plan_produccion'
        )

        self.assertEqual(result['sincronizacion_supabase']['status'], 'success')
        upsert.assert_called_once_with(
            'plan_produccion',
            [{
                'periodo': '2026-10-01',
                'producto': 'PT-ESC-EJE',
                'cantidad_planeada': 5,
                'cantidad_real': 4
            }],
            on_conflict_col=('periodo', 'producto'),
            do_update=True
        )

    @patch('nucleo.ingesta_supabase.datos.supabase_upsert')
    def test_numero_invalido_se_agrega_a_filas_rechazadas(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        result = ingesta.ejecutar_carga_cinco_pasos(
            'plan_mixto.csv',
            'periodo,producto,cantidad_planeada,cantidad_real\n'
            '2026-10-01,PT-ESC-EJE,5,4\n'
            '2026-10-02,PT-ESC-EJE,2.5,2\n',
            'plan_produccion'
        )

        self.assertEqual(result['filas_rechazadas'], 1)
        self.assertEqual(result['estado_carga'], 'Parcial')
        rechazadas = [
            fila for fila in result['trazabilidad_filas']
            if fila['estado'] == 'RECHAZADA'
        ]
        self.assertEqual(len(rechazadas), 1)
        self.assertEqual(rechazadas[0]['fila'], 3)
        self.assertIn('cantidad_planeada debe ser un número entero', rechazadas[0]['detalle'])
        self.assertEqual(upsert.call_args.args[1], [{
            'periodo': '2026-10-01',
            'producto': 'PT-ESC-EJE',
            'cantidad_planeada': 5,
            'cantidad_real': 4
        }])

    @patch('nucleo.datos.supabase_upsert')
    def test_numero_no_finito_en_conteo_se_rechaza_antes_de_enviar(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        result = ingesta.ejecutar_carga_cinco_pasos(
            'conteo_mixto.csv',
            'sku,stock_fisico_contado,fecha_conteo\n'
            'MP-0001,12,2026-10-20\n'
            'MP-0002,Infinity,2026-10-20\n',
            'conteo_fisico'
        )

        self.assertEqual(result['filas_rechazadas'], 1)
        rechazadas = [
            fila for fila in result['trazabilidad_filas']
            if fila['estado'] == 'RECHAZADA'
        ]
        self.assertEqual(len(rechazadas), 1)
        self.assertIn('número finito', rechazadas[0]['detalle'])
        self.assertEqual(upsert.call_args.kwargs['payload'], [{
            'sku': 'MP-0001',
            'stock_fisico_contado': 12.0,
            'fecha_conteo': '2026-10-20'
        }])

    @patch('nucleo.datos.supabase_upsert')
    def test_ordenes_rechaza_decimales_y_envia_enteros_puros(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        csv = (
            'orden_compra,fecha_pedido,sku,cantidad,proveedor,costo_unitario\n'
            'OC-ENTERO,2026-10-20,MP-0001,100.0,Proveedor QA,2500.0\n'
            'OC-CANT-DECIMAL,2026-10-20,MP-0001,100.5,Proveedor QA,2500\n'
            'OC-COSTO-DECIMAL,2026-10-20,MP-0001,100,Proveedor QA,2500.2\n'
        )

        result = ingesta.ejecutar_carga_cinco_pasos(
            'ordenes_enteros.csv', csv, 'ordenes_compra'
        )

        self.assertEqual(result['filas_rechazadas'], 2)
        rechazadas = [
            fila for fila in result['trazabilidad_filas']
            if fila['estado'] == 'RECHAZADA'
        ]
        self.assertEqual(len(rechazadas), 2)
        self.assertTrue(all(
            fila['motivo'] ==
            'Cantidad inválida: no se permiten valores decimales en órdenes de compra'
            for fila in rechazadas
        ))

        payload = upsert.call_args.kwargs['payload']
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['cantidad'], 100)
        self.assertIs(type(payload[0]['cantidad']), int)
        self.assertEqual(payload[0]['costo_unitario'], 2500)
        self.assertIs(type(payload[0]['costo_unitario']), int)
        self.assertEqual(result['estado_carga'], 'Parcial')

    @patch('nucleo.ingesta_supabase.datos.supabase_upsert')
    def test_inventario_inicial_y_maestro_productos_sincronizan(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        inventario = ingesta.ejecutar_carga_cinco_pasos(
            'inventario.csv',
            'sku,stock_inicial,fecha\nMP-0001,24,2024-07-01\n',
            'inventario_inicial'
        )
        self.assertEqual(inventario['estado_carga'], 'Exitoso')
        self.assertEqual(upsert.call_args.args[0], 'inventario_inicial')
        self.assertEqual(upsert.call_args.args[1], [{
            'sku': 'MP-0001',
            'stock_inicial': 24,
            'fecha': '2024-07-01'
        }])

        upsert.reset_mock()
        producto = ingesta.ejecutar_carga_cinco_pasos(
            'productos.csv',
            'producto,nombre_producto\nPT-ESC-STD,Escritorio estándar actualizado\n',
            'maestro_productos'
        )
        self.assertEqual(producto['estado_carga'], 'Exitoso')
        self.assertEqual(upsert.call_args.args[0], 'maestro_productos')
        self.assertEqual(upsert.call_args.args[1], [{
            'producto': 'PT-ESC-STD',
            'nombre_producto': 'Escritorio estándar actualizado'
        }])

    @patch('nucleo.ingesta_supabase.datos.supabase_upsert')
    def test_auditoria_genera_uuid_estable_y_persiste_en_sqlite(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        csv = (
            'eri_global_pct,skus_en_quiebre,inversion_total_sugerida_cop,'
            'materiales_fantasmas,desfases_muelle,status\n'
            '98.5,2,150000,1,3,completado\n'
        )
        primera = ingesta.ejecutar_carga_cinco_pasos(
            'auditoria.csv', csv, 'auditoria_corridas_orquestacion'
        )
        segunda = ingesta.ejecutar_carga_cinco_pasos(
            'auditoria.csv', csv, 'auditoria_corridas_orquestacion'
        )

        id_primera = upsert.call_args_list[0].args[1][0]['id']
        id_segunda = upsert.call_args_list[1].args[1][0]['id']
        self.assertEqual(id_primera, id_segunda)
        self.assertEqual(primera['estado_carga'], 'Exitoso')
        self.assertEqual(segunda['filas_actualizadas'], 1)
        conn = base_datos.get_connection()
        self.assertEqual(
            conn.execute(
                'SELECT count(*) FROM bitacora_corridas WHERE id = ?',
                (id_primera,)
            ).fetchone()[0],
            1
        )
        conn.close()

    @patch('nucleo.ingesta_supabase.datos.supabase_insert')
    def test_propuestas_identity_solo_se_guarda_en_supabase(self, insert):
        insert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        csv = (
            'id,sku,descripcion,categoria,clase_abc,stock_real,punto_reorden_rop,'
            'stock_seguridad_ss,cantidad_sugerida_eoq,costo_unitario_cop,'
            'inversion_estimada_cop,justificacion_ejecutiva,estado_decision\n'
            '9,MP-0001,Material,General,A,3,5,2,4,100,400,Reposición necesaria,PENDIENTE\n'
        )
        result = ingesta.ejecutar_carga_cinco_pasos(
            'propuestas.csv', csv, 'propuestas_reposicion'
        )

        self.assertEqual(result['estado_carga'], 'Exitoso')
        self.assertFalse(result['persistencia_local'])
        payload = insert.call_args.args[1]
        self.assertEqual(len(payload), 1)
        self.assertNotIn('id', payload[0])
        self.assertEqual(payload[0]['sku'], 'MP-0001')

    @patch('nucleo.datos.supabase_upsert')
    def test_movimientos_envia_solo_filas_validas_con_columnas_del_esquema_y_reintenta(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        csv = (
            'fecha,sku,tipo_movimiento,cantidad,documento,bodega,responsable,columna_extra\n'
            '2026-10-20,MP-0001,entrada,4,DOC-SYNC-001,BOD-01,Operador,ignorar\n'
            '2026-10-20,SKU-INEXISTENTE,salida,2,DOC-SYNC-002,BOD-01,Operador,ignorar\n'
        )

        primera = ingesta.ejecutar_carga_cinco_pasos(
            'movimientos.csv', csv, 'movimientos_inventario'
        )
        self.assertEqual(primera['filas_rechazadas'], 1)
        self.assertEqual(primera['sincronizacion_supabase']['status'], 'success')
        upsert.assert_called_once_with(
            table_name='movimientos_inventario',
            payload=[{
                'fecha': '2026-10-20',
                'sku': 'MP-0001',
                'tipo_movimiento': 'entrada',
                'cantidad': 4.0,
                'documento': 'DOC-SYNC-001',
                'bodega': 'BOD-01',
                'responsable': 'Operador'
            }],
            on_conflict_col='documento',
            do_update=True
        )

        segunda = ingesta.ejecutar_carga_cinco_pasos(
            'movimientos.csv', csv, 'movimientos_inventario'
        )
        self.assertEqual(segunda['filas_insertadas'], 0)
        self.assertEqual(segunda['sincronizacion_supabase']['status'], 'success')
        self.assertEqual(upsert.call_count, 2)

    @patch('nucleo.datos.supabase_upsert')
    def test_ordenes_mapea_fecha_promesa_y_notifica_falla_remota(self, upsert):
        upsert.return_value = {
            'status': 'error',
            'msg': 'HTTP 400: error de prueba',
            'filas_sincronizadas': 0,
            'filas_pendientes': 1
        }
        csv = (
            'orden_compra,fecha_pedido,sku,cantidad,proveedor,fecha_promesa,fecha_recepcion,costo_unitario\n'
            'OC-SYNC-001,2026-10-20,MP-0001,5,Proveedor QA,2026-10-30,,1200\n'
        )

        result = ingesta.ejecutar_carga_cinco_pasos('ordenes.csv', csv, 'ordenes_compra')

        self.assertEqual(result['estado_carga'], 'Parcial')
        self.assertEqual(result['sincronizacion_supabase']['status'], 'error')
        self.assertIn('Supabase', result['resumen_ejecutivo'])
        upsert.assert_called_once_with(
            table_name='ordenes_compra',
            payload=[{
                'orden_compra': 'OC-SYNC-001',
                'fecha_pedido': '2026-10-20',
                'sku': 'MP-0001',
                'cantidad': 5.0,
                'proveedor': 'Proveedor QA',
                'fecha_promesa': '2026-10-30',
                'fecha_recepcion': None,
                'costo_unitario': 1200.0
            }],
            on_conflict_col='orden_compra',
            do_update=True
        )

    @patch('nucleo.datos.supabase_upsert')
    def test_conteo_y_materiales_usan_los_campos_admitidos_por_supabase(self, upsert):
        upsert.return_value = {'status': 'success', 'filas_sincronizadas': 1, 'filas_pendientes': 0}
        conteo = ingesta.ejecutar_carga_cinco_pasos(
            'conteo.csv',
            'sku,stock_fisico_contado,fecha_conteo,auditor\nMP-0001,12,2026-10-20,QA\n',
            'conteo_fisico'
        )
        self.assertEqual(conteo['sincronizacion_supabase']['status'], 'success')
        self.assertEqual(upsert.call_args.kwargs['table_name'], 'conteo_fisico')
        self.assertEqual(upsert.call_args.kwargs['payload'], [{
            'sku': 'MP-0001',
            'stock_fisico_contado': 12.0,
            'fecha_conteo': '2026-10-20'
        }])

        upsert.reset_mock()
        material = ingesta.ejecutar_carga_cinco_pasos(
            'materiales.csv',
            'sku,descripcion,categoria,unidad,costo_unitario,proveedor,lead_time_declarado_dias,stock_min,stock_max\n'
            'MP-SYNC-001,Material QA,Lamina,unidad,1200,Proveedor QA,4,2,20\n',
            'maestro_materiales'
        )
        self.assertEqual(material['sincronizacion_supabase']['status'], 'success')
        self.assertEqual(upsert.call_args.kwargs['table_name'], 'maestro_materiales')
        self.assertEqual(upsert.call_args.kwargs['payload'], [{
            'sku': 'MP-SYNC-001',
            'descripcion': 'Material QA',
            'categoria': 'Lámina',
            'unidad': 'unidad',
            'costo_unitario': 1200.0,
            'lead_time_declarado_dias': 4,
            'proveedor': 'Proveedor QA',
            'stock_min': 2,
            'stock_max': 20
        }])

    def test_no_acepta_silenciosamente_un_tipo_no_soportado(self):
        preview = ingesta.previsualizar_archivo('otro.csv', b'a,b', 'tipo_desconocido')
        result = ingesta.ejecutar_carga_cinco_pasos(
            'otro.csv', 'a,b\n1,2\n', 'tipo_desconocido'
        )
        self.assertFalse(preview['valido'])
        self.assertEqual(result['estado_carga'], 'Rechazado')
        self.assertEqual(result['sincronizacion_supabase']['status'], 'skipped')

    @patch('nucleo.datos.urllib.request.urlopen')
    def test_cliente_supabase_reporta_exito_http_y_conflicto(self, urlopen):
        class Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        urlopen.return_value = Response()
        with patch.object(datos, 'API_KEY', 'test-key'), patch.object(
            datos, 'SUPABASE_URL', 'https://example.supabase.co'
        ):
            result = datos.supabase_upsert(
                'conteo_fisico',
                [{'sku': 'MP-TEST-001', 'stock_fisico_contado': 10}],
                on_conflict_col='sku'
            )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['filas_sincronizadas'], 1)
        request = urlopen.call_args.args[0]
        self.assertIn('on_conflict=sku', request.full_url)
        self.assertIn('resolution=merge-duplicates', request.headers['Prefer'])
        self.assertTrue(request.headers['Authorization'].startswith('Bearer '))
        self.assertEqual(request.headers['Apikey'], 'test-key')

    @patch('nucleo.datos.urllib.request.urlopen')
    def test_upsert_admite_conflicto_compuesto(self, urlopen):
        class Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        urlopen.return_value = Response()
        with patch.object(datos, 'API_KEY', 'test-key'), patch.object(
            datos, 'SUPABASE_URL', 'https://example.supabase.co'
        ):
            result = datos.supabase_upsert(
                'bom',
                [{'producto': 'PT-ESC-STD', 'sku_material': 'MP-0001'}],
                on_conflict_col=('producto', 'sku_material')
            )

        self.assertEqual(result['status'], 'success')
        self.assertIn('on_conflict=producto,sku_material', urlopen.call_args.args[0].full_url)

    @patch('nucleo.datos.urllib.request.urlopen')
    def test_bom_actualiza_fila_existente_sin_constraint_unica(self, urlopen):
        class Response:
            status = 200

            def __init__(self, content=b'[]'):
                self.content = content

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return self.content

        urlopen.side_effect = [
            Response(b'[{"producto":"PT-ESC-STD","sku_material":"MP-0001"}]'),
            Response()
        ]
        with patch.object(datos, 'API_KEY', 'test-key'), patch.object(
            datos, 'SUPABASE_URL', 'https://example.supabase.co'
        ):
            result = datos.supabase_sync_bom([{
                'producto': 'PT-ESC-STD',
                'sku_material': 'MP-0001',
                'cantidad_por_unidad': 2.5,
                'unidad': 'unidad'
            }])

        self.assertEqual(result['status'], 'success')
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(urlopen.call_args_list[0].args[0].method, 'GET')
        self.assertEqual(urlopen.call_args_list[1].args[0].method, 'PATCH')

    @patch('nucleo.datos.urllib.request.urlopen')
    def test_cliente_supabase_expone_detalle_http_y_filas_pendientes(self, urlopen):
        urlopen.side_effect = HTTPError(
            'https://example.supabase.co/rest/v1/conteo_fisico',
            400,
            'Bad Request',
            {},
            BytesIO(b'{"message":"unknown column"}')
        )
        with patch.object(datos, 'API_KEY', 'test-key'), patch.object(
            datos, 'SUPABASE_URL', 'https://example.supabase.co'
        ):
            result = datos.supabase_upsert(
                'conteo_fisico',
                [{'sku': 'MP-TEST-001'}, {'sku': 'MP-TEST-002'}],
                on_conflict_col='sku',
                batch_size=1
            )

        self.assertEqual(result['status'], 'error')
        self.assertIn('Supabase rechazó los datos enviados', result['msg'])
        self.assertIn('unknown column', result['msg'])
        self.assertNotIn('HTTP 400', result['msg'])
        self.assertEqual(result['filas_sincronizadas'], 0)
        self.assertEqual(result['filas_pendientes'], 2)


if __name__ == '__main__':
    unittest.main()
