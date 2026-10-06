"""
Módulo del Núcleo: ABC / VALORIZACIÓN FINANCIERA (Capa 2 - FÓRMULA / Pareto 80-15-5)
Responsabilidad Única: Calcular Demanda Anualizada por Valor (D * Cu) y clasificar en A, B y C.
Contrato:
  - clasificar_abc(df_demanda) -> dict: {
        'df_abc': DataFrame,
        'valor_total_anual': float,
        'resumen_clases': dict
    }
"""

import pandas as pd
import numpy as np

def clasificar_abc(df_demanda):
    """
    Calcula: Valor Anual = Demanda Anual * Costo Unitario
    Ordena descendente, calcula acumulados y aplica regla 80-15-5.
    """
    df = df_demanda.copy()
    df['valor_consumo_anual'] = df['demanda_anual_d'] * df['costo_unitario']
    
    df = df.sort_values(by='valor_consumo_anual', ascending=False).reset_index(drop=True)
    valor_total = df['valor_consumo_anual'].sum()
    
    df['valor_acumulado'] = df['valor_consumo_anual'].cumsum()
    df['pct_valor_acumulado'] = (df['valor_acumulado'] / valor_total) * 100 if valor_total > 0 else 0
    df['pct_sku_acumulado'] = ((df.index + 1) / len(df)) * 100
    
    def asignar(pct):
        if pct <= 80.0:
            return 'A'
        elif pct <= 95.0:
            return 'B'
        else:
            return 'C'
            
    df['clasificacion_abc'] = df['pct_valor_acumulado'].apply(asignar)
    
    resumen = {
        'A': {
            'skus': int((df['clasificacion_abc'] == 'A').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'A').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum() / valor_total * 100) if valor_total > 0 else 0)
        },
        'B': {
            'skus': int((df['clasificacion_abc'] == 'B').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'B').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum() / valor_total * 100) if valor_total > 0 else 0)
        },
        'C': {
            'skus': int((df['clasificacion_abc'] == 'C').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'C').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum() / valor_total * 100) if valor_total > 0 else 0)
        }
    }
    
    return {
        'df_abc': df,
        'valor_total_anual': float(valor_total),
        'resumen_clases': resumen
    }
