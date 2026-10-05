-- ==============================================================================
-- Consulta Analítica: Explosión BOM y Parámetros Dinámicos de Reposición (SS, ROP, EOQ)
-- Base de Datos: Supabase PostgreSQL (E2 SAS)
-- Solución a la Queja 4 de Gerencia: Picos de Demanda y Desborde Multiplicativo en Matriz BOM
-- ==============================================================================

WITH explosion_bom AS (
    -- 1. Explosión de Demanda Dependiente: Plan de Producción x Matriz BOM
    SELECT 
        b.sku_material AS sku,
        p.periodo,
        SUM(p.cantidad_planeada * b.cantidad_por_unidad) AS consumo_mensual_planeado
    FROM public.plan_produccion p
    INNER JOIN public.bom b ON p.producto = b.producto
    GROUP BY b.sku_material, p.periodo
),
estadisticas_demanda AS (
    -- 2. Consumo Total Anualizado y Variabilidad Diaria (sigma_diario)
    SELECT 
        sku,
        SUM(consumo_mensual_planeado) * (12.0 / 21.0) AS demanda_anual_d,
        (SUM(consumo_mensual_planeado) * (12.0 / 21.0) / 365.0) AS consumo_diario_d,
        -- Desviación estándar diaria = stddev_mensual / sqrt(30)
        COALESCE(STDDEV_SAMP(consumo_mensual_planeado) / SQRT(30), 0) AS sigma_diario
    FROM explosion_bom
    GROUP BY sku
),
lead_time_real AS (
    -- 3. Lead Time Real Promedio por Categoría desde Órdenes de Compra
    SELECT 
        mm.categoria,
        AVG(EXTRACT(DAY FROM (oc.fecha_recepcion::timestamp - oc.fecha_pedido::timestamp))) AS lead_time_promedio_categoria
    FROM public.ordenes_compra oc
    INNER JOIN public.maestro_materiales mm ON oc.sku = mm.sku
    WHERE oc.fecha_recepcion IS NOT NULL AND oc.fecha_pedido IS NOT NULL
    GROUP BY mm.categoria
),
parametros_base AS (
    -- 4. Parámetros Financieros y Operacionales
    -- Co = $150.000 COP, i = 22% anual, Z = 1.645 (SLA 95% / Riesgo quiebre ~6%)
    SELECT 
        mm.sku,
        mm.descripcion,
        mm.categoria,
        mm.costo_unitario,
        COALESCE(lt.lead_time_promedio_categoria, mm.lead_time_declarado_dias) AS lead_time_dias,
        COALESCE(ed.demanda_anual_d, 0) AS demanda_anual_d,
        COALESCE(ed.consumo_diario_d, 0) AS consumo_diario_d,
        COALESCE(ed.sigma_diario, 0) AS sigma_diario,
        150000.0 AS costo_ordenar_co,
        (mm.costo_unitario * 0.22) AS costo_posesion_cc,
        1.645 AS factor_servicio_z
    FROM public.maestro_materiales mm
    LEFT JOIN estadisticas_demanda ed ON mm.sku = ed.sku
    LEFT JOIN lead_time_real lt ON mm.categoria = lt.categoria
)
-- 5. Cálculo Final de SS, ROP y EOQ
SELECT 
    sku,
    descripcion,
    categoria,
    costo_unitario,
    ROUND(lead_time_dias::numeric, 1) AS lead_time_dias,
    ROUND(demanda_anual_d::numeric, 2) AS demanda_anual_unidades,
    ROUND(consumo_diario_d::numeric, 2) AS consumo_diario_d,
    ROUND(sigma_diario::numeric, 2) AS sigma_diario,
    -- Stock de Seguridad: SS = Z * sigma_d * sqrt(L)
    ROUND((factor_servicio_z * sigma_diario * SQRT(lead_time_dias))::numeric, 0) AS stock_seguridad_ss95,
    -- Punto de Reorden: ROP = (d * L) + SS
    ROUND(((consumo_diario_d * lead_time_dias) + (factor_servicio_z * sigma_diario * SQRT(lead_time_dias)))::numeric, 0) AS punto_reorden_rop,
    -- Lote Económico: EOQ = sqrt((2 * D * Co) / Cc)
    CASE 
        WHEN costo_posesion_cc > 0 AND demanda_anual_d > 0 
        THEN ROUND(SQRT((2.0 * demanda_anual_d * costo_ordenar_co) / costo_posesion_cc)::numeric, 0)
        ELSE 0
    END AS lote_economico_eoq
FROM parametros_base
ORDER BY demanda_anual_d DESC, sku ASC;
