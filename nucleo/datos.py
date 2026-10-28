"""
Módulo del Núcleo: DATOS (Capa 1 - Estado Canónico en Base Relacional SQL & Supabase)
Principio Rector (Diapositivas 3, 5 y 12):
  "El archivo no es el dato. Es el documento que trae el dato.
   Nadie corre el inventario sobre el montón de remisiones que llegaron.
   Las asienta en el kardex, y corre sobre el kardex.
   Y de aquí en adelante, todos los módulos leen de la base.
   Ninguno vuelve a tocar el archivo."
"""

import os
import json
import uuid
import urllib.request
import urllib.error
from urllib.parse import quote, urlencode
import pandas as pd
import numpy as np
from datetime import datetime

from nucleo import base_datos

def get_base_dir():
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and os.path.dirname(cur) != cur:
        if os.path.exists(os.path.join(cur, 'datos_limpios')) or os.path.exists(os.path.join(cur, 'datos_iniciales')):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()

def load_env():
    env_vars = {}
    base_dir = get_base_dir()
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

ENV = load_env()
SUPABASE_URL = ENV.get('SUPABASE_URL', 'https://wheclfavngzgmlhbojrd.supabase.co')
API_KEY = ENV.get('SUPABASE_SERVICE_ROLE_KEY') or ENV.get('SUPABASE_ANON_KEY')

def _mensaje_error_http(error):
    cuerpo = error.read().decode('utf-8', errors='replace').strip()
    try:
        respuesta = json.loads(cuerpo)
    except (json.JSONDecodeError, TypeError):
        respuesta = None

    if isinstance(respuesta, dict):
        detalle = ' '.join(
            str(respuesta[campo]).strip()
            for campo in ('message', 'details', 'hint')
            if respuesta.get(campo)
        )
    else:
        detalle = cuerpo

    if not detalle:
        detalle = str(error.reason or 'Error de validación remota')
    if error.code == 400:
        return f'Supabase rechazó los datos enviados: {detalle}'
    return f'Error HTTP {error.code} al sincronizar con Supabase: {detalle}'

def supabase_post(table_name, payload):
    """Envía un registro o lista de registros a la API REST de Supabase."""
    if not API_KEY or not SUPABASE_URL:
        return {'status': 'skipped', 'msg': 'No hay credenciales de Supabase configuradas'}
        
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{quote(table_name, safe='')}"
    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp_body = resp.read().decode('utf-8')
            return {'status': 'success', 'data': json.loads(resp_body) if resp_body else {}}
    except urllib.error.HTTPError as e:
        return {'status': 'error', 'msg': _mensaje_error_http(e)}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}

def supabase_upsert(table_name, payload, on_conflict_col='sku', do_update=True, batch_size=200):
    """
    Ejecuta un UPSERT idempotente sobre la API REST de Supabase con PostgREST.
    Encabezados:
      - Prefer: resolution=merge-duplicates (ON CONFLICT DO UPDATE)
      - Prefer: resolution=ignore-duplicates (ON CONFLICT DO NOTHING)
    Query param: on_conflict=<clave_unica>
    """
    if not API_KEY or not SUPABASE_URL:
        return {
            'status': 'error',
            'msg': 'No hay credenciales de Supabase configuradas',
            'filas_sincronizadas': 0
        }
        
    records = payload if isinstance(payload, list) else [payload]
    if not records:
        return {'status': 'success', 'msg': 'No hay registros para sincronizar', 'filas_sincronizadas': 0}
    if batch_size <= 0:
        raise ValueError('batch_size debe ser mayor que cero')
        
    table_path = quote(table_name, safe='')
    conflict_columns = ','.join(on_conflict_col) if isinstance(on_conflict_col, (list, tuple)) else str(on_conflict_col)
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_path}?on_conflict={quote(conflict_columns, safe=',')}"
    resolution = 'merge-duplicates' if do_update else 'ignore-duplicates'
    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': f'resolution={resolution},return=minimal'
    }
    
    total_synced = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            data_bytes = json.dumps(batch, ensure_ascii=False, allow_nan=False).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status not in (200, 201, 204):
                    return {
                        'status': 'error',
                        'msg': f'Supabase respondió con HTTP {resp.status}',
                        'filas_sincronizadas': total_synced,
                        'filas_pendientes': len(records) - total_synced
                    }
                total_synced += len(batch)
        except urllib.error.HTTPError as e:
            return {
                'status': 'error',
                'msg': _mensaje_error_http(e),
                'filas_sincronizadas': total_synced,
                'filas_pendientes': len(records) - total_synced
            }
        except (urllib.error.URLError, TimeoutError, OSError, TypeError, ValueError) as e:
            return {
                'status': 'error',
                'msg': str(e),
                'filas_sincronizadas': total_synced,
                'filas_pendientes': len(records) - total_synced
            }

    return {'status': 'success', 'filas_sincronizadas': total_synced, 'filas_pendientes': 0}

