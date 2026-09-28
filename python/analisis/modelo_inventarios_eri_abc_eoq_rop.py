"""
Modelo Integral de Gestión de Inventarios - E2 SAS (Producción 4.0 / Énfasis 2)
Cálculo riguroso de:
1. Indicador ERI (Exactitud de Registros de Inventario con tolerancia +-5% y análisis de saldo sistema)
2. Referencias Fantasmas y Discrepancias Físico vs Sistema
3. Explosión de Demanda Dependiente de Materiales (Plan de Producción x BOM) vs Demanda Independiente (PT)
4. Clasificación ABC basada estrictamente en Valor de Consumo Anual (Consumo Anual x Precio Unitario)
5. Análisis de Cuellos de Botella: Lámina vs Vidrio y Tiempos de Suministro (Lead Time)
6. Modelado de EOQ Básico, Stock de Seguridad (Z=95%, SLA 6% riesgo de stockout) y Punto de Reorden (ROP)
"""

import os
import pandas as pd
import numpy as np
import json

# Rutas del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR)) if os.path.basename(CURRENT_DIR) == 'analisis' else os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'datos_limpios')
RESULTS_DIR = os.path.join(BASE_DIR, 'resultados_auditoria')

os.makedirs(RESULTS_DIR, exist_ok=True)

# 1. Cargar conjuntos de datos limpios
mm = pd.read_csv(os.path.join(DATA_DIR, 'maestro_materiales_clean.csv'))
ii = pd.read_csv(os.path.join(DATA_DIR, 'inventario_inicial_clean.csv'))
cf = pd.read_csv(os.path.join(DATA_DIR, 'conteo_fisico_clean.csv'))
jefe = pd.read_csv(os.path.join(DATA_DIR, 'inventario_bodega_JEFE_clean.csv'))
bom = pd.read_csv(os.path.join(DATA_DIR, 'bom_clean.csv'))
plan = pd.read_csv(os.path.join(DATA_DIR, 'plan_produccion_clean.csv'))
oc = pd.read_csv(os.path.join(DATA_DIR, 'ordenes_compra_clean.csv'))
mov = pd.read_csv(os.path.join(DATA_DIR, 'movimientos_inventario_clean.csv'))

# ==============================================================================
# 1. EXACTITUD DE REGISTRO DE INVENTARIO (ERI / IRA)
# ==============================================================================
# Fórmula: SISTEMA = INV_INICIAL + ENTRADAS - SALIDAS +- AJUSTES
mov_neto = mov.groupby(['sku', 'tipo_movimiento'])['cantidad'].sum().unstack(fill_value=0)
entradas = mov_neto['entrada'] if 'entrada' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
salidas = mov_neto['salida'] if 'salida' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
ajustes = mov_neto['ajuste'] if 'ajuste' in mov_neto.columns else pd.Series(0, index=mov_neto.index)

df_eri = mm[['sku', 'descripcion', 'categoria', 'costo_unitario', 'lead_time_declarado_dias']].copy()
df_eri = df_eri.merge(ii[['sku', 'stock_inicial']], on='sku', how='left').fillna({'stock_inicial': 0})
df_eri = df_eri.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')

df_eri = df_eri.merge(entradas.rename('entradas_kardex'), on='sku', how='left').fillna({'entradas_kardex': 0})
df_eri = df_eri.merge(salidas.rename('salidas_kardex'), on='sku', how='left').fillna({'salidas_kardex': 0})
df_eri = df_eri.merge(ajustes.rename('ajustes_kardex'), on='sku', how='left').fillna({'ajustes_kardex': 0})

df_eri['saldo_sistema'] = df_eri['stock_inicial'] + df_eri['entradas_kardex'] - df_eri['salidas_kardex'] + df_eri['ajustes_kardex']
df_eri['dif_sistema_fisico'] = df_eri['saldo_sistema'] - df_eri['stock_fisico_contado']
df_eri['dif_absoluta'] = df_eri['dif_sistema_fisico'].abs()

