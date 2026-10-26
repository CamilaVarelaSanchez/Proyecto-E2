"""
Módulo del Núcleo: AGENTE DE ABASTECIMIENTO / RECOMENDACIONES INTELIGENTES DE PEDIDOS
Responsabilidad Única: Generar recomendaciones ejecutivas de compras basadas en los modelos
                       cuantitativos (ROP, EOQ, SS, ABC, ERI), detallando material, cantidad exacta,
                       momento de emisión y justificación en dinero del riesgo evitado.

Reglas directrices:
  - Muestra únicamente resultados ejecutivos y decisiones sugeridas.
  - Sin fórmulas sin procesar, sin scripts de depuración ni jerga técnica interna.
  - No menciona expresiones informales como 'Queja 3' ni 'Queja 4'.
"""

from datetime import datetime, timedelta

def calcular_prioridad(clase_abc, stock_real, ss, rop):
    """Determina la prioridad ejecutiva de reorden según criticidad y nivel de cobertura."""
    if stock_real <= ss or clase_abc == 'A':
        return 'Alta'
    elif stock_real <= rop or clase_abc == 'B':
        return 'Media'
    return 'Programada'

def generar_propuestas(df_quiebres):
    """
    Recibe los insumos cuyo stock real perforó o tocó el Punto de Reorden (Stock Real <= ROP)
    y genera la recomendación ejecutiva para el Planeador de Abastecimiento.
    """
    propuestas = []
    fecha_actual = datetime.now()
    
    # Costo por hora de parada de ensamble en planta E2 SAS
    COSTO_HORA_PARADA_PLANTA = 450000.0
    HORAS_TURNO_OPERATIVO = 8.0
    COSTO_TURNO_PARADA = COSTO_HORA_PARADA_PLANTA * HORAS_TURNO_OPERATIVO  # $3.600.000 COP/turno
    
    for _, row in df_quiebres.iterrows():
        sku = str(row['sku'])
        desc = str(row.get('descripcion', 'Materia Prima'))
        cat = str(row.get('categoria', 'Insumos Generales'))
        unidad = str(row.get('unidad', 'unidad'))
        clase = str(row.get('clasificacion_abc', 'C'))
        
        stock_real = float(row.get('stock_real', 0.0))
        rop = float(row.get('ROP', 0.0))
        ss = float(row.get('SS_95', 0.0))
        eoq = float(row.get('EOQ', 0.0))
        cu = float(row.get('costo_unitario', 0.0))
        demanda_anual = float(row.get('demanda_anual_d', 0.0))
        consumo_diario = float(row.get('consumo_diario_d', 0.0))
        lead_time = int(row.get('lead_time_usado', row.get('lead_time_declarado_dias', 15)))
        
        # Inversión calculada para la orden
        inversion = round(eoq * cu, 2)
        
        # Cobertura remanente en días
        dias_cobertura = max(0, int(stock_real / consumo_diario)) if consumo_diario > 0 else 0
        
        # Prioridad ejecutiva
        prioridad = calcular_prioridad(clase, stock_real, ss, rop)
        
        # Cronograma de orden
        fecha_emision = fecha_actual.strftime('%Y-%m-%d')
        fecha_recepcion_esperada = (fecha_actual + timedelta(days=lead_time)).strftime('%Y-%m-%d')
        
        # Cuantificación monetaria del riesgo evitado
        # Si el material es Clase A o stock <= SS, el riesgo es al menos 2 turnos de parada operativa
        factor_riesgo_turnos = 3 if (stock_real <= ss or clase == 'A') else (2 if clase == 'B' else 1)
        riesgo_evitado_cop = round(factor_riesgo_turnos * COSTO_TURNO_PARADA, 2)
        
        # Justificación ejecutiva en dinero del riesgo evitado
        justificacion = (
            f"Se recomienda emitir de inmediato una orden de compra por {eoq:,.0f} {unidad}s de {desc} ({sku}), "
            f"con una inversión proyectada de ${inversion:,.0f} COP. "
            f"El inventario físico disponible ({stock_real:,.0f} {unidad}s) tocó el Punto de Reorden ({rop:,.0f} {unidad}s), "
            f"dejando una cobertura crítica de apenas {dias_cobertura} días de consumo en planta. "
            f"Esta adquisición mitiga un riesgo financiero estimado en ${riesgo_evitado_cop:,.0f} COP por concepto de interrupción "
            f"de las líneas de ensamble de archivadores y estanterías ($450.000 COP/hora), "
            f"asegurando la recepción estimada para el {fecha_recepcion_esperada} bajo un tiempo de entrega de {lead_time} días."
        )
        
        propuestas.append({
            'sku': sku,
            'descripcion': desc,
            'categoria': cat,
            'unidad': unidad,
            'clase_abc': clase,
            'stock_real': round(stock_real, 1),
            'punto_reorden_rop': round(rop, 1),
            'stock_seguridad_ss': round(ss, 1),
            'cantidad_sugerida_eoq': round(eoq, 0),
            'costo_unitario_cop': cu,
            'inversion_estimada_cop': inversion,
            'riesgo_evitado_cop': riesgo_evitado_cop,
            'lead_time_dias': lead_time,
            'dias_cobertura_remanente': dias_cobertura,
            'momento_emision': f"Inmediato (Stock {stock_real:,.0f} ≤ ROP {rop:,.0f})",
            'fecha_sugerida_emision': fecha_emision,
            'fecha_recepcion_estimada': fecha_recepcion_esperada,
            'prioridad': prioridad,
            'accion_sugerida': f"Emitir Orden de Compra por {eoq:,.0f} {unidad}s (${inversion:,.0f} COP)",
            'justificacion_ejecutiva': justificacion,
            'estado_decision': 'PENDIENTE'
        })
        
    return propuestas
