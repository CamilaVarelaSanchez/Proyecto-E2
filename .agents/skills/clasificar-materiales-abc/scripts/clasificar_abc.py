"""
Script de Automatización: Clasificación ABC de Materiales (Demanda Anualizada por Valor)
Proyecto: E2 SAS - Gestión de Inventarios
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

def ejecutar_clasificacion_abc():
    base_dir = get_project_root()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)

    # Cargar datos limpios
    mm = pd.read_csv(os.path.join(data_dir, 'maestro_materiales_clean.csv'))
    bom = pd.read_csv(os.path.join(data_dir, 'bom_clean.csv'))
    plan = pd.read_csv(os.path.join(data_dir, 'plan_produccion_clean.csv'))

    # 1. Explosión Plan x BOM
    plan_bom = plan.merge(bom, on='producto', how='inner')
    plan_bom['consumo_planeado'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']

    consumo_dep = plan_bom.groupby('sku_material')['consumo_planeado'].sum().reset_index().rename(columns={'sku_material': 'sku'})

    # 2. Anualización y Valorización
    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario']].merge(consumo_dep, on='sku', how='left').fillna({'consumo_planeado': 0})
    df['demanda_anual'] = df['consumo_planeado'] * (12.0 / 21.0)
    df['valor_consumo_anual'] = df['demanda_anual'] * df['costo_unitario']

    # 3. Ordenamiento y Porcentajes Acumulados
    df = df.sort_values(by='valor_consumo_anual', ascending=False).reset_index(drop=True)
    valor_total = df['valor_consumo_anual'].sum()
    df['valor_acumulado'] = df['valor_consumo_anual'].cumsum()
    df['pct_valor_acumulado'] = (df['valor_acumulado'] / valor_total) * 100
    df['pct_sku_acumulado'] = ((df.index + 1) / len(df)) * 100

    # 4. Asignación ABC
    def asignar(pct):
        if pct <= 80.0:
            return 'A'
        elif pct <= 95.0:
            return 'B'
        else:
            return 'C'

    df['clasificacion_abc'] = df['pct_valor_acumulado'].apply(asignar)

    # Guardar resultado CSV
    output_path = os.path.join(results_dir, 'clasificacion_abc_materiales.csv')
    df.to_csv(output_path, index=False)

    # Resumen
    resumen = {
        'total_skus': len(df),
        'valor_total_anual_cop': float(valor_total),
        'clase_A': {
            'skus': int((df['clasificacion_abc'] == 'A').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'A').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum() / valor_total) * 100)
        },
        'clase_B': {
            'skus': int((df['clasificacion_abc'] == 'B').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'B').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum() / valor_total) * 100)
        },
        'clase_C': {
            'skus': int((df['clasificacion_abc'] == 'C').sum()),
            'pct_skus': float((df['clasificacion_abc'] == 'C').mean() * 100),
            'valor_cop': float(df[df['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum()),
            'pct_valor': float((df[df['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum() / valor_total) * 100)
        }
    }

    print("=== RESUMEN CLASIFICACIÓN ABC (PARETO 80-15-5) ===")
    print(f"Total SKUs: {resumen['total_skus']}")
    print(f"Valor Total Anual: ${resumen['valor_total_anual_cop']:,.2f} COP\n")
    for clase in ['clase_A', 'clase_B', 'clase_C']:
        info = resumen[clase]
        print(f"[{clase[-1]}]: {info['skus']} SKUs ({info['pct_skus']:.2f}%) | ${info['valor_cop']:,.2f} COP ({info['pct_valor']:.2f}%)")

    return resumen

if __name__ == '__main__':
    ejecutar_clasificacion_abc()
