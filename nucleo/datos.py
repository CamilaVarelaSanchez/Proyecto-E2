"""
Módulo del Núcleo: DATOS (Capa 1 - Estado Canónico & Integración Supabase)
Responsabilidad Única: Leer y escribir el estado en Supabase PostgreSQL y sincronizar réplica local.
Contrato:
  - leer_estado() -> dict con DataFrames canónicos
  - guardar_propuestas(resultado_orquestacion) -> dict con confirmación de persistencia en Supabase y local
  - registrar_decision(sku, decision, planeador, motivo) -> dict con registro transaccional en Supabase
"""

import os
import json
import uuid
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from datetime import datetime

def get_base_dir():
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and os.path.dirname(cur) != cur:
        if os.path.exists(os.path.join(cur, 'datos_limpios')):
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

def supabase_post(table_name, payload):
    """Envía un registro o lista de registros a la API REST de Supabase."""
    if not API_KEY or not SUPABASE_URL:
        return {'status': 'skipped', 'msg': 'No hay credenciales de Supabase configuradas'}
        
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}"
    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode('utf-8')
            return {'status': 'success', 'data': json.loads(resp_body) if resp_body else {}}
    except Exception as e:
        print(f"[Aviso Supabase Sync] No se pudo sincronizar tabla {table_name}: {e}")
        return {'status': 'error', 'msg': str(e)}

def supabase_patch(table_name, query_params, payload):
    """Actualiza registros en Supabase."""
    if not API_KEY or not SUPABASE_URL:
        return {'status': 'skipped'}
        
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}?{query_params}"
    headers = {
        'apikey': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}

def leer_estado():
    """
    Lee las tablas canónicas saneadas (datos limpios).
    """
    base_dir = get_base_dir()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    
    tablas = {
        'maestro_materiales': 'maestro_materiales_clean.csv',
        'maestro_productos': 'maestro_productos_clean.csv',
        'bom': 'bom_clean.csv',
        'plan_produccion': 'plan_produccion_clean.csv',
        'ordenes_compra': 'ordenes_compra_clean.csv',
        'movimientos_inventario': 'movimientos_inventario_clean.csv',
        'conteo_fisico': 'conteo_fisico_clean.csv',
        'inventario_inicial': 'inventario_inicial_clean.csv'
    }
    
    estado = {}
    for nombre, arch in tablas.items():
        ruta = os.path.join(data_dir, arch)
        if os.path.exists(ruta):
            estado[nombre] = pd.read_csv(ruta)
        else:
            raise FileNotFoundError(f"Tabla canónica no encontrada en: {ruta}")
            
    return estado

def guardar_propuestas(resultado_orquestacion):
    """
    1. Guarda localmente en resultados_auditoria/ordenes_compra_sugeridas_ia.json
    2. Inserta el log transaccional en Supabase (auditoria_corridas_orquestacion)
    3. Inserta las propuestas en Supabase (propuestas_reposicion)
    """
    base_dir = get_base_dir()
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)
    
    # 1. Guardar réplica local
    ruta_json = os.path.join(results_dir, 'ordenes_compra_sugeridas_ia.json')
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(resultado_orquestacion, f, indent=2, ensure_ascii=False)
        
    # 2. Persistir en Supabase
    ciclo_id = str(uuid.uuid4())
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
    
    # 3. Guardar propuestas en Supabase
    propuestas_sb = []
    for p in resultado_orquestacion.get('propuestas_compra', []):
        propuestas_sb.append({
            'ciclo_orquestacion_id': ciclo_id,
            'sku': p['sku'],
            'descripcion': p['descripcion'],
            'categoria': p.get('categoria', 'General'),
            'clase_abc': p.get('clase_abc', 'C'),
            'stock_real': int(p.get('stock_real', 0)),
            'punto_reorden_rop': int(p.get('punto_reorden_rop', 0)),
            'stock_seguridad_ss': int(p.get('stock_seguridad_ss', 0)),
            'cantidad_sugerida_eoq': int(p.get('cantidad_sugerida_eoq', 0)),
            'costo_unitario_cop': float(p.get('costo_unitario_cop', 0.0)),
            'inversion_estimada_cop': float(p.get('inversion_estimada_cop', 0.0)),
            'justificacion_ejecutiva': p.get('justificacion_ejecutiva', ''),
            'estado_decision': 'PENDIENTE'
        })
        
    if propuestas_sb:
        supabase_post('propuestas_reposicion', propuestas_sb)
        
    return {
        'status': 'success',
        'ciclo_id': ciclo_id,
        'archivo_local': ruta_json,
        'supabase_sync': sb_res_corrida.get('status')
    }

def registrar_decision(sku, accion, planeador="Planeador Compras E2", motivo="Reorden autorizada en tablero"):
    """
    1. Asienta la decisión humana en Supabase (registro_decisiones_compras)
    2. Actualiza el estado de la propuesta en Supabase (propuestas_reposicion)
    3. Guarda réplica en CSV local para auditoría fuera de línea.
    """
    base_dir = get_base_dir()
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp_actual = datetime.now().isoformat()
    
    # 1. Asentar en Supabase
    decision_payload = {
        'sku': sku,
        'decision': accion,
        'planeador': planeador,
        'motivo': motivo,
        'created_at': timestamp_actual
    }
    
    sb_res = supabase_post('registro_decisiones_compras', decision_payload)
    
    # Actualizar estado en propuestas_reposicion
    supabase_patch('propuestas_reposicion', f'sku=eq.{sku}&estado_decision=eq.PENDIENTE', {'estado_decision': accion})
    
    # 2. Guardar réplica local
    ruta_decisiones = os.path.join(results_dir, 'registro_decisiones_compras.csv')
    nuevo_registro = pd.DataFrame([{
        'timestamp': timestamp_actual,
        'sku': sku,
        'decision': accion,
        'planeador': planeador,
        'motivo': motivo
    }])
    
    if os.path.exists(ruta_decisiones):
        nuevo_registro.to_csv(ruta_decisiones, mode='a', header=False, index=False)
    else:
        nuevo_registro.to_csv(ruta_decisiones, mode='w', header=True, index=False)
        
    return {
        'status': 'registrado',
        'sku': sku,
        'decision': accion,
        'supabase_sync': sb_res.get('status')
    }
