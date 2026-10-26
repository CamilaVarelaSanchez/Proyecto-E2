"""
Módulo del Núcleo: REPOSICIÓN Y DIMENSIONAMIENTO DINÁMICO (Capa 2 - Parámetros ROP, EOQ, SS)
Responsabilidad Única: Dimensionar Stock de Seguridad (SS), Punto de Reorden (ROP) y Lote Económico (EOQ)
                       con base en modelos estocásticos de ingeniería industrial.
Contrato:
  - calcular_parametros_reposicion(df_abc, estado, z=1.645, co=80000.0, i_tasa=0.25) -> dict: {
        'df_parametros': DataFrame,
        'total_evaluados': int
    }
"""

import pandas as pd
import numpy as np

def calcular_parametros_reposicion(df_abc, estado, z=1.645, co=80000.0, i_tasa=0.25, usar_variabilidad_combinada=True):
    """
    Calcula los parámetros analíticos de reposición bajo modelos formales de ingeniería industrial:
      1. Lead Time real auditado de proveedores por categoría (ej. 20.8 días en lámina).
      2. Stock de Seguridad (SS) probabilístico que absorbe la variabilidad combinada
         de la demanda y del tiempo de entrega:
         sigma_combinada = sqrt( LT_prom * sigma_d^2 + d_prom^2 * sigma_LT^2 )
         SS = Z * sigma_combinada  (con Z = 1.645 para 95% de nivel de servicio).
      3. Punto de Reorden (ROP): ROP = d_prom * LT_prom + SS
      4. Lote Económico de Compra (EOQ): EOQ = sqrt( (2 * D * S) / H )
         donde S = $80.000 COP y H = 0.25 * Cu (25% anual del costo unitario).
    """
    if df_abc is None or len(df_abc) == 0:
        return {
            'df_parametros': pd.DataFrame(),
            'total_evaluados': 0
        }

    df = df_abc.copy()
    oc = estado.get('ordenes_compra') if estado else None
    mm = estado.get('maestro_materiales') if estado else None
    
    # 1. Lead Time Real promedio y desviación estándar por categoría (Auditoría de Proveedores)
    if oc is not None and len(oc) > 0:
        oc_temp = oc.copy()
        oc_temp['lt_real'] = (pd.to_datetime(oc_temp['fecha_recepcion']) - pd.to_datetime(oc_temp['fecha_pedido'])).dt.days
        oc_validas = oc_temp[oc_temp['lt_real'] > 0]
        if len(oc_validas) > 0 and mm is not None:
            oc_cat = oc_validas.merge(mm[['sku', 'categoria']], on='sku', how='left')
            lt_prom = oc_cat.groupby('categoria')['lt_real'].mean().to_dict()
            lt_std = oc_cat.groupby('categoria')['lt_real'].std().fillna(0.0).to_dict()
            df['lead_time_usado'] = df['categoria'].map(lt_prom).fillna(df['lead_time_declarado_dias'])
            df['sigma_lt'] = df['categoria'].map(lt_std).fillna(0.0)
        else:
            df['lead_time_usado'] = df['lead_time_declarado_dias']
            df['sigma_lt'] = 0.0
    else:
        df['lead_time_usado'] = df['lead_time_declarado_dias']
        df['sigma_lt'] = 0.0
        
    # Costo anual de posesión de inventario H = 0.25 * Cu
    df['C_c'] = df['costo_unitario'] * i_tasa
    
    # 2. Stock de Seguridad (SS) Probabilístico
    if usar_variabilidad_combinada:
        # Variabilidad combinada de demanda (sigma_d) y tiempo de entrega (sigma_LT)
        var_combinada = (df['lead_time_usado'] * (df['sigma_diario'] ** 2)) + ((df['consumo_diario_d'] ** 2) * (df['sigma_lt'] ** 2))
        df['sigma_combinada'] = np.sqrt(np.maximum(0.0, var_combinada))
        df['SS_95'] = np.round(z * df['sigma_combinada'])
    else:
        df['SS_95'] = np.round(z * df['sigma_diario'] * np.sqrt(df['lead_time_usado']))
        
    # 3. Punto de Reorden (ROP): Demanda durante Lead Time + Colchón de Seguridad
    df['ROP'] = np.round((df['consumo_diario_d'] * df['lead_time_usado']) + df['SS_95'])
    
    # 4. Lote Económico de Compra (EOQ) con S = $80.000 COP y H = 25% anual
    demanda_pos = np.maximum(0.0, df['demanda_anual_d'])
    df['EOQ'] = np.where((df['C_c'] > 0) & (demanda_pos > 0), np.round(np.sqrt((2 * demanda_pos * co) / df['C_c'])), 0)
    
    return {
        'df_parametros': df,
        'total_evaluados': len(df)
    }
