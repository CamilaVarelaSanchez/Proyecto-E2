"""
ORQUESTADOR PRINCIPAL DEL SISTEMA - E2 SAS (Producción 4.0 / Énfasis II)
Responsabilidad: Encadenar los módulos del núcleo en el orden definido por la arquitectura,
                 manejar excepciones, evaluar criterios de parada y registrar el resultado.
"""

import os
import sys
import pandas as pd
from nucleo import datos, validador, eri, bom, abc, reposicion, explicador

def ejecutar_orquestacion(tolerancia_eri=0.05, nivel_servicio_z=1.645):
    """
    Ejecuta el ciclo integral de reposición y abastecimiento.
    Retorna un diccionario estructurado con:
      - kpis: resumen de salud del inventario
      - propuestas_compra: lista de sugerencias que requieren aprobación
      - alertas_auditoria: discrepancias ERI detectadas
      - estado_ejecucion: status y trazabilidad
    """
    print("--- [1/6] Leyendo estado canónico de datos ---")
    estado = datos.leer_estado()
    
    print("--- [2/6] Validando calidad de datos (Capa 0) ---")
    val = validador.verificar_sanidad(estado)
    if not val['valido']:
        print(f"[ERROR DE SANIDAD]: {val['hallazgos']}")
        return {
            'status': 'error_sanidad',
            'mensaje': 'El sistema se detuvo por inconsistencias en la base de datos.',
            'hallazgos': val['hallazgos']
        }
        
    print("--- [3/6] Reconciliando Kardex y Auditoría ERI (Queja 3) ---")
    res_eri = eri.auditar_eri(estado, tolerancia=tolerancia_eri)
    
    print("--- [4/6] Explosión BOM y Variabilidad de Demanda (Queja 4) ---")
    res_bom = bom.explotar_bom(estado)
    
    print("--- [5/6] Valorización Anualizada y Clasificación Pareto ABC ---")
    res_abc = abc.clasificar_abc(res_bom['df_demanda_insumos'])
    
    print("--- [6/6] Dimensionamiento Dinámico ROP / EOQ / SS (Queja 4) ---")
    res_rep = reposicion.calcular_parametros_reposicion(res_abc['df_abc'], estado, z=nivel_servicio_z)
    
    # 7. Cruce Multivariable: Stock Físico Real vs ROP
    df_parametros = res_rep['df_parametros'].copy()
    
    # Vincular con conteo físico auditado o saldo teórico
    cf = estado['conteo_fisico']
    df_parametros = df_parametros.merge(cf[['sku', 'stock_fisico_contado']], on='sku', how='left')
    
    # Reconstruir Kardex teórico si no hay conteo físico
    df_eri_res = res_eri['df_auditoria'][['sku', 'saldo_teorico']]
    df_parametros = df_parametros.merge(df_eri_res, on='sku', how='left')
    df_parametros['stock_real'] = df_parametros['stock_fisico_contado'].fillna(df_parametros['saldo_teorico']).fillna(0)
    
    # Identificar Quiebres (Stock Real <= ROP)
    df_quiebres = df_parametros[(df_parametros['stock_real'] <= df_parametros['ROP']) & (df_parametros['demanda_anual_d'] > 0)].copy()
    df_quiebres = df_quiebres.sort_values(by=['clasificacion_abc', 'valor_consumo_anual'], ascending=[True, False])
    
    # 8. Generar Propuestas con Justificación en Lenguaje Natural (IA)
    propuestas = explicador.generar_propuestas(df_quiebres)
    
    # 9. Estructurar Respuesta Consolidada
    inversion_total = sum(p['inversion_estimada_cop'] for p in propuestas)
    
    resultado_consolidado = {
        'status': 'completado',
        'kpis': {
            'total_skus': len(df_parametros),
            'eri_global_pct': round(res_eri['eri_global_pct'], 2),
            'valor_total_anual_cop': round(res_abc['valor_total_anual'], 2),
            'skus_en_quiebre': len(propuestas),
            'inversion_propuesta_cop': round(inversion_total, 2),
            'materiales_fantasmas_detectados': len(res_eri['fantasmas']),
            'desfases_muelle_detectados': len(res_eri['desfases_muelle'])
        },
        'resumen_abc': res_abc['resumen_clases'],
        'propuestas_compra': propuestas,
        'alertas_auditoria_fantasmas': res_eri['fantasmas'][:10], # Top 10
        'criterio_parada_activado': len(propuestas) > 0,
        'mensaje_parada': "EL SISTEMA SE DETUVO: Requiere supervisión humana y aprobación del planeador antes de comprometer compras." if len(propuestas) > 0 else "Operación en parámetros normales."
    }
    
    # 10. Persistir Estado en Capa de Datos
    datos.guardar_propuestas(resultado_consolidado)
    
    return resultado_consolidado

if __name__ == '__main__':
    resultado = ejecutar_orquestacion()
    print("\n=== RESUMEN EJECUTIVO DE LA ORQUESTACIÓN ===")
    print(f"Estado: {resultado['status']}")
    print(f"Indicador ERI: {resultado['kpis']['eri_global_pct']}%")
    print(f"Propuestas de Reorden Crítica: {resultado['kpis']['skus_en_quiebre']} SKUs")
    print(f"Inversión Sugerida: ${resultado['kpis']['inversion_propuesta_cop']:,.2f} COP")
    print(f"Criterio de Parada: {resultado['mensaje_parada']}")