# Tolerancia +- 5% sobre el conteo físico
df_eri_auditados = df_eri[df_eri['stock_fisico_contado'].notna()].copy()
df_eri_auditados['eri_exacto_0'] = df_eri_auditados['dif_absoluta'] == 0
df_eri_auditados['eri_5pct'] = (df_eri_auditados['dif_absoluta'] <= 0.05 * df_eri_auditados['stock_fisico_contado']) | (df_eri_auditados['dif_absoluta'] == 0)

# ==============================================================================
# 2. EXPLOSIÓN DE DEMANDA DEPENDIENTE (PLAN PROD x BOM)
# ==============================================================================
# Demanda independiente de PT
plan_bom = plan.merge(bom, on='producto', how='inner')
plan_bom['consumo_dependiente_plan'] = plan_bom['cantidad_planeada'] * plan_bom['cantidad_por_unidad']
plan_bom['consumo_dependiente_real'] = plan_bom['cantidad_real'] * plan_bom['cantidad_por_unidad']

consumo_dep = plan_bom.groupby('sku_material').agg({
    'consumo_dependiente_plan': 'sum',
    'consumo_dependiente_real': 'sum'
}).reset_index().rename(columns={'sku_material': 'sku'})

consumo_total = mm.merge(consumo_dep, on='sku', how='left').fillna({'consumo_dependiente_plan': 0, 'consumo_dependiente_real': 0})
consumo_total = consumo_total.merge(salidas.rename('salidas_kardex_21m'), on='sku', how='left').fillna({'salidas_kardex_21m': 0})

# Anualización de consumo (21 meses -> 12 meses: factor 12/21)
consumo_total['demanda_anual_d'] = consumo_total['consumo_dependiente_plan'] * (12.0 / 21.0)
consumo_total['consumo_diario_d'] = consumo_total['demanda_anual_d'] / 365.0
consumo_total['valor_consumo_anual'] = consumo_total['demanda_anual_d'] * consumo_total['costo_unitario']

# ==============================================================================
# 3. CLASIFICACIÓN ABC (VALOR DE CONSUMO ANUAL)
# ==============================================================================
consumo_total = consumo_total.sort_values(by='valor_consumo_anual', ascending=False).reset_index(drop=True)
consumo_total['valor_acumulado'] = consumo_total['valor_consumo_anual'].cumsum()
valor_total_anual = consumo_total['valor_consumo_anual'].sum()
consumo_total['pct_valor_acumulado'] = (consumo_total['valor_acumulado'] / valor_total_anual) * 100
consumo_total['pct_sku_acumulado'] = ((consumo_total.index + 1) / len(consumo_total)) * 100

def asignar_abc(pct):
    if pct <= 80.0:
        return 'A'
    elif pct <= 95.0:
        return 'B'
    else:
        return 'C'

consumo_total['clasificacion_abc'] = consumo_total['pct_valor_acumulado'].apply(asignar_abc)

# ==============================================================================
# 4. ANÁLISIS DE LEAD TIME, EOQ, ROP Y STOCK DE SEGURIDAD (Z=95%, SLA 6%)
# ==============================================================================
oc['lead_time_real_dias'] = (pd.to_datetime(oc['fecha_recepcion']) - pd.to_datetime(oc['fecha_pedido'])).dt.days
oc_analisis = oc.merge(mm[['sku', 'categoria']], on='sku', how='left')

lt_cat_real = oc_analisis.groupby('categoria')['lead_time_real_dias'].mean().to_dict()
consumo_total['lead_time_real_est'] = consumo_total['categoria'].map(lt_cat_real).fillna(consumo_total['lead_time_declarado_dias'])

# Variabilidad diaria de demanda de insumos
demanda_mensual_mat = plan_bom.groupby(['sku_material', 'periodo'])['consumo_dependiente_plan'].sum().unstack(fill_value=0)
sigma_mensual = demanda_mensual_mat.std(axis=1)
sigma_diario = (sigma_mensual / np.sqrt(30)).rename('sigma_diario')

consumo_total = consumo_total.merge(sigma_diario, left_on='sku', right_index=True, how='left').fillna({'sigma_diario': 0})

# Parámetros financieros:
# Co = 150.000 COP por orden de compra emitida
# Cc = i * Cu (tasa anual de posesión i = 22%)
# Z = 1.645 (Nivel de servicio 95% / Riesgo de quiebre SLA aprox. 5.5 - 6%)
C_o = 150000.0
i_tasa = 0.22
Z_95 = 1.645

