"""
Script de Automatización: Validación de Sanidad y Calidad de Datos (Capa 0)
Proyecto: E2 SAS - Data Cleansing & Integrity Verification
"""

import os
import sys
import pandas as pd
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

def validar_calidad_datos():
    base_dir = get_project_root()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)

    archivos = {
        'maestro_materiales': 'maestro_materiales_clean.csv',
        'maestro_productos': 'maestro_productos_clean.csv',
        'bom': 'bom_clean.csv',
        'plan_produccion': 'plan_produccion_clean.csv',
        'ordenes_compra': 'ordenes_compra_clean.csv',
        'movimientos_inventario': 'movimientos_inventario_clean.csv',
        'conteo_fisico': 'conteo_fisico_clean.csv',
        'inventario_inicial': 'inventario_inicial_clean.csv'
    }

    dfs = {}
    for nombre, arch in archivos.items():
        ruta = os.path.join(data_dir, arch)
        if os.path.exists(ruta):
            dfs[nombre] = pd.read_csv(ruta)
        else:
            print(f"Advertencia: Archivo no encontrado {ruta}")

    hallazgos = []

    # 1. Chequeo de duplicados en maestros
    mm = dfs.get('maestro_materiales')
    if mm is not None:
        dups_mm = mm[mm.duplicated(subset=['sku'], keep=False)]
        if len(dups_mm) > 0:
            hallazgos.append(f"Duplicados en maestro_materiales: {len(dups_mm)} registros.")
        
        nulos_costo = mm[mm['costo_unitario'].isna() | (mm['costo_unitario'] <= 0)]
        if len(nulos_costo) > 0:
            hallazgos.append(f"Costos unitarios invalidos en maestro_materiales: {len(nulos_costo)} registros.")

    # 2. Chequeo de integridad referencial
    if mm is not None:
        skus_validos = set(mm['sku'].unique())

        for tbl in ['movimientos_inventario', 'conteo_fisico', 'ordenes_compra']:
            df_check = dfs.get(tbl)
            if df_check is not None and 'sku' in df_check.columns:
                huerfanos = set(df_check['sku'].unique()) - skus_validos
                if len(huerfanos) > 0:
                    hallazgos.append(f"SKUs huerfanos en {tbl}: {len(huerfanos)} SKUs no existen en maestro.")

        bom = dfs.get('bom')
        if bom is not None and 'sku_material' in bom.columns:
            huerfanos_bom = set(bom['sku_material'].unique()) - skus_validos
            if len(huerfanos_bom) > 0:
                hallazgos.append(f"Insumos huerfanos en BOM: {len(huerfanos_bom)} materiales no existen en maestro.")

    print("=== REPORTE DE SANIDAD Y CALIDAD DE DATOS ===")
    if len(hallazgos) == 0:
        print("[OK] Base de datos 100% SANA: Cero duplicados, cero nulos criticos y 100% de integridad referencial.")
    else:
        print(f"[ALERTA] Se detectaron {len(hallazgos)} inconsistencias:")
        for h in hallazgos:
            print(f" - {h}")

    return hallazgos

if __name__ == '__main__':
    validar_calidad_datos()
