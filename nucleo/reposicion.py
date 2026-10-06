"""
Módulo del Núcleo: REPOSICIÓN (Capa 2 - FÓRMULA / Queja 4)
Responsabilidad Única: Dimensionar Stock de Seguridad (SS), Punto de Reorden (ROP) y Lote Económico (EOQ).
Contrato:
  - calcular_parametros_reposicion(df_abc, estado, z=1.645, co=150000.0, i_tasa=0.22) -> dict: {
        'df_parametros': DataFrame,
        'total_evaluados': int
    }
"""

import pandas as pd
import numpy as np

def calcular_parametros_reposicion(df_abc, estado, z=1.645, co=150000.0, i_tasa=0.22):
    """
    Calcula:
      SS = Z * sigma_d * sqrt(LeadTime)
      ROP = (d * LeadTime) + SS
      EOQ = sqrt((2 * D * Co) / (i * Cu))
    """
    df = df_abc.copy()
    oc = estado.get('ordenes_compra')
    mm = estado.get('maestro_materiales')
    
    # Lead Time Real promedio por categoría
    if oc is not None and len(oc) > 0:
        oc_temp = oc.copy()
        oc_temp['lt_real'] = (pd.to_datetime(oc_temp['fecha_recepcion']) - pd.to_datetime(oc_temp['fecha_pedido'])).dt.days
        oc_cat = oc_temp.merge(mm[['sku', 'categoria']], on='sku', how='left')
        lt_prom = oc_cat.groupby('categoria')['lt_real'].mean().to_dict()
        df['lead_time_usado'] = df['categoria'].map(lt_prom).fillna(df['lead_time_declarado_dias'])
    else:
        df['lead_time_usado'] = df['lead_time_declarado_dias']
        
    df['C_c'] = df['costo_unitario'] * i_tasa
    df['SS_95'] = np.round(z * df['sigma_diario'] * np.sqrt(df['lead_time_usado']))
    df['ROP'] = np.round((df['consumo_diario_d'] * df['lead_time_usado']) + df['SS_95'])
    df['EOQ'] = np.where(df['C_c'] > 0, np.round(np.sqrt((2 * df['demanda_anual_d'] * co) / df['C_c'])), 0)
    
    return {
        'df_parametros': df,
        'total_evaluados': len(df)
    }
