"""
Módulo del Núcleo: RECONCILIACIÓN DE INVENTARIO Y EXACTITUD DE REGISTRO (ERI / IRA)
Responsabilidad Única: Reconstruir el Kardex canónico relacional, contrastar contra auditoría física
                       y conciliar discrepancias bajo un umbral de tolerancia del ±5%.
Contrato:
  - auditar_eri(estado, tolerancia=0.05) -> dict: {
        'df_auditoria': DataFrame,
        'eri_global_pct': float,
        'total_auditados': int,
        'concordantes': int,
        'fantasmas': list,
        'desfases_muelle': list,
        'impacto_fantasmas_cop': float,
        'impacto_desfases_cop': float,
        'impacto_total_cop': float
    }
"""

import pandas as pd
import numpy as np

def auditar_eri(estado, tolerancia=0.05):
    """
    Reconstruye el saldo teórico de Kardex:
      Saldo Teórico = Inventario Inicial + Entradas - Salidas ± Ajustes
    Contrasta contra el conteo físico en piso con umbral de tolerancia del ±5%.
    """
    mm = estado['maestro_materiales']
    ii = estado['inventario_inicial']
    cf = estado['conteo_fisico']
    mov = estado['movimientos_inventario']
    
    # 1. Agrupación y Reconstrucción del Kardex Canónico
    mov_neto = mov.groupby(['sku', 'tipo_movimiento'])['cantidad'].sum().unstack(fill_value=0)
    entradas = mov_neto['entrada'] if 'entrada' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    salidas = mov_neto['salida'] if 'salida' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    ajustes = mov_neto['ajuste'] if 'ajuste' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    
    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario']].copy()
    df = df.merge(ii[['sku', 'stock_inicial']], on='sku', how='left').fillna({'stock_inicial': 0})
    df = df.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')
    
    df = df.merge(entradas.rename('entradas'), on='sku', how='left').fillna({'entradas': 0})
    df = df.merge(salidas.rename('salidas'), on='sku', how='left').fillna({'salidas': 0})
    df = df.merge(ajustes.rename('ajustes'), on='sku', how='left').fillna({'ajustes': 0})
    
    # 2. Saldo Teórico y Discrepancias
    df['saldo_teorico'] = df['stock_inicial'] + df['entradas'] - df['salidas'] + df['ajustes']
    df['discrepancia_neta'] = df['saldo_teorico'] - df['stock_fisico_contado']
    df['discrepancia_absoluta'] = df['discrepancia_neta'].abs()
    df['impacto_financiero_cop'] = df['discrepancia_absoluta'] * df['costo_unitario']
    
    # 3. Auditoría de Exactitud de Registro (ERI / IRA con umbral ±5%)
    auditados = df[df['stock_fisico_contado'].notna()].copy()
    auditados['concordancia'] = (auditados['discrepancia_absoluta'] <= (tolerancia * auditados['stock_fisico_contado'])) | (auditados['discrepancia_absoluta'] == 0)
    
    def tipificar(row):
        if row['concordancia']:
            return 'Concordante (±5%)'
        elif row['saldo_teorico'] > row['stock_fisico_contado']:
            return 'Faltante en Piso / No Localizado (Kardex > Físico)'
        else:
            return 'Desfase en Muelle de Recepción (Físico > Kardex)'
            
    auditados['diagnostico_eri'] = auditados.apply(tipificar, axis=1)
    
    total_aud = len(auditados)
    concordantes = int(auditados['concordancia'].sum())
    eri_pct = float((concordantes / total_aud) * 100) if total_aud > 0 else 0.0
    
    fantasmas_df = auditados[auditados['diagnostico_eri'] == 'Faltante en Piso / No Localizado (Kardex > Físico)']
    desfases_df = auditados[auditados['diagnostico_eri'] == 'Desfase en Muelle de Recepción (Físico > Kardex)']
    
    impacto_fantasmas = float(fantasmas_df['impacto_financiero_cop'].sum())
    impacto_desfases = float(desfases_df['impacto_financiero_cop'].sum())
    impacto_total = impacto_fantasmas + impacto_desfases
    
    return {
        'df_auditoria': auditados,
        'eri_global_pct': round(eri_pct, 2),
        'total_auditados': total_aud,
        'concordantes': concordantes,
        'fantasmas': fantasmas_df.to_dict(orient='records'),
        'desfases_muelle': desfases_df.to_dict(orient='records'),
        'impacto_fantasmas_cop': round(impacto_fantasmas, 2),
        'impacto_desfases_cop': round(impacto_desfases, 2),
        'impacto_total_cop': round(impacto_total, 2)
    }
