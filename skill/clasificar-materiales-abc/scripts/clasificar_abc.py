"""
Script Automatizado: Clasificación ABC de Materiales
Skill: clasificar-materiales-abc (Producción 4.0 / Énfasis 2 - E2 SAS)

Pasos implementados:
1. Traer consumo del periodo y costo unitario de cada material (excluyendo duplicados).
2. Valor de consumo = consumo anual x costo unitario.
3. Ordenar de mayor a menor y acumular el porcentaje.
4. Clase A hasta 80% acumulado, B hasta 95%, C el resto.
5. Excluir materiales duplicados antes de calcular.

Cómo verificar:
- Los porcentajes acumulados deben llegar a 100%.
- La clase A debe ser pocos materiales con mucho valor.
- Reportar cuántos SKU y qué % del valor tiene cada clase.
"""

import os
import sys
import pandas as pd
import numpy as np

# Compatibilidad UTF-8 en terminales Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def clasificar_materiales_abc():
    # 0. Ubicación de archivos en el repositorio
    # Proyecto E2 / skill / clasificar-materiales-abc / scripts / clasificar_abc.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    data_dir = os.path.join(base_dir, 'datos_limpios')
    
    # 1. Traer datos
    mm_path = os.path.join(data_dir, 'maestro_materiales_clean.csv')
    bom_path = os.path.join(data_dir, 'bom_clean.csv')
    plan_path = os.path.join(data_dir, 'plan_produccion_clean.csv')
    
    mm = pd.read_csv(mm_path)
    bom = pd.read_csv(bom_path)
    plan = pd.read_csv(plan_path)
    
    # Paso 5: Excluir materiales duplicados antes de calcular
    mm = mm.drop_duplicates(subset=['sku']).copy()
    
    # Paso 1: Traer consumo del periodo y costo unitario
    # Explosión de demanda dependiente: Plan Maestro x BOM
    plan_bom = plan.merge(bom, on='producto', how='inner')
    plan_bom['consumo_periodo'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']
    
    consumo_dep = plan_bom.groupby('sku_material')['consumo_periodo'].sum().reset_index()
    consumo_dep.rename(columns={'sku_material': 'sku'}, inplace=True)
    
    # Unir con maestro de materiales
    df = mm.merge(consumo_dep, on='sku', how='left').fillna({'consumo_periodo': 0})
    
    # Anualización (21 meses de horizonte -> 12 meses anuales: factor 12/21)
    df['consumo_anual'] = df['consumo_periodo'] * (12.0 / 21.0)
    
    # Paso 2: Valor de consumo = consumo anual x costo unitario
    df['valor_consumo'] = df['consumo_anual'] * df['costo_unitario']
    
    # Paso 3: Ordenar de mayor a menor y acumular el porcentaje
    df = df.sort_values(by=['valor_consumo', 'sku'], ascending=[False, True]).reset_index(drop=True)
    df['valor_acumulado'] = df['valor_consumo'].cumsum()
    valor_total = df['valor_consumo'].sum()
    
    df['pct_valor_acumulado'] = (df['valor_acumulado'] / valor_total) * 100.0
    
    # Paso 4: Clase A hasta 80% acumulado, B hasta 95%, C el resto
    def asignar_clase(pct):
        if pct <= 80.0:
            return 'A'
        elif pct <= 95.0:
            return 'B'
        else:
            return 'C'
            
    df['clasificacion_abc'] = df['pct_valor_acumulado'].apply(asignar_clase)
    
    # =========================================================================
    # CÓMO VERIFICAR
    # =========================================================================
    print("=" * 80)
    print("🔬 VERIFICACIÓN DE LA CLASIFICACIÓN ABC (SKILL: clasificar-materiales-abc)")
    print("=" * 80)
    
    # Verificación 1: Los porcentajes acumulados deben llegar a 100%
    pct_final = df['pct_valor_acumulado'].iloc[-1]
    print(f"1. Porcentaje Acumulado Final: {pct_final:.2f}% (Meta: 100.0%) -> {'✅ CORRECTO' if abs(pct_final - 100.0) < 1e-4 else '❌ ERROR'}")
    
    # Resumen por clase
    resumen = df.groupby('clasificacion_abc').agg(
        total_skus=('sku', 'count'),
        valor_total_cop=('valor_consumo', 'sum')
    ).reset_index()
    
    resumen['pct_skus'] = (resumen['total_skus'] / len(df)) * 100.0
    resumen['pct_valor'] = (resumen['valor_total_cop'] / valor_total) * 100.0
    
    # Verificación 2: La clase A debe ser pocos materiales con mucho valor
    skus_a = resumen.loc[resumen['clasificacion_abc'] == 'A', 'pct_skus'].values[0]
    val_a = resumen.loc[resumen['clasificacion_abc'] == 'A', 'pct_valor'].values[0]
    print(f"2. Principio de Pareto (Clase A): {skus_a:.2f}% de los SKUs concentran el {val_a:.2f}% del valor financiero -> {'✅ CUMPLE PARETO' if skus_a < 15 and val_a >= 75 else '⚠️ REVISAR'}")
    
    # Verificación 3: Reportar cuántos SKU y qué % del valor tiene cada clase
    print("\n3. REPORTE DE RESULTADOS POR CLASE ABC:")
    print("-" * 80)
    print(f"{'Clase':<6} | {'SKUs':<8} | {'% SKUs':<10} | {'Valor Anual Total (COP)':<25} | {'% Valor Financiero':<18}")
    print("-" * 80)
    for _, row in resumen.iterrows():
        print(f"{row['clasificacion_abc']:<6} | {row['total_skus']:<8} | {row['pct_skus']:>8.2f}% | ${row['valor_total_cop']:>22,.2f} | {row['pct_valor']:>16.2f}%")
    print("-" * 80)
    print(f"{'TOTAL':<6} | {len(df):<8} | {100.0:>8.2f}% | ${valor_total:>22,.2f} | {100.0:>16.2f}%")
    print("=" * 80)
    
    # Top 10 Clase A
    print("\n🔝 TOP 10 MATERIALES DE MAYOR IMPORTANCIA (CLASE A):")
    print("-" * 95)
    print(f"{'SKU':<10} | {'Descripción':<26} | {'Categoría':<12} | {'Costo Unit.':<12} | {'Consumo Anual':<14} | {'Valor Anual (COP)':<18} | {'% Acum.'}")
    print("-" * 95)
    for _, r in df.head(10).iterrows():
        print(f"{r['sku']:<10} | {r['descripcion'][:25]:<26} | {r['categoria'][:11]:<12} | ${r['costo_unitario']:>10,.0f} | {r['consumo_anual']:>12,.1f}  | ${r['valor_consumo']:>16,.0f} | {r['pct_valor_acumulado']:>6.2f}%")
    print("-" * 95)
    
    return df, resumen

if __name__ == '__main__':
    clasificar_materiales_abc()
