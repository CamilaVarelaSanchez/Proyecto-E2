"""
Script de Automatización: Dimensionamiento Dinámico de Reposición (BOM, SS, ROP, EOQ)
Proyecto: E2 SAS - Solución a la Queja 4 de Gerencia
"""

import os
import sys
import pandas as pd
import numpy as np
import json

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_project_root():
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and os.path.dirname(cur) != cur:
        if os.path.exists(os.path.join(cur, 'datos_limpios')):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()

def ejecutar_dimensionamiento_reposicion():
    base_dir = get_project_root()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)

    # Cargar datasets
    mm = pd.read_csv(os.path.join(data_dir, 'maestro_materiales_clean.csv'))
    bom = pd.read_csv(os.path.join(data_dir, 'bom_clean.csv'))
    plan = pd.read_csv(os.path.join(data_dir, 'plan_produccion_clean.csv'))
    oc = pd.read_csv(os.path.join(data_dir, 'ordenes_compra_clean.csv'))

    # 1. Explosión Plan x BOM
    plan_bom = plan.merge(bom, on='producto', how='inner')
    plan_bom['consumo_dependiente_plan'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']

    consumo_dep = plan_bom.groupby('sku_material')['consumo_dependiente_plan'].sum().reset_index().rename(columns={'sku_material': 'sku'})

    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario', 'lead_time_declarado_dias']].copy()
    df = df.merge(consumo_dep, on='sku', how='left').fillna({'consumo_dependiente_plan': 0})

    # Anualización a 12 meses
    df['demanda_anual_d'] = df['consumo_dependiente_plan'] * (12.0 / 21.0)
    df['consumo_diario_d'] = df['demanda_anual_d'] / 365.0

    # 2. Variabilidad de Demanda Diaria (sigma_diario)
    demanda_mensual_mat = plan_bom.groupby(['sku_material', 'periodo'])['consumo_dependiente_plan'].sum().unstack(fill_value=0)
    sigma_mensual = demanda_mensual_mat.std(axis=1)
    sigma_diario = (sigma_mensual / np.sqrt(30)).rename('sigma_diario')
    df = df.merge(sigma_diario, left_on='sku', right_index=True, how='left').fillna({'sigma_diario': 0})

    # 3. Lead Time Real por Categoría
    oc['lead_time_real_dias'] = (pd.to_datetime(oc['fecha_recepcion']) - pd.to_datetime(oc['fecha_pedido'])).dt.days
    oc_cat = oc.merge(mm[['sku', 'categoria']], on='sku', how='left')
    lt_prom_cat = oc_cat.groupby('categoria')['lead_time_real_dias'].mean().to_dict()
    df['lead_time_real_dias'] = df['categoria'].map(lt_prom_cat).fillna(df['lead_time_declarado_dias'])

    # 4. Parámetros Financieros
    C_o = 150000.0  # Costo fijo por emitir orden de compra
    i_tasa = 0.22   # Tasa anual de posesión de inventario
    Z_95 = 1.645    # Factor de servicio para 95% (riesgo ~6%)

    df['C_c'] = df['costo_unitario'] * i_tasa
    df['SS_95'] = np.round(Z_95 * df['sigma_diario'] * np.sqrt(df['lead_time_real_dias']))
    df['ROP'] = np.round((df['consumo_diario_d'] * df['lead_time_real_dias']) + df['SS_95'])
    df['EOQ'] = np.where(df['C_c'] > 0, np.round(np.sqrt((2 * df['demanda_anual_d'] * C_o) / df['C_c'])), 0)

    # Guardar reporte
    output_path = os.path.join(results_dir, 'parametros_reposicion_rop_eoq.csv')
    df.to_csv(output_path, index=False)

    # Resumen
    activos = df[df['demanda_anual_d'] > 0]
    resumen = {
        'total_skus_evaluados': len(df),
        'skus_con_demanda_activa': len(activos),
        'ss_promedio_unidades': float(activos['SS_95'].mean()),
        'rop_promedio_unidades': float(activos['ROP'].mean()),
        'eoq_promedio_unidades': float(activos['EOQ'].mean()),
        'top_rop_skus': activos.sort_values(by='ROP', ascending=False)[['sku', 'descripcion', 'demanda_anual_d', 'SS_95', 'ROP', 'EOQ']].head(5).to_dict(orient='records')
    }

    print("=== RESUMEN REPOSICIÓN Y DIMENSIONAMIENTO ROP / EOQ (QUEJA 4) ===")
    print(f"Total SKUs Evaluados: {resumen['total_skus_evaluados']}")
    print(f"SKUs con Demanda Activa: {resumen['skus_con_demanda_activa']}")
    print(f"Stock de Seguridad Promedio (SS 95%): {resumen['ss_promedio_unidades']:.1f} unidades")
    print(f"Punto de Reorden Promedio (ROP): {resumen['rop_promedio_unidades']:.1f} unidades")
    print(f"Lote Económico Promedio (EOQ): {resumen['eoq_promedio_unidades']:.1f} unidades\n")

    return resumen

if __name__ == '__main__':
    ejecutar_dimensionamiento_reposicion()
