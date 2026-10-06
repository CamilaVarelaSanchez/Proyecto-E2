"""
Módulo del Núcleo: EXPLICADOR / GENERADOR DE PROPUESTAS (Capa 3 - IA / Orquestación)
Responsabilidad Única: Redactar la justificación ejecutiva en lenguaje natural para el planeador de compras.
Contrato:
  - generar_propuestas(df_quiebres) -> list de dicts con formato estructurado para el tablero y registro.
Defensa contra alucinación:
  - El texto se construye sobre variables estrictamente calculadas por el núcleo determinístico.
"""

def generar_propuestas(df_quiebres):
    """
    Recibe los insumos en quiebre (Stock Real <= ROP) y construye la propuesta formal
    con su justificación técnica en lenguaje natural.
    """
    propuestas = []
    
    for _, row in df_quiebres.iterrows():
        sku = str(row['sku'])
        desc = str(row.get('descripcion', 'Material'))
        cat = str(row.get('categoria', 'General'))
        clase = str(row.get('clasificacion_abc', 'C'))
        stock_real = int(row.get('stock_real', 0))
        rop = int(row.get('ROP', 0))
        ss = int(row.get('SS_95', 0))
        eoq = int(row.get('EOQ', 0))
        cu = float(row.get('costo_unitario', 0.0))
        demanda_anual = int(row.get('demanda_anual_d', 0))
        inversion = eoq * cu
        
        # Redacción ejecutiva contextualizada
        justificacion = (
            f"Se recomienda emitir Orden de Compra por {eoq:,} unidades del SKU {sku} ({desc}), "
            f"debido a que el stock disponible en bodega ({stock_real:,} unids) perforó el Punto de Reorden ROP "
            f"({rop:,} unids). Insumo clasificado en Pareto como Clase {clase}, con un consumo anual proyectado "
            f"de {demanda_anual:,} unidades y un Stock de Seguridad de amortiguación de {ss:,} unidades."
        )
        
        propuestas.append({
            'sku': sku,
            'descripcion': desc,
            'categoria': cat,
            'clase_abc': clase,
            'stock_real': stock_real,
            'punto_reorden_rop': rop,
            'stock_seguridad_ss': ss,
            'cantidad_sugerida_eoq': eoq,
            'costo_unitario_cop': cu,
            'inversion_estimada_cop': inversion,
            'justificacion_ejecutiva': justificacion,
            'decision_sugerida': 'Reorden Inmediata'
        })
        
    return propuestas
