"""
Módulo del Núcleo: BOM / EXPLOSIÓN DE DEMANDA (Capa 2 - FÓRMULA / Queja 4)
Responsabilidad Única: Explotar el Plan Maestro de Producción sobre la Matriz BOM y calcular consumo diario y variabilidad.
Contrato:
  - explotar_bom(estado) -> dict: {
        'df_demanda_insumos': DataFrame,
        'total_insumos_activos': int
    }
"""

import pandas as pd
import numpy as np

def explotar_bom(estado):
    """
    Multiplica cantidades planeadas por coeficientes de ensamble:
    D_i = sum(Plan_j * BOM_ji)
    Anualizado a 12 meses (factor 12.0 / 21.0).
    Calcula consumo diario y variabilidad diaria (sigma_diario).
    """
    plan = estado['plan_produccion']
    bom = estado['bom']
    mm = estado['maestro_materiales']
    
    plan_bom = plan.merge(bom, on='producto', how='inner')
    plan_bom['consumo_planeado'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']
    
    # Consumo total de insumos
    consumo_dep = plan_bom.groupby('sku_material')['consumo_planeado'].sum().reset_index().rename(columns={'sku_material': 'sku'})
    
    # Variabilidad mensual y diaria
    demanda_mensual = plan_bom.groupby(['sku_material', 'periodo'])['consumo_planeado'].sum().unstack(fill_value=0)
    sigma_mensual = demanda_mensual.std(axis=1)
    sigma_diario = (sigma_mensual / np.sqrt(30)).rename('sigma_diario')
    
    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario', 'lead_time_declarado_dias']].copy()
    df = df.merge(consumo_dep, on='sku', how='left').fillna({'consumo_planeado': 0})
    df = df.merge(sigma_diario, left_on='sku', right_index=True, how='left').fillna({'sigma_diario': 0})
    
    df['demanda_anual_d'] = df['consumo_planeado'] * (12.0 / 21.0)
    df['consumo_diario_d'] = df['demanda_anual_d'] / 365.0
    
    activos = len(df[df['demanda_anual_d'] > 0])
    
    return {
        'df_demanda_insumos': df,
        'total_insumos_activos': activos
    }