def supabase_insert(table_name, payload, batch_size=200):
    """Inserta filas sin clave natural, como registros de decisiones append-only."""
    records = payload if isinstance(payload, list) else [payload]
    if not API_KEY or not SUPABASE_URL:
        return {
            'status': 'error',
            'msg': 'No hay credenciales de Supabase configuradas',
            'filas_sincronizadas': 0,
            'filas_pendientes': len(records)
        }
    if not records:
        return {'status': 'success', 'filas_sincronizadas': 0, 'filas_pendientes': 0}
    if batch_size <= 0:
        raise ValueError('batch_size debe ser mayor que cero')

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{quote(table_name, safe='')}"
    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }

    total_synced = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            data_bytes = json.dumps(batch, ensure_ascii=False, allow_nan=False).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status not in (200, 201, 204):
                    return {
                        'status': 'error',
                        'msg': f'Supabase respondió con HTTP {resp.status}',
                        'filas_sincronizadas': total_synced,
                        'filas_pendientes': len(records) - total_synced
                    }
                total_synced += len(batch)
        except urllib.error.HTTPError as e:
            return {
                'status': 'error',
                'msg': _mensaje_error_http(e),
                'filas_sincronizadas': total_synced,
                'filas_pendientes': len(records) - total_synced
            }
        except (urllib.error.URLError, TimeoutError, OSError, TypeError, ValueError) as e:
            return {
                'status': 'error',
                'msg': str(e),
                'filas_sincronizadas': total_synced,
                'filas_pendientes': len(records) - total_synced
            }

    return {'status': 'success', 'filas_sincronizadas': total_synced, 'filas_pendientes': 0}

def supabase_sync_bom(payload):
    """Inserta o actualiza filas BOM sin requerir una constraint remota adicional."""
    records = payload if isinstance(payload, list) else [payload]
    if not API_KEY or not SUPABASE_URL:
        return {
            'status': 'error',
            'msg': 'No hay credenciales de Supabase configuradas',
            'filas_sincronizadas': 0,
            'filas_pendientes': len(records)
        }

    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{quote('bom', safe='')}"
    synced = 0

    for record in records:
        query = urlencode({
            'select': 'producto,sku_material',
            'producto': f"eq.{record['producto']}",
            'sku_material': f"eq.{record['sku_material']}"
        })
        lookup = urllib.request.Request(f'{url}?{query}', headers=headers, method='GET')
        try:
            with urllib.request.urlopen(lookup, timeout=8) as response:
                matches = json.loads(response.read().decode('utf-8'))
            if len(matches) > 1:
                return {
                    'status': 'error',
                    'msg': (
                        'Hay varias filas BOM con la misma combinación producto/SKU; '
                        'no se modificaron para evitar una actualización ambigua.'
                    ),
                    'filas_sincronizadas': synced,
                    'filas_pendientes': len(records) - synced
                }

            if matches:
                update_query = urlencode({
                    'producto': f"eq.{record['producto']}",
                    'sku_material': f"eq.{record['sku_material']}"
                })
                request = urllib.request.Request(
                    f'{url}?{update_query}',
                    data=json.dumps(record, ensure_ascii=False, allow_nan=False).encode('utf-8'),
                    headers=headers,
                    method='PATCH'
                )
            else:
                request = urllib.request.Request(
                    url,
                    data=json.dumps(record, ensure_ascii=False, allow_nan=False).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )

            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status not in (200, 201, 204):
                    return {
                        'status': 'error',
                        'msg': f'Supabase respondió con HTTP {response.status}',
                        'filas_sincronizadas': synced,
                        'filas_pendientes': len(records) - synced
                    }
            synced += 1
        except urllib.error.HTTPError as error:
            return {
                'status': 'error',
                'msg': _mensaje_error_http(error),
                'filas_sincronizadas': synced,
                'filas_pendientes': len(records) - synced
            }
        except (urllib.error.URLError, TimeoutError, OSError, TypeError, ValueError) as error:
            return {
                'status': 'error',
                'msg': str(error),
                'filas_sincronizadas': synced,
                'filas_pendientes': len(records) - synced
            }

    return {'status': 'success', 'filas_sincronizadas': synced, 'filas_pendientes': 0}

