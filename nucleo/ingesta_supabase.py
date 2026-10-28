"""Ingesta CSV para las tablas de Supabase fuera del flujo transaccional principal."""

import hashlib
import json
import math
import os
import sqlite3
import uuid
from datetime import datetime

import pandas as pd

from nucleo import base_datos, datos


TABLAS_ADICIONALES = {
    'Inventario_bodega_JEFE': {
        'tabla': 'Inventario_bodega_JEFE',
        'columnas': ('material', 'codigo', 'conteo_jefe', 'observacion'),
        'requeridas': (('codigo',), ('conteo_jefe', 'conteo_jefe_limpio')),
        'alias_columnas': {'conteo_jefe_limpio': 'conteo_jefe'},
        'clave': ('codigo',),
        'enteros': ('conteo_jefe',),
        'local': 'inventario_bodega_jefe'
    },
    'inventario_inicial': {
        'tabla': 'inventario_inicial',
        'columnas': ('sku', 'stock_inicial', 'fecha'),
        'requeridas': (('sku',), ('stock_inicial',)),
        'enteros': ('stock_inicial',),
        'fechas': ('fecha',),
        'clave': ('sku',),
        'local': 'inventario_inicial'
    },
    'maestro_productos': {
        'tabla': 'maestro_productos',
        'columnas': ('producto', 'nombre_producto'),
        'requeridas': (('producto',), ('nombre_producto',)),
        'clave': ('producto',),
        'local': 'maestro_productos'
    },
    'bom': {
        'tabla': 'bom',
        'columnas': ('producto', 'sku_material', 'cantidad_por_unidad', 'unidad'),
        'requeridas': (('producto',), ('sku_material',), ('cantidad_por_unidad',)),
        'clave': ('producto', 'sku_material'),
        'numericas': ('cantidad_por_unidad',),
        'local': 'bom'
    },
    'plan_produccion': {
        'tabla': 'plan_produccion',
        'columnas': ('periodo', 'producto', 'cantidad_planeada', 'cantidad_real'),
        'requeridas': (('periodo',), ('producto',), ('cantidad_planeada',), ('cantidad_real',)),
        'fechas': ('periodo',),
        'enteros': ('cantidad_planeada', 'cantidad_real'),
        'clave': ('periodo', 'producto'),
        'local': 'plan_produccion'
    },
    'auditoria_corridas_orquestacion': {
        'tabla': 'auditoria_corridas_orquestacion',
        'columnas': (
            'id', 'created_at', 'eri_global_pct', 'skus_en_quiebre',
            'inversion_total_sugerida_cop', 'materiales_fantasmas',
            'desfases_muelle', 'status'
        ),
        'requeridas': (
            ('eri_global_pct',), ('skus_en_quiebre',),
            ('inversion_total_sugerida_cop',), ('materiales_fantasmas',),
            ('desfases_muelle',)
        ),
        'numericas': ('eri_global_pct', 'inversion_total_sugerida_cop'),
        'enteros': ('skus_en_quiebre', 'materiales_fantasmas', 'desfases_muelle'),
        'fechas_hora': ('created_at',),
        'uuid': ('id',),
        'clave': ('id',),
        'local': 'auditoria_corridas_orquestacion'
    },
    'propuestas_reposicion': {
        'tabla': 'propuestas_reposicion',
        'columnas': (
            'created_at', 'ciclo_orquestacion_id', 'sku', 'descripcion',
            'categoria', 'clase_abc', 'stock_real', 'punto_reorden_rop',
            'stock_seguridad_ss', 'cantidad_sugerida_eoq', 'costo_unitario_cop',
            'inversion_estimada_cop', 'justificacion_ejecutiva', 'estado_decision'
        ),
        'requeridas': (
            ('sku',), ('descripcion',), ('clase_abc',), ('stock_real',),
            ('punto_reorden_rop',), ('stock_seguridad_ss',),
            ('cantidad_sugerida_eoq',), ('costo_unitario_cop',),
            ('inversion_estimada_cop',), ('justificacion_ejecutiva',)
        ),
        'numericas': ('costo_unitario_cop', 'inversion_estimada_cop'),
        'enteros': (
            'stock_real', 'punto_reorden_rop', 'stock_seguridad_ss',
            'cantidad_sugerida_eoq'
        ),
        'fechas_hora': ('created_at',),
        'uuid': ('ciclo_orquestacion_id',),
        'append_only': True,
        'ignorar': ('id',),
        'local': None
    },
    'registro_decisiones_compras': {
        'tabla': 'registro_decisiones_compras',
        'columnas': ('created_at', 'sku', 'decision', 'planeador', 'motivo', 'propuesta_id'),
        'requeridas': (('sku',), ('decision',)),
        'enteros': ('propuesta_id',),
        'fechas_hora': ('created_at',),
        'append_only': True,
        'ignorar': ('id',),
        'local': None
    }
}

