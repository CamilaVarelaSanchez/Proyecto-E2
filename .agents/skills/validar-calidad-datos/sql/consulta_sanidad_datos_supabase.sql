-- ==============================================================================
-- Consulta Analítica: Diagnóstico de Sanidad e Integridad de Datos en Supabase
-- Base de Datos: Supabase PostgreSQL (E2 SAS) - Capa 0
-- Auditoría de: Nulos Críticos, Llaves Foráneas Rotas, Duplicados e Inconsistencias
-- ==============================================================================

-- 1. Auditoría de Claves Primarias y Duplicados en Maestros
SELECT 
    'maestro_materiales' AS tabla,
    'Duplicados en SKU' AS tipo_verificacion,
    sku AS identificador,
    COUNT(*) AS ocurrencias
FROM public.maestro_materiales
GROUP BY sku
HAVING COUNT(*) > 1

UNION ALL

-- 2. Auditoría de Registros Huérfanos en Movimientos de Inventario
SELECT 
    'movimientos_inventario' AS tabla,
    'SKU Huerfano (No existe en maestro_materiales)' AS tipo_verificacion,
    m.sku AS identificador,
    COUNT(*) AS ocurrencias
FROM public.movimientos_inventario m
LEFT JOIN public.maestro_materiales mm ON m.sku = mm.sku
WHERE mm.sku IS NULL
GROUP BY m.sku

UNION ALL

-- 3. Auditoría de Registros Huérfanos en Conteo Físico
SELECT 
    'conteo_fisico' AS tabla,
    'SKU Huerfano (No existe en maestro_materiales)' AS tipo_verificacion,
    cf.sku AS identificador,
    COUNT(*) AS ocurrencias
FROM public.conteo_fisico cf
LEFT JOIN public.maestro_materiales mm ON cf.sku = mm.sku
WHERE mm.sku IS NULL
GROUP BY cf.sku

UNION ALL

-- 4. Auditoría de Recetas BOM Huérfanas de Material
SELECT 
    'bom' AS tabla,
    'Insumo BOM no existe en maestro_materiales' AS tipo_verificacion,
    b.sku_material AS identificador,
    COUNT(*) AS ocurrencias
FROM public.bom b
LEFT JOIN public.maestro_materiales mm ON b.sku_material = mm.sku
WHERE mm.sku IS NULL
GROUP BY b.sku_material

UNION ALL

-- 5. Auditoría de Nulos o Valores Negativos en Costos Unitarios
SELECT 
    'maestro_materiales' AS tabla,
    'Costo Unitario Nulo o Invalido' AS tipo_verificacion,
    sku AS identificador,
    COUNT(*) AS ocurrencias
FROM public.maestro_materiales
WHERE costo_unitario IS NULL OR costo_unitario <= 0
GROUP BY sku;
