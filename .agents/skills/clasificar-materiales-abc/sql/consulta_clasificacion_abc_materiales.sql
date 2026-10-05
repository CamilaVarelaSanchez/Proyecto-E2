-- ==============================================================================
-- Consulta Analítica: Clasificación ABC de Materiales por Demanda Anualizada por Valor
-- Base de Datos: Supabase PostgreSQL (E2 SAS)
-- Principio: Pareto 80-15-5 sobre Demanda Anualizada en Valor Monetario (D_i * Cu_i)
-- ==============================================================================

WITH consumo_planeado AS (
    -- 1. Explosión de Demanda Dependiente: Plan de Producción x Matriz BOM
    -- Anualizado de 21 meses a 12 meses (factor 12.0 / 21.0)
    SELECT 
        b.sku_material AS sku,
        SUM(p.cantidad_planeada * b.cantidad_por_unidad) * (12.0 / 21.0) AS demanda_anual_planeada
    FROM public.plan_produccion p
    INNER JOIN public.bom b ON p.producto = b.producto
    GROUP BY b.sku_material
),
consumo_kardex AS (
    -- 2. Demanda Real Histórica Vía Salidas de Kardex (Anualizado 12/21)
    SELECT 
        m.sku,
        SUM(m.cantidad) * (12.0 / 21.0) AS salidas_anuales_kardex
    FROM public.movimientos_inventario m
    WHERE LOWER(m.tipo_movimiento) = 'salida'
    GROUP BY m.sku
),
valorizacion AS (
    -- 3. Cálculo de la Demanda Anualizada por Valor Monetario (D_i * Cu_i)
    SELECT 
        mm.sku,
        mm.descripcion,
        mm.categoria,
        mm.costo_unitario,
        COALESCE(cp.demanda_anual_planeada, 0) AS demanda_anual,
        (COALESCE(cp.demanda_anual_planeada, 0) * mm.costo_unitario) AS valor_consumo_anual,
        COALESCE(ck.salidas_anuales_kardex, 0) AS salidas_anuales_reales
    FROM public.maestro_materiales mm
    LEFT JOIN consumo_planeado cp ON mm.sku = cp.sku
    LEFT JOIN consumo_kardex ck ON mm.sku = ck.sku
),
acumulados AS (
    -- 4. Ordenamiento Descendente y Cálculo de Porcentajes Acumulados
    SELECT 
        v.*,
        SUM(v.valor_consumo_anual) OVER (ORDER BY v.valor_consumo_anual DESC, v.sku ASC) AS valor_acumulado,
        SUM(v.valor_consumo_anual) OVER () AS valor_total_empresa,
        ROW_NUMBER() OVER (ORDER BY v.valor_consumo_anual DESC, v.sku ASC) AS ranking_sku,
        COUNT(*) OVER () AS total_skus
    FROM valorizacion v
)
-- 5. Asignación de Clasificación ABC (Regla Pareto 80-15-5)
SELECT 
    sku,
    descripcion,
    categoria,
    costo_unitario,
    ROUND(demanda_anual::numeric, 2) AS demanda_anual_unidades,
    ROUND(valor_consumo_anual::numeric, 2) AS valor_consumo_anual_cop,
    ROUND((valor_acumulado / NULLIF(valor_total_empresa, 0) * 100)::numeric, 4) AS pct_valor_acumulado,
    ROUND((ranking_sku::numeric / total_skus * 100)::numeric, 2) AS pct_sku_acumulado,
    CASE 
        WHEN (valor_acumulado / NULLIF(valor_total_empresa, 0) * 100) <= 80.0 THEN 'A'
        WHEN (valor_acumulado / NULLIF(valor_total_empresa, 0) * 100) <= 95.0 THEN 'B'
        ELSE 'C'
    END AS clasificacion_abc
FROM acumulados
ORDER BY valor_consumo_anual DESC, sku ASC;
