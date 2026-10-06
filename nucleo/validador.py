"""
Módulo del Núcleo: VALIDADOR (Capa 0 - Sanidad y Calidad de Datos)
Responsabilidad Única: Validar integridad referencial 3FN, no nulos y unicidad antes de ejecutar cálculos.
Contrato:
  - verificar_sanidad(estado) -> dict: {'valido': bool, 'hallazgos': list, 'total_skus': int}
"""

def verificar_sanidad(estado):
    """
    Evalúa la higiene de las tablas canónicas cargadas.
    Si hay una falla catastrófica (ej. SKUs duplicados en maestro), detiene el flujo.
    """
    hallazgos = []
    
    mm = estado.get('maestro_materiales')
    if mm is None or len(mm) == 0:
        return {'valido': False, 'hallazgos': ['Tabla maestro_materiales vacía o ausente.'], 'total_skus': 0}
        
    # 1. Chequeo de duplicados en SKU
    duplicados = mm[mm.duplicated(subset=['sku'], keep=False)]
    if len(duplicados) > 0:
        hallazgos.append(f"Se encontraron {len(duplicados)} SKUs duplicados en maestro_materiales.")
        
    # 2. Chequeo de costos nulos o negativos
    costos_invalidos = mm[mm['costo_unitario'].isna() | (mm['costo_unitario'] <= 0)]
    if len(costos_invalidos) > 0:
        hallazgos.append(f"Se encontraron {len(costos_invalidos)} materiales con costo unitario nulo o inválido.")
        
    # 3. Chequeo de integridad en BOM y Movimientos
    skus_maestro = set(mm['sku'].unique())
    
    bom = estado.get('bom')
    if bom is not None:
        huerfanos_bom = set(bom['sku_material'].unique()) - skus_maestro
        if len(huerfanos_bom) > 0:
            hallazgos.append(f"Hay {len(huerfanos_bom)} materiales en BOM no registrados en maestro_materiales.")
            
    mov = estado.get('movimientos_inventario')
    if mov is not None:
        huerfanos_mov = set(mov['sku'].unique()) - skus_maestro
        if len(huerfanos_mov) > 0:
            hallazgos.append(f"Hay {len(huerfanos_mov)} SKUs en movimientos_inventario no registrados en maestro.")
            
    valido = len(hallazgos) == 0
    return {
        'valido': valido,
        'hallazgos': hallazgos,
        'total_skus': len(mm)
    }
