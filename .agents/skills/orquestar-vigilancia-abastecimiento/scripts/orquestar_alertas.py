"""
Script de Orquestación: Vigilancia Integral de Abastecimiento y Generación de OCs
Proyecto: E2 SAS - Capa 3 de Arquitectura (Agente de Abastecimiento)
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

def orquestar_vigilancia_inventarios():
    base_dir = get_project_root()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)

    # Cargar datasets
    mm = pd.read_csv(os.path.join(data_dir, 'maestro_materiales_clean.csv'))
    ii = pd.read_csv(os.path.join(data_dir, 'inventario_inicial_clean.csv'))
    cf = pd.read_csv(os.path.join(data_dir, 'conteo_fisico_clean.csv'))
    mov = pd.read_csv(os.path.join(data_dir, 'movimientos_inventario_clean.csv'))
    bom = pd.read_csv(os.path.join(data_dir, 'bom_clean.csv'))
    plan = pd.read_csv(os.path.join(data_dir, 'plan_produccion_clean.csv'))
    oc = pd.read_csv(os.path.join(data_dir, 'ordenes_compra_clean.csv'))

    # 1. Reconstrucción Kardex y ERI
    mov_neto = mov.groupby(['sku', 'tipo_movimiento'])['cantidad'].sum().unstack(fill_value=0)
    entradas = mov_neto['entrada'] if 'entrada' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    salidas = mov_neto['salida'] if 'salida' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    ajustes = mov_neto['ajuste'] if 'ajuste' in mov_neto.columns else pd.Series(0, index=mov_neto.index)

    df_kardex = mm[['sku', 'descripcion', 'categoria', 'costo_unitario', 'lead_time_declarado_dias']].copy()
    df_kardex = df_kardex.merge(ii[['sku', 'stock_inicial']], on='sku', how='left').fillna({'stock_inicial': 0})
    df_kardex = df_kardex.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')
    df_kardex = df_kardex.merge(entradas.rename('entradas'), on='sku', how='left').fillna({'entradas': 0})
    df_kardex = df_kardex.merge(salidas.rename('salidas'), on='sku', how='left').fillna({'salidas': 0})
    df_kardex = df_kardex.merge(ajustes.rename('ajustes'), on='sku', how='left').fillna({'ajustes': 0})

    df_kardex['saldo_teorico'] = df_kardex['stock_inicial'] + df_kardex['entradas'] - df_kardex['salidas'] + df_kardex['ajustes']
    df_kardex['stock_real'] = df_kardex['stock_fisico_contado'].fillna(df_kardex['saldo_teorico'])

    # 2. Explosión BOM y Estadísticas
    plan_bom = plan.merge(bom, on='producto', how='inner')
    plan_bom['consumo_planeado'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']
    consumo_dep = plan_bom.groupby('sku_material')['consumo_planeado'].sum().reset_index().rename(columns={'sku_material': 'sku'})

    df_kardex = df_kardex.merge(consumo_dep, on='sku', how='left').fillna({'consumo_planeado': 0})
    df_kardex['demanda_anual'] = df_kardex['consumo_planeado'] * (12.0 / 21.0)
    df_kardex['consumo_diario'] = df_kardex['demanda_anual'] / 365.0
    df_kardex['valor_anual'] = df_kardex['demanda_anual'] * df_kardex['costo_unitario']

    # 3. Variabilidad y Lead Times
    demanda_mensual_mat = plan_bom.groupby(['sku_material', 'periodo'])['consumo_planeado'].sum().unstack(fill_value=0)
    sigma_mensual = demanda_mensual_mat.std(axis=1)
    sigma_diario = (sigma_mensual / np.sqrt(30)).rename('sigma_diario')
    df_kardex = df_kardex.merge(sigma_diario, left_on='sku', right_index=True, how='left').fillna({'sigma_diario': 0})

    oc['lead_time_real_dias'] = (pd.to_datetime(oc['fecha_recepcion']) - pd.to_datetime(oc['fecha_pedido'])).dt.days
    oc_cat = oc.merge(mm[['sku', 'categoria']], on='sku', how='left')
    lt_prom = oc_cat.groupby('categoria')['lead_time_real_dias'].mean().to_dict()
    df_kardex['lead_time_real'] = df_kardex['categoria'].map(lt_prom).fillna(df_kardex['lead_time_declarado_dias'])

    # 4. ROP, EOQ y ABC
    C_o = 150000.0
    i_tasa = 0.22
    Z_95 = 1.645

    df_kardex['C_c'] = df_kardex['costo_unitario'] * i_tasa
    df_kardex['SS_95'] = np.round(Z_95 * df_kardex['sigma_diario'] * np.sqrt(df_kardex['lead_time_real']))
    df_kardex['ROP'] = np.round((df_kardex['consumo_diario'] * df_kardex['lead_time_real']) + df_kardex['SS_95'])
    df_kardex['EOQ'] = np.where(df_kardex['C_c'] > 0, np.round(np.sqrt((2 * df_kardex['demanda_anual'] * C_o) / df_kardex['C_c'])), 0)

    # Clasificación ABC
    df_kardex = df_kardex.sort_values(by='valor_anual', ascending=False).reset_index(drop=True)
    valor_total = df_kardex['valor_anual'].sum()
    df_kardex['pct_valor_acum'] = (df_kardex['valor_anual'].cumsum() / valor_total) * 100
    df_kardex['clase_abc'] = df_kardex['pct_valor_acum'].apply(lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C'))

    # 5. Detección de Quiebres y Generación de Alertas
    df_kardex['en_quiebre'] = (df_kardex['stock_real'] <= df_kardex['ROP']) & (df_kardex['demanda_anual'] > 0)

    alertas_rojas = df_kardex[df_kardex['en_quiebre']].copy()
    alertas_rojas = alertas_rojas.sort_values(by=['clase_abc', 'valor_anual'], ascending=[True, False])

    ordenes_sugeridas = []
    for _, row in alertas_rojas.iterrows():
        ordenes_sugeridas.append({
            'sku': row['sku'],
            'descripcion': row['descripcion'],
            'categoria': row['categoria'],
            'clase_abc': row['clase_abc'],
            'stock_fisico_real': int(row['stock_real']),
            'punto_reorden_rop': int(row['ROP']),
            'stock_seguridad_ss': int(row['SS_95']),
            'cantidad_sugerida_eoq': int(row['EOQ']),
            'costo_unitario_cop': float(row['costo_unitario']),
            'inversion_estimada_cop': float(row['EOQ'] * row['costo_unitario']),
            'justificacion_ejecutiva': (
                f"Se recomienda emitir Orden de Compra por {int(row['EOQ']):,} unidades del SKU {row['sku']} "
                f"({row['descripcion']}), debido a que el stock disponible real ({int(row['stock_real']):,} unidades) "
                f"perforó el Punto de Reorden ROP ({int(row['ROP']):,} unidades). Pertenece a Clase {row['clase_abc']} "
                f"con una demanda anualizada de {int(row['demanda_anual']):,} unidades."
            )
        })

    salida = {
        'total_alertas_reorden': len(ordenes_sugeridas),
        'inversion_total_sugerida_cop': sum(item['inversion_estimada_cop'] for item in ordenes_sugeridas),
        'ordenes_sugeridas': ordenes_sugeridas
    }

    with open(os.path.join(results_dir, 'ordenes_compra_sugeridas_ia.json'), 'w', encoding='utf-8') as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print(f"=== REPORTE DE VIGILANCIA DE ABASTECIMIENTO ===")
    print(f"Total Alertas Criticas (Stock <= ROP): {salida['total_alertas_reorden']}")
    print(f"Inversion Total Sugerida: ${salida['inversion_total_sugerida_cop']:,.2f} COP\n")
    for o in ordenes_sugeridas[:5]:
        print(f"[{o['clase_abc']}] {o['sku']} - {o['descripcion']}")
        print(f"   -> Pedir: {o['cantidad_sugerida_eoq']} unids | Stock: {o['stock_fisico_real']} <= ROP: {o['punto_reorden_rop']}")
        print(f"   -> Justificacion: {o['justificacion_ejecutiva']}\n")

    return salida

if __name__ == '__main__':
    orquestar_vigilancia_inventarios()