TIPOS_DOCUMENTO_ADICIONALES = frozenset(TABLAS_ADICIONALES)


def columnas_esperadas(tipo_documento):
    config = TABLAS_ADICIONALES[tipo_documento]
    return [
        ' o '.join(grupo)
        for grupo in config['requeridas']
    ]


def faltan_columnas(tipo_documento, columnas):
    config = TABLAS_ADICIONALES[tipo_documento]
    presentes = set(columnas)
    return [
        ' o '.join(grupo)
        for grupo in config['requeridas']
        if not any(nombre in presentes for nombre in grupo)
    ]


def _normalizar_columna(nombre, config):
    normalizada = str(nombre).strip().lower().replace('"', '').replace("'", '')
    return config.get('alias_columnas', {}).get(normalizada, normalizada)


def _parsear_valor(nombre, valor, config, numero_fila):
    if pd.isna(valor) or not str(valor).strip():
        return None

    valor = str(valor).strip()
    if nombre in config.get('numericas', ()) or nombre in config.get('enteros', ()):
        numero = float(valor.replace(',', '.'))
        if not math.isfinite(numero):
            raise ValueError(f'{nombre} debe ser un número finito')
        if nombre in config.get('enteros', ()):
            if not numero.is_integer():
                raise ValueError(f'{nombre} debe ser un número entero')
            return int(numero)
        return numero

    if nombre in config.get('fechas', ()):
        fecha = pd.to_datetime(valor, errors='raise')
        return fecha.date().isoformat()

    if nombre in config.get('fechas_hora', ()):
        fecha_hora = pd.to_datetime(valor, errors='raise', utc=True)
        return fecha_hora.isoformat()

    if nombre in config.get('uuid', ()):
        try:
            return str(uuid.UUID(valor))
        except ValueError as exc:
            raise ValueError(f'{nombre} no tiene formato UUID válido') from exc

    return valor


def _identificador(tipo_documento, record, numero_fila):
    config = TABLAS_ADICIONALES[tipo_documento]
    if tipo_documento == 'auditoria_corridas_orquestacion' and not record.get('id'):
        semilla = f"{tipo_documento}:{record['_hash_archivo']}:{numero_fila}"
        record['id'] = str(uuid.uuid5(uuid.NAMESPACE_URL, semilla))
    clave = config.get('clave')
    if clave:
        return ' | '.join(str(record.get(columna, '')) for columna in clave)
    return f'Fila {numero_fila}'