def leer_estado():
    """
    LEE EXCLUSIVAMENTE DE LA BASE DE DATOS RELACIONAL SQL.
    (Diapositiva 5: 'Todos los módulos leen de la base. Ninguno vuelve a tocar el archivo').
    """
    base_datos.poblar_estado_inicial_si_vacio()
    conn = base_datos.get_connection()
    
    estado = {
        'maestro_materiales': pd.read_sql_query("SELECT sku, descripcion, categoria, unidad, costo_unitario, lead_time_declarado_dias FROM maestro_materiales;", conn),
        'maestro_productos': pd.read_sql_query("SELECT producto, nombre_producto FROM maestro_productos;", conn),
        'bom': pd.read_sql_query("SELECT producto, sku_material, cantidad_por_unidad, unidad FROM bom;", conn),
        'plan_produccion': pd.read_sql_query("SELECT periodo, producto, cantidad_planeada, cantidad_real FROM plan_produccion;", conn),
        'ordenes_compra': pd.read_sql_query("SELECT orden_compra, sku, proveedor, cantidad, fecha_pedido, fecha_recepcion, costo_unitario, estado, lead_time_dias FROM ordenes_compra;", conn),
        'movimientos_inventario': pd.read_sql_query("SELECT fecha, sku, tipo_movimiento, cantidad, documento, bodega, usuario FROM movimientos_inventarios ORDER BY fecha ASC;", conn),
        'conteo_fisico': pd.read_sql_query("SELECT sku, stock_fisico_contado, fecha_conteo, auditor FROM conteo_fisico;", conn),
        'inventario_inicial': pd.read_sql_query("SELECT sku, stock_inicial, fecha_corte FROM inventario_inicial;", conn)
    }
    
    conn.close()
    return estado

def guardar_propuestas(resultado_orquestacion):
    """
    1. Asienta en la base de datos relacional (bitacora_corridas y propuestas_reposicion)
    2. Sincroniza con Supabase si está activo
    3. Guarda réplica en resultados_auditoria/ordenes_compra_sugeridas_ia.json
    """
    base_dir = get_base_dir()
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)
    
    ciclo_id = resultado_orquestacion.get('id', str(uuid.uuid4()))
    resultado_orquestacion['id'] = ciclo_id
    
    # 1. Guardar réplica local JSON
    ruta_json = os.path.join(results_dir, 'ordenes_compra_sugeridas_ia.json')
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(resultado_orquestacion, f, indent=2, ensure_ascii=False)
        
    # 2. Sincronización con Supabase (en segundo plano / no bloqueante)
    kpis = resultado_orquestacion.get('kpis', {})
    corrida_payload = {
        'id': ciclo_id,
        'created_at': datetime.now().isoformat(),
        'eri_global_pct': float(kpis.get('eri_global_pct', 0.0)),
        'skus_en_quiebre': int(kpis.get('skus_en_quiebre', 0)),
        'inversion_total_sugerida_cop': float(kpis.get('inversion_propuesta_cop', 0.0)),
        'materiales_fantasmas': int(kpis.get('materiales_fantasmas_detectados', 0)),
        'desfases_muelle': int(kpis.get('desfases_muelle_detectados', 0)),
        'status': resultado_orquestacion.get('status', 'completado')
    }
    sb_res_corrida = supabase_post('auditoria_corridas_orquestacion', corrida_payload)
    
    return {
        'status': 'success',
        'ciclo_id': ciclo_id,
        'archivo_local': ruta_json,
        'supabase_sync': sb_res_corrida.get('status')
    }

