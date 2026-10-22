"""
Módulo del Núcleo: INSTRUMENTACIÓN Y TELEMETRÍA (El sistema se mide solo)
Cumple rigurosamente las diapositivas 9, 10, 11 y 12 de Producción 4.0 (UdeM).

Instrumentos medidos:
  1. De la carga   -> Filas leídas, cargadas y rechazadas (Calidad del dato que entra)
  2. De la corrida -> Cuántas propuestas generó (Trabajo que ahorró)
  3. De las paradas-> Cuántas veces se detuvo y por qué (Calibración del criterio)
  4. De la decisión-> Cuántas aprobó y cuántas rechazó el humano (Acierto del sistema)
  5. Del costo     -> Cuánto tardó la corrida en ms (Costo de operación)
"""

import time
from datetime import datetime
import pandas as pd
from nucleo import base_datos

def registrar_inicio_corrida():
    """Inicia el cronómetro de la corrida."""
    return time.perf_counter()

def registrar_fin_corrida(t_inicio, resultado_orquestacion):
    """
    Asienta en la tabla `bitacora_corridas` la telemetría completa de la corrida.
    Slide 11: 'Una tabla más en la base: la bitácora de corridas.'
    """
    t_fin = time.perf_counter()
    duracion_ms = round((t_fin - t_inicio) * 1000, 2)
    
    conn = base_datos.get_connection()
    cur = conn.cursor()
    
    corrida_id = resultado_orquestacion.get('id', str(datetime.now().timestamp()))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    kpis = resultado_orquestacion.get('kpis', {})
    
    cur.execute("""
    INSERT INTO bitacora_corridas (
        id, timestamp, duracion_ms, total_skus, eri_global_pct,
        skus_en_quiebre, inversion_total_cop, materiales_fantasmas,
        desfases_muelle, criterio_parada_activado, motivo_parada, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        corrida_id,
        timestamp,
        duracion_ms,
        int(kpis.get('total_skus', 0)),
        float(kpis.get('eri_global_pct', 0.0)),
        int(kpis.get('skus_en_quiebre', 0)),
        float(kpis.get('inversion_propuesta_cop', 0.0)),
        int(kpis.get('materiales_fantasmas_detectados', 0)),
        int(kpis.get('desfases_muelle_detectados', 0)),
        1 if resultado_orquestacion.get('criterio_parada_activado') else 0,
        resultado_orquestacion.get('mensaje_parada', ''),
        resultado_orquestacion.get('status', 'completado')
    ))
    
    # Asentar propuestas en base de datos
    for p in resultado_orquestacion.get('propuestas_compra', []):
        propuesta_id = f"{corrida_id}_{p['sku']}"
        cur.execute("""
        INSERT OR REPLACE INTO propuestas_reposicion (
            id, corrida_id, sku, descripcion, categoria, clase_abc,
            stock_real, punto_reorden_rop, stock_seguridad_ss, cantidad_sugerida_eoq,
            costo_unitario_cop, inversion_estimada_cop, justificacion_ejecutiva, estado_decision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE');
        """, (
            propuesta_id, corrida_id, p['sku'], p.get('descripcion', ''),
            p.get('categoria', 'General'), p.get('clase_abc', 'C'),
            float(p.get('stock_real', 0)), float(p.get('punto_reorden_rop', 0)),
            float(p.get('stock_seguridad_ss', 0)), float(p.get('cantidad_sugerida_eoq', 0)),
            float(p.get('costo_unitario_cop', 0.0)), float(p.get('inversion_estimada_cop', 0.0)),
            p.get('justificacion_ejecutiva', '')
        ))
        
    conn.commit()
    conn.close()
    
    resultado_orquestacion['telemetria'] = {
        'duracion_ms': duracion_ms,
        'timestamp': timestamp,
        'corrida_id': corrida_id
    }
    return resultado_orquestacion

def obtener_metricas_instrumentacion():
    """
    Calcula los 5 instrumentos de autorregulación del sistema a partir de las tablas de base de datos.
    Slide 10: 'Qué debe medir de sí mismo'.
    """
    base_datos.inicializar_esquema()
    conn = base_datos.get_connection()
    cur = conn.cursor()
    
    # 1. DE LA CARGA: Filas leídas, cargadas y rechazadas (Calidad del dato)
    cur.execute("""
    SELECT 
        COALESCE(SUM(filas_leidas), 0) as total_leidas,
        COALESCE(SUM(filas_cargadas), 0) as total_cargadas,
        COALESCE(SUM(filas_rechazadas), 0) as total_rechazadas,
        COALESCE(SUM(filas_omitidas_duplicadas), 0) as total_duplicadas_evitadas,
        COUNT(*) as total_cargas
    FROM bitacora_cargas;
    """)
    row_carga = cur.fetchone()
    total_leidas = row_carga['total_leidas']
    total_cargadas = row_carga['total_cargadas']
    total_rechazadas = row_carga['total_rechazadas']
    total_dups = row_carga['total_duplicadas_evitadas']
    tasa_rechazo_pct = round((total_rechazadas / total_leidas * 100), 2) if total_leidas > 0 else 0.0

    # 2. DE LA CORRIDA: Cuántas propuestas generó (Trabajo que ahorró)
    # 3. DE LAS PARADAS: Cuántas veces se detuvo y por qué (Calibración del criterio)
    # 5. DEL COSTO: Cuánto tardó la corrida (Costo de operación)
    cur.execute("""
    SELECT 
        COUNT(*) as total_corridas,
        COALESCE(SUM(skus_en_quiebre), 0) as total_propuestas_generadas,
        COALESCE(SUM(criterio_parada_activado), 0) as total_paradas,
        COALESCE(AVG(duracion_ms), 0) as duracion_promedio_ms,
        COALESCE(MIN(duracion_ms), 0) as duracion_min_ms,
        COALESCE(MAX(duracion_ms), 0) as duracion_max_ms
    FROM bitacora_corridas;
    """)
    row_corrida = cur.fetchone()
    total_corridas = row_corrida['total_corridas']
    total_propuestas = row_corrida['total_propuestas_generadas']
    total_paradas = row_corrida['total_paradas']
    duracion_prom = round(row_corrida['duracion_promedio_ms'], 2)
    tasa_paradas_pct = round((total_paradas / total_corridas * 100), 2) if total_corridas > 0 else 0.0

    # 4. DE LA DECISIÓN: Cuántas aprobó y cuántas rechazó el humano (Acierto del sistema)
    cur.execute("""
    SELECT 
        COUNT(*) as total_decisiones,
        SUM(CASE WHEN UPPER(decision) = 'APROBADA' THEN 1 ELSE 0 END) as aprobadas,
        SUM(CASE WHEN UPPER(decision) = 'RECHAZADA' THEN 1 ELSE 0 END) as rechazadas
    FROM registro_decisiones_compras;
    """)
    row_dec = cur.fetchone()
    total_decisiones = row_dec['total_decisiones']
    aprobadas = row_dec['aprobadas'] or 0
    rechazadas = row_dec['rechazadas'] or 0
    tasa_acierto_humano_pct = round((aprobadas / total_decisiones * 100), 2) if total_decisiones > 0 else 0.0

    # Historial de las últimas 10 corridas para la bitácora
    cur.execute("""
    SELECT id, timestamp, duracion_ms, total_skus, eri_global_pct, skus_en_quiebre,
           inversion_total_cop, criterio_parada_activado, motivo_parada
    FROM bitacora_corridas
    ORDER BY timestamp DESC
    LIMIT 10;
    """)
    ultimas_corridas = [dict(r) for r in cur.fetchall()]

    # Historial de las últimas 10 cargas
    cur.execute("""
    SELECT id, timestamp, nombre_archivo, tipo_documento, filas_leidas, filas_cargadas,
           filas_rechazadas, filas_omitidas_duplicadas, detalle_rechazos
    FROM bitacora_cargas
    ORDER BY timestamp DESC
    LIMIT 10;
    """)
    ultimas_cargas = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        'instrumento_1_carga': {
            'total_leidas': total_leidas,
            'total_cargadas': total_cargadas,
            'total_rechazadas': total_rechazadas,
            'total_duplicadas_evitadas': total_dups,
            'tasa_rechazo_pct': tasa_rechazo_pct,
            'calidad_ingesta': 'Excelente' if tasa_rechazo_pct < 2.0 else 'Atención requerida'
        },
        'instrumento_2_corrida': {
            'total_corridas': total_corridas,
            'total_propuestas_generadas': total_propuestas,
            'propuestas_por_corrida_prom': round(total_propuestas / total_corridas, 1) if total_corridas > 0 else 0,
            'trabajo_ahorrado_horas_est': round(total_propuestas * 0.25, 1) # ~15 min por orden manual
        },
        'instrumento_3_paradas': {
            'total_paradas': total_paradas,
            'tasa_paradas_pct': tasa_paradas_pct,
            'diagnostico_calibracion': 'Bien calibrado (Detiene ante riesgo)' if total_paradas > 0 else 'Sin quiebres'
        },
        'instrumento_4_decision': {
            'total_decisiones': total_decisiones,
            'aprobadas': aprobadas,
            'rechazadas': rechazadas,
            'tasa_acierto_pct': tasa_acierto_humano_pct,
            'diagnostico_acierto': 'Alta confianza humana' if tasa_acierto_humano_pct >= 70 else ('En calibración' if total_decisiones > 0 else 'Sin decisiones registradas aún')
        },
        'instrumento_5_costo': {
            'duracion_promedio_ms': duracion_prom,
            'costo_operativo': f'{duracion_prom} ms por corrida (Costo computacional mínimo)'
        },
        'bitacora_corridas': ultimas_corridas,
        'bitacora_cargas': ultimas_cargas
    }