def _guardar_local(conn, tipo_documento, record):
    cursor = conn.cursor()
    if tipo_documento == 'Inventario_bodega_JEFE':
        cursor.execute(
            'SELECT 1 FROM inventario_bodega_jefe WHERE codigo = ?',
            (record['codigo'],)
        )
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO inventario_bodega_jefe (codigo, material, conteo_jefe, observacion)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                material = excluded.material,
                conteo_jefe = excluded.conteo_jefe,
                observacion = excluded.observacion
        """, (record['codigo'], record.get('material'), record['conteo_jefe'], record.get('observacion')))
    elif tipo_documento == 'inventario_inicial':
        cursor.execute('SELECT 1 FROM inventario_inicial WHERE sku = ?', (record['sku'],))
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO inventario_inicial (sku, stock_inicial, fecha_corte)
            VALUES (?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                stock_inicial = excluded.stock_inicial,
                fecha_corte = excluded.fecha_corte
        """, (record['sku'], record['stock_inicial'], record.get('fecha')))
    elif tipo_documento == 'maestro_productos':
        cursor.execute('SELECT 1 FROM maestro_productos WHERE producto = ?', (record['producto'],))
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO maestro_productos (producto, nombre_producto)
            VALUES (?, ?)
            ON CONFLICT(producto) DO UPDATE SET nombre_producto = excluded.nombre_producto
        """, (record['producto'], record['nombre_producto']))
    elif tipo_documento == 'bom':
        id_bom = f"{record['producto']}_{record['sku_material']}"
        cursor.execute('SELECT 1 FROM bom WHERE id_bom = ?', (id_bom,))
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO bom (id_bom, producto, sku_material, cantidad_por_unidad, unidad)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id_bom) DO UPDATE SET
                cantidad_por_unidad = excluded.cantidad_por_unidad,
                unidad = excluded.unidad
        """, (id_bom, record['producto'], record['sku_material'],
              record['cantidad_por_unidad'], record.get('unidad')))
    elif tipo_documento == 'plan_produccion':
        id_plan = f"{record['periodo']}_{record['producto']}"
        cursor.execute('SELECT 1 FROM plan_produccion WHERE id_plan = ?', (id_plan,))
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO plan_produccion
                (id_plan, periodo, producto, cantidad_planeada, cantidad_real)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id_plan) DO UPDATE SET
                cantidad_planeada = excluded.cantidad_planeada,
                cantidad_real = excluded.cantidad_real
        """, (id_plan, record['periodo'], record['producto'],
              record['cantidad_planeada'], record['cantidad_real']))
    elif tipo_documento == 'auditoria_corridas_orquestacion':
        cursor.execute('SELECT 1 FROM bitacora_corridas WHERE id = ?', (record['id'],))
        existe = cursor.fetchone() is not None
        cursor.execute("""
            INSERT INTO bitacora_corridas (
                id, timestamp, duracion_ms, total_skus, eri_global_pct,
                skus_en_quiebre, inversion_total_cop, materiales_fantasmas,
                desfases_muelle, criterio_parada_activado, motivo_parada, status
            ) VALUES (?, ?, 0, 0, ?, ?, ?, ?, ?, 0, NULL, ?)
            ON CONFLICT(id) DO UPDATE SET
                timestamp = excluded.timestamp,
                eri_global_pct = excluded.eri_global_pct,
                skus_en_quiebre = excluded.skus_en_quiebre,
                inversion_total_cop = excluded.inversion_total_cop,
                materiales_fantasmas = excluded.materiales_fantasmas,
                desfases_muelle = excluded.desfases_muelle,
                status = excluded.status
        """, (
            record['id'],
            record.get('created_at') or datetime.now().astimezone().isoformat(),
            record['eri_global_pct'],
            record['skus_en_quiebre'],
            record['inversion_total_sugerida_cop'],
            record['materiales_fantasmas'],
            record['desfases_muelle'],
            record.get('status', 'completado')
        ))
    else:
        raise ValueError(f'No existe persistencia local configurada para {tipo_documento}')

    return not existe


def _respuesta_rechazo(nombre_archivo, tipo_documento, hash_archivo, mensaje, filas_leidas=0):
    return {
        'status': 'error_validacion',
        'mensaje': mensaje,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tipo_documento': tipo_documento,
        'hash_archivo_sha256': hash_archivo,
        'estado_carga': 'Rechazado',
        'filas_leidas': filas_leidas,
        'filas_insertadas': 0,
        'filas_actualizadas': 0,
        'filas_insertadas_o_actualizadas': 0,
        'filas_cargadas': 0,
        'filas_omitidas_duplicadas': 0,
        'filas_rechazadas': filas_leidas,
        'sincronizacion_supabase': {
            'status': 'skipped',
            'msg': mensaje,
            'filas_sincronizadas': 0,
            'filas_pendientes': filas_leidas
        },
        'resumen_ejecutivo': mensaje,
        'trazabilidad_filas': []
    }


def ejecutar_ingesta(nombre_archivo, contenido_bytes, df_raw, tipo_documento, usuario):
    config = TABLAS_ADICIONALES[tipo_documento]
    id_carga = str(uuid.uuid4())
    timestamp_carga = datetime.now().astimezone().isoformat()
    hash_archivo = hashlib.sha256(contenido_bytes).hexdigest()
    df = df_raw.copy()
    df.columns = [
        str(columna).strip().lower().replace('"', '').replace("'", '')
        for columna in df.columns
    ]
    filas_leidas = len(df)

    if len(set(df.columns)) != len(df.columns):
        return _respuesta_rechazo(
            nombre_archivo, tipo_documento, hash_archivo,
            'El CSV contiene encabezados duplicados después de normalizar sus nombres.',
            filas_leidas
        )

    if tipo_documento == 'Inventario_bodega_JEFE':
        if 'conteo_jefe_limpio' in df.columns and 'conteo_jefe' in df.columns:
            df['conteo_jefe'] = df['conteo_jefe_limpio']
            df = df.drop(columns=['conteo_jefe_limpio'])
        elif 'conteo_jefe_limpio' in df.columns:
            df = df.rename(columns={'conteo_jefe_limpio': 'conteo_jefe'})
    else:
        df.columns = [_normalizar_columna(columna, config) for columna in df.columns]

    if len(set(df.columns)) != len(df.columns):
        return _respuesta_rechazo(
            nombre_archivo, tipo_documento, hash_archivo,
            'El CSV contiene encabezados duplicados después de normalizar sus nombres.',
            filas_leidas
        )

    faltantes = faltan_columnas(tipo_documento, df.columns)
    if faltantes:
        return _respuesta_rechazo(
            nombre_archivo, tipo_documento, hash_archivo,
            f"Faltan columnas requeridas: {', '.join(faltantes)}.",
            filas_leidas
        )

    conn = base_datos.get_connection()
    filas_insertadas = 0
    filas_actualizadas = 0
    filas_omitidas = 0
    filas_rechazadas = 0
    trazabilidad = []
    records_supabase = []
    claves_vistas = set()
    append_file_already_uploaded = False

    if config.get('append_only'):
        append_file_already_uploaded = conn.execute("""
            SELECT 1 FROM control_ingesta_supabase
            WHERE tipo_documento = ? AND hash_archivo_sha256 = ?
        """, (tipo_documento, hash_archivo)).fetchone() is not None

    columnas = set(df.columns)
    for indice, (_, fila) in enumerate(df.iterrows(), start=2):
        record = {}
        error = None
        try:
            for columna in config['columnas']:
                if columna not in columnas:
                    continue
                valor = _parsear_valor(columna, fila[columna], config, indice)
                if valor is not None or columna in config['requeridas'][0]:
                    record[columna] = valor
            for grupo in config['requeridas']:
                if not any(record.get(nombre) not in (None, '') for nombre in grupo):
                    raise ValueError(f"Falta un valor requerido ({' o '.join(grupo)})")
            for grupo in config['requeridas']:
                if len(grupo) > 1 and not record.get(grupo[0]) and record.get(grupo[1]):
                    record[grupo[0]] = record.pop(grupo[1])
            if tipo_documento == 'auditoria_corridas_orquestacion' and not record.get('id'):
                record['id'] = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f'{tipo_documento}:{hash_archivo}:{indice}'
                ))
        except (ValueError, TypeError, OverflowError) as exc:
            error = str(exc)

        if error is None:
            clave = tuple(record.get(nombre) for nombre in config.get('clave', ()))
            if clave and clave in claves_vistas:
                filas_omitidas += 1
                trazabilidad.append({
                    'fila': indice,
                    'identificador': ' | '.join(str(valor) for valor in clave),
                    'estado': 'OMITIDA',
                    'motivo': 'Clave duplicada dentro del archivo',
                    'detalle': 'La primera fila con esta clave se conserva para el UPSERT.',
                    'valor_original': str(clave)
                })
                continue
            if clave:
                claves_vistas.add(clave)

            if config.get('append_only') and append_file_already_uploaded:
                filas_omitidas += 1
                trazabilidad.append({
                    'fila': indice,
                    'identificador': f'Fila {indice}',
                    'estado': 'OMITIDA',
                    'motivo': 'Archivo ya sincronizado',
                    'detalle': 'El mismo archivo ya se cargó correctamente; se evita duplicar registros.',
                    'valor_original': hash_archivo
                })
                continue

            record['_hash_archivo'] = hash_archivo
            records_supabase.append({
                key: value
                for key, value in record.items()
                if key != '_hash_archivo' and key in config['columnas']
            })

            local = config.get('local')
            if local:
                conn.execute('SAVEPOINT fila_ingesta')
                try:
                    es_insert = _guardar_local(conn, tipo_documento, record)
                    conn.execute('RELEASE SAVEPOINT fila_ingesta')
                    if es_insert:
                        filas_insertadas += 1
                    else:
                        filas_actualizadas += 1
                except sqlite3.IntegrityError as exc:
                    conn.execute('ROLLBACK TO SAVEPOINT fila_ingesta')
                    conn.execute('RELEASE SAVEPOINT fila_ingesta')
                    records_supabase.pop()
                    filas_rechazadas += 1
                    trazabilidad.append({
                        'fila': indice,
                        'identificador': _identificador(tipo_documento, record, indice),
                        'estado': 'RECHAZADA',
                        'motivo': 'Integridad relacional local',
                        'detalle': str(exc),
                        'valor_original': json.dumps(record, ensure_ascii=False, default=str)
                    })
                    continue

            trazabilidad.append({
                'fila': indice,
                'identificador': _identificador(tipo_documento, record, indice),
                'estado': 'INSERTADA',
                'motivo': 'Registro validado',
                'detalle': 'Preparado para sincronizar con Supabase.',
                'valor_original': json.dumps(record, ensure_ascii=False, default=str)
            })
        else:
            filas_rechazadas += 1
            trazabilidad.append({
                'fila': indice,
                'identificador': f'Fila {indice}',
                'estado': 'RECHAZADA',
                'motivo': 'Validación de valor',
                'detalle': error,
                'valor_original': json.dumps(fila.to_dict(), ensure_ascii=False, default=str)
            })

    if config.get('append_only') and filas_rechazadas:
        records_supabase.clear()
        for fila in trazabilidad:
            if fila['estado'] == 'INSERTADA':
                fila['estado'] = 'RECHAZADA'
                fila['motivo'] = 'Carga atómica append-only'
                fila['detalle'] = 'No se insertó el lote porque contiene filas inválidas.'
                filas_rechazadas += 1

    conn.commit()
    persistencia_local = bool(config.get('local'))

    if append_file_already_uploaded:
        sync = {
            'status': 'success',
            'msg': 'El mismo archivo ya se sincronizó anteriormente; no se repitió la inserción.',
            'filas_sincronizadas': 0,
            'filas_pendientes': 0,
            'archivo_duplicado': True
        }
    elif not records_supabase:
        sync = {
            'status': 'skipped',
            'msg': 'No hay filas válidas nuevas para sincronizar.',
            'filas_sincronizadas': 0,
            'filas_pendientes': 0
        }
    elif tipo_documento == 'bom':
        sync = datos.supabase_sync_bom(records_supabase)
    elif config.get('append_only'):
        sync = datos.supabase_insert(config['tabla'], records_supabase)
    else:
        sync = datos.supabase_upsert(
            config['tabla'], records_supabase,
            on_conflict_col=config['clave'],
            do_update=True
        )

    filas_remotas = sync.get('filas_sincronizadas', 0)
    filas_locales = filas_insertadas + filas_actualizadas
    filas_cargadas = filas_locales if persistencia_local else filas_remotas
    insertadas_reporte = filas_insertadas if persistencia_local else filas_remotas
    actualizadas_reporte = filas_actualizadas if persistencia_local else 0

    if config.get('append_only') and sync.get('status') == 'success' and records_supabase:
        conn.execute("""
            INSERT OR IGNORE INTO control_ingesta_supabase
                (tipo_documento, hash_archivo_sha256, timestamp)
            VALUES (?, ?, ?)
        """, (tipo_documento, hash_archivo, datetime.now().astimezone().isoformat()))
        conn.commit()

    conn.execute("""
        INSERT INTO bitacora_cargas
            (id, timestamp, nombre_archivo, tipo_documento, filas_leidas,
             filas_cargadas, filas_rechazadas, filas_omitidas_duplicadas,
             detalle_rechazos, usuario, hash_archivo_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_carga,
        timestamp_carga,
        os.path.basename(nombre_archivo),
        tipo_documento,
        filas_leidas,
        filas_cargadas,
        filas_rechazadas,
        filas_omitidas,
        sync.get('msg', ''),
        usuario,
        hash_archivo
    ))
    conn.commit()
    conn.close()

    if filas_rechazadas == 0 and sync.get('status') in ('success', 'skipped'):
        estado = 'Exitoso'
    elif filas_cargadas or filas_omitidas:
        estado = 'Parcial'
    else:
        estado = 'Rechazado'

    resumen = (
        f'{filas_leidas} filas leídas; {insertadas_reporte} insertadas, '
        f'{actualizadas_reporte} actualizadas, {filas_omitidas} omitidas y '
        f'{filas_rechazadas} rechazadas.'
    )
    if sync.get('status') == 'error':
        resumen += f" Supabase no confirmó la carga: {sync.get('msg', 'error desconocido')}."
        if persistencia_local:
            resumen += ' Los cambios locales quedaron asentados.'
        estado = 'Parcial' if persistencia_local and (filas_insertadas + filas_actualizadas) else 'Rechazado'
    elif not persistencia_local:
        resumen += ' Esta tabla se guarda únicamente en Supabase.'

    if sync.get('archivo_duplicado'):
        resumen += ' El archivo ya se había cargado; no se duplicaron sus registros append-only.'

    return {
        'status': 'completado',
        'id_carga': id_carga,
        'timestamp': timestamp_carga,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tipo_documento': tipo_documento,
        'hash_archivo_sha256': hash_archivo,
        'estado_carga': estado,
        'filas_leidas': filas_leidas,
        'total_registros_procesados': filas_leidas,
        'filas_insertadas': insertadas_reporte,
        'filas_actualizadas': actualizadas_reporte,
        'filas_insertadas_o_actualizadas': filas_cargadas,
        'filas_cargadas': filas_cargadas,
        'filas_omitidas_duplicadas': filas_omitidas,
        'filas_rechazadas': filas_rechazadas,
        'conteo_base_antes': None,
        'conteo_base_despues': None,
        'cambio_neto_base': filas_cargadas,
        'es_idempotente': not config.get('append_only') or sync.get('status') == 'success',
        'persistencia_local': persistencia_local,
        'filas_persistidas_localmente': filas_insertadas + filas_actualizadas if persistencia_local else 0,
        'sincronizacion_supabase': sync,
        'resumen_ejecutivo': resumen,
        'trazabilidad_filas': trazabilidad
    }