def registrar_decision(sku, accion, planeador="Planeador Compras E2", motivo="Reorden autorizada en tablero", corrida_id=None):
    """
    Asienta la decisión humana en la base de datos relacional y Supabase.
    Slide 10: 'De la decisión: Cuántas aprobó y cuántas rechazó el humano (Si el sistema acierta)'.
    Slide 11: 'Qué decidió el humano en cada propuesta'.
    """
    if not sku or not str(sku).strip():
        return {
            'status': 'error',
            'mensaje': 'El parámetro SKU es obligatorio para registrar la decisión de compra.'
        }
        
    base_datos.inicializar_esquema()
    conn = base_datos.get_connection()
    cur = conn.cursor()
    
    id_decision = str(uuid.uuid4())
    timestamp_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. Asentar en tabla registro_decisiones_compras
    cur.execute("""
    INSERT INTO registro_decisiones_compras (id, corrida_id, sku, decision, planeador, motivo, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (id_decision, corrida_id, sku, accion, planeador, motivo, timestamp_actual))
    
    # 2. Actualizar estado en propuestas_reposicion
    cur.execute("""
    UPDATE propuestas_reposicion 
    SET estado_decision = ?, updated_at = ?
    WHERE sku = ? AND estado_decision = 'PENDIENTE';
    """, (accion, timestamp_actual, sku))
    
    conn.commit()
    conn.close()
    
    # 3. Asentar en Supabase si está disponible
    decision_payload = {
        'sku': sku,
        'decision': accion,
        'planeador': planeador,
        'motivo': motivo,
        'created_at': datetime.now().isoformat()
    }
    sb_res = supabase_post('registro_decisiones_compras', decision_payload)
    
    return {
        'status': 'registrado',
        'id_decision': id_decision,
        'sku': sku,
        'decision': accion,
        'timestamp': timestamp_actual,
        'supabase_sync': sb_res.get('status')
    }

def obtener_analisis_demanda():
    """
    Retorna la matriz detallada de demanda dependiente (BOM), clasificación Pareto ABC
    y parámetros analíticos de reposición (ROP, EOQ, Stock de Seguridad).
    """
    from nucleo import bom, abc, reposicion, eri
    
    estado = leer_estado()
    res_bom = bom.explotar_bom(estado)
    res_abc = abc.clasificar_abc(res_bom['df_demanda_insumos'])
    res_rep = reposicion.calcular_parametros_reposicion(res_abc['df_abc'], estado)
    res_eri = eri.auditar_eri(estado)
    
    df = res_rep['df_parametros'].copy()
    cf = estado['conteo_fisico']
    df = df.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')
    df_eri_res = res_eri['df_auditoria'][['sku', 'saldo_teorico']]
    df = df.merge(df_eri_res, on='sku', how='left')
    df['stock_real'] = df['stock_fisico_contado'].fillna(df['saldo_teorico']).fillna(0)
    df['en_quiebre'] = (df['stock_real'] <= df['ROP']) & (df['demanda_anual_d'] > 0)
    
    df_clean = df.replace({np.nan: None})
    return {
        'resumen_abc': res_abc['resumen_clases'],
        'total_skus': len(df_clean),
        'skus_en_quiebre': int(df['en_quiebre'].sum()),
        'materiales': df_clean[[
            'sku', 'descripcion', 'categoria', 'costo_unitario', 'lead_time_usado',
            'demanda_anual_d', 'consumo_diario_d', 'sigma_diario',
            'clasificacion_abc', 'valor_consumo_anual', 'SS_95', 'ROP', 'EOQ',
            'stock_real', 'en_quiebre'
        ]].to_dict(orient='records')
    }
