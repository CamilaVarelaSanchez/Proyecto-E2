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
    mm = estado.get('maestro_materiales', pd.DataFrame()) if estado else pd.DataFrame()
    ii = estado.get('inventario_inicial', pd.DataFrame()) if estado else pd.DataFrame()
    cf = estado.get('conteo_fisico', pd.DataFrame()) if estado else pd.DataFrame()
    mov = estado.get('movimientos_inventario', pd.DataFrame()) if estado else pd.DataFrame()
    
    if mm.empty:
        return {
            'df_auditoria': pd.DataFrame(),
            'eri_global_pct': 0.0,
            'total_auditados': 0,
            'concordantes': 0,
            'fantasmas': [],
            'desfases_muelle': [],
            'impacto_fantasmas_cop': 0.0,
            'impacto_desfases_cop': 0.0,
            'impacto_total_cop': 0.0
        }

    # 1. Agrupación y Reconstrucción del Kardex Canónico
    if not mov.empty and 'sku' in mov.columns and 'tipo_movimiento' in mov.columns:
        mov_neto = mov.groupby(['sku', 'tipo_movimiento'])['cantidad'].sum().unstack(fill_value=0)
        entradas = mov_neto['entrada'] if 'entrada' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
        salidas = mov_neto['salida'] if 'salida' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
        ajustes = mov_neto['ajuste'] if 'ajuste' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    else:
        entradas = pd.Series(dtype=float)
        salidas = pd.Series(dtype=float)
        ajustes = pd.Series(dtype=float)
    
    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario']].copy()
    if not ii.empty and 'stock_inicial' in ii.columns:
        df = df.merge(ii[['sku', 'stock_inicial']], on='sku', how='left').fillna({'stock_inicial': 0})
    else:
        df['stock_inicial'] = 0.0
        
    if not cf.empty and 'stock_fisico_contado' in cf.columns:
        df = df.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')
    else:
        df['stock_fisico_contado'] = np.nan
    
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
