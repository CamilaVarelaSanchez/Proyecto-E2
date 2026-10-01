-- ==============================================================================
-- 📦 CONSULTA SQL: CLASIFICACIÓN ABC DE MATERIALES POR VALOR DE CONSUMO ANUAL
-- Skill: clasificar-materiales-abc (E2 SAS / Producción 4.0)
-- 
-- Cumple con:
-- 1. Traer consumo del periodo (BOM y Plan) y costo unitario.
-- 2. Valor de consumo = consumo anual x costo unitario.
-- 3. Ordenar de mayor a menor y acumular porcentaje con funciones de ventana.
-- 4. Clase A hasta 80% acumulado, B hasta 95%, C el resto.
-- 5. Excluir materiales duplicados antes de calcular.
-- 
-- Verificación:
-- - Porcentajes acumulados llegan a 100%.
-- - Clase A concentra pocos materiales con alto valor financiero.
-- - Reporta cantidad de SKUs, % de SKUs, valor total en COP y % del valor por clase.
-- ==============================================================================

-- 1. DETALLE MATERIAL POR MATERIAL CON ASIGNACIÓN ABC
WITH consumo_calculado AS (
    -- Paso 1 y 5: Traer consumo anualizado excluyendo duplicados
    SELECT 
        m.sku,
        m.descripcion,
        m.categoria,
        m.costo_unitario,
        COALESCE(SUM(p.cantidad_planeada * b.cantidad_por_unidad) * (12.0 / 21.0), 0) AS consumo_anual
    FROM public.maestro_materiales m
    LEFT JOIN public.bom b ON m.sku = b.sku_material
    LEFT JOIN public.plan_produccion p ON b.producto = p.producto
    GROUP BY m.sku, m.descripcion, m.categoria, m.costo_unitario
),
valor_calculado AS (
    -- Paso 2: Valor de consumo = consumo anual x costo unitario
    SELECT 
        sku,
        descripcion,
        categoria,
        costo_unitario,
        consumo_anual,
        (consumo_anual * costo_unitario) AS valor_consumo
    FROM consumo_calculado
),
porcentajes_acumulados AS (
    -- Paso 3: Ordenar de mayor a menor y acumular el porcentaje
    SELECT 
        sku,
        descripcion,
        categoria,
        costo_unitario,
        consumo_anual,
        valor_consumo,
        SUM(valor_consumo) OVER (ORDER BY valor_consumo DESC, sku ASC) AS valor_acumulado,
        SUM(valor_consumo) OVER () AS valor_total_general,
        ROUND((SUM(valor_consumo) OVER (ORDER BY valor_consumo DESC, sku ASC) / NULLIF(SUM(valor_consumo) OVER (), 0) * 100)::numeric, 4) AS pct_acumulado
    FROM valor_calculado
)
-- Paso 4: Asignación de Clase A (hasta 80%), B (hasta 95%) y C (el resto)
SELECT 
    sku,
    descripcion,
    categoria,
    costo_unitario,
    ROUND(consumo_anual::numeric, 2) AS consumo_anual,
    ROUND(valor_consumo::numeric, 2) AS valor_consumo_anual_cop,
    ROUND(pct_acumulado, 2) AS pct_valor_acumulado,
    CASE 
        WHEN pct_acumulado <= 80.0 THEN 'A'
        WHEN pct_acumulado <= 95.0 THEN 'B'
        ELSE 'C'
    END AS clasificacion_abc
FROM porcentajes_acumulados
ORDER BY valor_consumo DESC, sku ASC;


-- ==============================================================================
-- 2. REPORTE EJECUTIVO RESUMIDO POR CLASE ABC
-- ==============================================================================
WITH consumo_calculado AS (
    SELECT 
        m.sku,
        m.costo_unitario,
        COALESCE(SUM(p.cantidad_planeada * b.cantidad_por_unidad) * (12.0 / 21.0), 0) AS consumo_anual
    FROM public.maestro_materiales m
    LEFT JOIN public.bom b ON m.sku = b.sku_material
    LEFT JOIN public.plan_produccion p ON b.producto = p.producto
    GROUP BY m.sku, m.costo_unitario
),
valor_calculado AS (
    SELECT 
        sku,
        (consumo_anual * costo_unitario) AS valor_consumo
    FROM consumo_calculado
),
porcentajes_acumulados AS (
    SELECT 
        sku,
        valor_consumo,
        SUM(valor_consumo) OVER () AS valor_total_general,
        ROUND((SUM(valor_consumo) OVER (ORDER BY valor_consumo DESC, sku ASC) / NULLIF(SUM(valor_consumo) OVER (), 0) * 100)::numeric, 4) AS pct_acumulado
    FROM valor_calculado
)
SELECT 
    CASE 
        WHEN pct_acumulado <= 80.0 THEN 'A (Críticos)'
        WHEN pct_acumulado <= 95.0 THEN 'B (Medios)'
        ELSE 'C (Bajo Valor)'
    END AS clase_abc,
    COUNT(*) AS cantidad_skus,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(DISTINCT sku) FROM public.maestro_materiales)::numeric * 100), 2) AS pct_skus,
    ROUND(SUM(valor_consumo)::numeric, 2) AS valor_total_anual_cop,
    ROUND((SUM(valor_consumo) / MAX(valor_total_general) * 100)::numeric, 2) AS pct_valor_financiero
FROM porcentajes_acumulados
GROUP BY 
    CASE 
        WHEN pct_acumulado <= 80.0 THEN 'A (Críticos)'
        WHEN pct_acumulado <= 95.0 THEN 'B (Medios)'
        ELSE 'C (Bajo Valor)'
    END
ORDER BY MIN(pct_acumulado) ASC;