consumo_total['C_c'] = consumo_total['costo_unitario'] * i_tasa
consumo_total['EOQ'] = np.where(consumo_total['C_c'] > 0, np.sqrt((2 * consumo_total['demanda_anual_d'] * C_o) / consumo_total['C_c']), 0)
consumo_total['SS_95'] = Z_95 * consumo_total['sigma_diario'] * np.sqrt(consumo_total['lead_time_real_est'])
consumo_total['ROP'] = (consumo_total['consumo_diario_d'] * consumo_total['lead_time_real_est']) + consumo_total['SS_95']

# ==============================================================================
# 5. GUARDAR RESULTADOS CONSOLIDADOS
# ==============================================================================
consumo_total.to_csv(os.path.join(RESULTS_DIR, 'parametros_inventario_eoq_rop_abc.csv'), index=False)
df_eri.to_csv(os.path.join(RESULTS_DIR, 'auditoria_eri_detallada.csv'), index=False)

resumen_metricas = {
    "total_skus_maestro": len(mm),
    "total_skus_conteo_fisico": len(df_eri_auditados),
    "eri_estricto_0pct": float(df_eri_auditados['eri_exacto_0'].mean() * 100),
    "eri_tolerancia_5pct": float(df_eri_auditados['eri_5pct'].mean() * 100),
    "valor_total_consumo_anual_cop": float(valor_total_anual),
    "abc_resumen": {
        "clase_A": {
            "skus": int((consumo_total['clasificacion_abc'] == 'A').sum()),
            "pct_skus": float((consumo_total['clasificacion_abc'] == 'A').mean() * 100),
            "valor_cop": float(consumo_total[consumo_total['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum()),
            "pct_valor": float((consumo_total[consumo_total['clasificacion_abc'] == 'A']['valor_consumo_anual'].sum() / valor_total_anual) * 100)
        },
        "clase_B": {
            "skus": int((consumo_total['clasificacion_abc'] == 'B').sum()),
            "pct_skus": float((consumo_total['clasificacion_abc'] == 'B').mean() * 100),
            "valor_cop": float(consumo_total[consumo_total['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum()),
            "pct_valor": float((consumo_total[consumo_total['clasificacion_abc'] == 'B']['valor_consumo_anual'].sum() / valor_total_anual) * 100)
        },
        "clase_C": {
            "skus": int((consumo_total['clasificacion_abc'] == 'C').sum()),
            "pct_skus": float((consumo_total['clasificacion_abc'] == 'C').mean() * 100),
            "valor_cop": float(consumo_total[consumo_total['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum()),
            "pct_valor": float((consumo_total[consumo_total['clasificacion_abc'] == 'C']['valor_consumo_anual'].sum() / valor_total_anual) * 100)
        }
    },
    "cuello_botella_lead_time": {
        "lamina_lt_declarado": float(mm[mm['categoria'] == 'Lámina']['lead_time_declarado_dias'].mean()),
        "lamina_lt_real": float(oc_analisis[oc_analisis['categoria'] == 'Lámina']['lead_time_real_dias'].mean()),
        "vidrio_lt_declarado": float(mm[mm['categoria'] == 'Vidrio']['lead_time_declarado_dias'].mean()),
        "vidrio_lt_real": float(oc_analisis[oc_analisis['categoria'] == 'Vidrio']['lead_time_real_dias'].mean()),
        "valor_consumo_anual_lamina": float(consumo_total[consumo_total['categoria'] == 'Lámina']['valor_consumo_anual'].sum()),
        "valor_consumo_anual_vidrio": float(consumo_total[consumo_total['categoria'] == 'Vidrio']['valor_consumo_anual'].sum())
    }
}

with open(os.path.join(RESULTS_DIR, 'metricas_modelo_inventarios.json'), 'w', encoding='utf-8') as f:
    json.dump(resumen_metricas, f, indent=2, ensure_ascii=False)

print("¡Modelo ejecutado y archivos generados exitosamente en resultados_auditoria/!")
