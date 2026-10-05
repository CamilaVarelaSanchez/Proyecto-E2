"""
Script de Automatización: Auditoría de Exactitud de Registro de Inventario (ERI / IRA)
Proyecto: E2 SAS - Solución a la Queja 3 de Gerencia
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

def ejecutar_auditoria_eri():
    base_dir = get_project_root()
    data_dir = os.path.join(base_dir, 'datos_limpios')
    results_dir = os.path.join(base_dir, 'resultados_auditoria')
    os.makedirs(results_dir, exist_ok=True)

    # Cargar datasets
    mm = pd.read_csv(os.path.join(data_dir, 'maestro_materiales_clean.csv'))
    ii = pd.read_csv(os.path.join(data_dir, 'inventario_inicial_clean.csv'))
    cf = pd.read_csv(os.path.join(data_dir, 'conteo_fisico_clean.csv'))
    mov = pd.read_csv(os.path.join(data_dir, 'movimientos_inventario_clean.csv'))

    # 1. Agrupar movimientos de Kardex
    mov_neto = mov.groupby(['sku', 'tipo_movimiento'])['cantidad'].sum().unstack(fill_value=0)
    entradas = mov_neto['entrada'] if 'entrada' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    salidas = mov_neto['salida'] if 'salida' in mov_neto.columns else pd.Series(0, index=mov_neto.index)
    ajustes = mov_neto['ajuste'] if 'ajuste' in mov_neto.columns else pd.Series(0, index=mov_neto.index)

    df = mm[['sku', 'descripcion', 'categoria', 'costo_unitario']].copy()
    df = df.merge(ii[['sku', 'stock_inicial']], on='sku', how='left').fillna({'stock_inicial': 0})
    df = df.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')

    df = df.merge(entradas.rename('entradas_kardex'), on='sku', how='left').fillna({'entradas_kardex': 0})
    df = df.merge(salidas.rename('salidas_kardex'), on='sku', how='left').fillna({'salidas_kardex': 0})
    df = df.merge(ajustes.rename('ajustes_kardex'), on='sku', how='left').fillna({'ajustes_kardex': 0})

    # 2. Saldo Teórico Canónico
    df['saldo_sistema'] = df['stock_inicial'] + df['entradas_kardex'] - df['salidas_kardex'] + df['ajustes_kardex']
    df['discrepancia_neta'] = df['saldo_sistema'] - df['stock_fisico_contado']
    df['discrepancia_absoluta'] = df['discrepancia_neta'].abs()
    df['impacto_financiero_cop'] = df['discrepancia_absoluta'] * df['costo_unitario']

    # 3. Auditoría ERI con tolerancia +-5%
    auditados = df[df['stock_fisico_contado'].notna()].copy()
    auditados['concordancia_5pct'] = (auditados['discrepancia_absoluta'] <= (0.05 * auditados['stock_fisico_contado'])) | (auditados['discrepancia_absoluta'] == 0)
    auditados['concordancia_estricta'] = auditados['discrepancia_absoluta'] == 0

    def tipificar(row):
        if row['concordancia_5pct']:
            return 'Concordante (+-5%)'
        elif row['saldo_sistema'] > row['stock_fisico_contado']:
            return 'Material Fantasma (Kardex > Fisico)'
        else:
            return 'Desfase Muelle (Fisico > Kardex)'

    auditados['diagnostico_eri'] = auditados.apply(tipificar, axis=1)

    # Guardar reporte detallado
    output_path = os.path.join(results_dir, 'auditoria_eri_detallada.csv')
    auditados.to_csv(output_path, index=False)

    # Resumen
    total_aud = len(auditados)
    concordantes = int(auditados['concordancia_5pct'].sum())
    fantasmas = auditados[auditados['diagnostico_eri'] == 'Material Fantasma (Kardex > Fisico)']
    desfases = auditados[auditados['diagnostico_eri'] == 'Desfase Muelle (Fisico > Kardex)']

    resumen = {
        'total_skus_auditados': total_aud,
        'eri_tolerancia_5pct': float((concordantes / total_aud) * 100),
        'eri_estricto_0pct': float((auditados['concordancia_estricta'].sum() / total_aud) * 100),
        'total_fantasmas_skus': len(fantasmas),
        'impacto_fantasmas_cop': float(fantasmas['impacto_financiero_cop'].sum()),
        'total_desfase_muelle_skus': len(desfases),
        'impacto_desfase_cop': float(desfases['impacto_financiero_cop'].sum())
    }

    print("=== RESUMEN AUDITORÍA ERI (QUEJA 3) ===")
    print(f"SKUs Auditados: {resumen['total_skus_auditados']}")
    print(f"Indicador ERI (+-5% tolerancia): {resumen['eri_tolerancia_5pct']:.2f}% ({concordantes}/{total_aud})")
    print(f"Indicador ERI Estricto (0% error): {resumen['eri_estricto_0pct']:.2f}%")
    print(f"Materiales Fantasmas: {resumen['total_fantasmas_skus']} SKUs | Impacto: ${resumen['impacto_fantasmas_cop']:,.2f} COP")
    print(f"Desfases de Muelle (Kardex < Fisico): {resumen['total_desfase_muelle_skus']} SKUs | Impacto: ${resumen['impacto_desfase_cop']:,.2f} COP")

    return resumen

if __name__ == '__main__':
    ejecutar_auditoria_eri()
