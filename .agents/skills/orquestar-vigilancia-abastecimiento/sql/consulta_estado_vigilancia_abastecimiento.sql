-- ==============================================================================
-- Consulta Analítica: Estado Integral de Vigilancia de Abastecimiento (Capa 3 - Orquestación)
-- Base de Datos: Supabase PostgreSQL (E2 SAS)
-- Cruce Multivariable: Stock Físico Real vs ROP, Pareto ABC por Valor, ERI y Órdenes en Tránsito
-- ==============================================================================

WITH base_abc AS (
    -- 1. Clasificación ABC por Demanda Anualizada por Valor
    SELECT 
        b.sku_material AS sku,
        SUM(p.cantidad_planeada * b.cantidad_por_unidad) * (12.0 / 21.0) AS demanda_anual_d,
        (SUM(p.cantidad_planeada * b.cantidad_por_unidad) * (12.0 / 21.0) / 365.0) AS consumo_diario_d,
        COALESCE(STDDEV_SAMP(p.cantidad_planeada * b.cantidad_por_unidad) / SQRT(30), 0) AS sigma_diario
    FROM public.plan_produccion p
    INNER JOIN public.bom b ON p.producto = b.producto
    GROUP BY b.sku_material
),
lead_times AS (
    -- 2. Lead Time Real por Categoría
    SELECT 
        mm.categoria,
        AVG(EXTRACT(DAY FROM (oc.fecha_recepcion::timestamp - oc.fecha_pedido::timestamp))) AS lead_time_promedio_categoria
    FROM public.ordenes_compra oc
    INNER JOIN public.maestro_materiales mm ON oc.sku = mm.sku
    WHERE oc.fecha_recepcion IS NOT NULL AND oc.fecha_pedido IS NOT NULL
    GROUP BY mm.categoria
),
kardex_saldo AS (
    -- 3. Saldo Teórico del Kardex
    SELECT 
        m.sku,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'entrada' THEN m.cantidad ELSE 0 END), 0) AS total_entradas,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'salida' THEN m.cantidad ELSE 0 END), 0) AS total_salidas,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'ajuste' THEN m.cantidad ELSE 0 END), 0) AS total_ajustes
    FROM public.movimientos_inventario m
    GROUP BY m.sku
),
ordenes_transito AS (
    -- 4. Órdenes de Compra en Tránsito (Sin recepción asentada)
    SELECT 
        oc.sku,
        COUNT(oc.id_orden) AS ocs_abiertas,
        SUM(oc.cantidad_pedida) AS cantidad_en_transito
    FROM public.ordenes_compra oc
    WHERE oc.fecha_recepcion IS NULL OR oc.estado = 'pendiente'
    GROUP BY oc.sku
),
consolidado AS (
    SELECT 
        mm.sku,
        mm.descripcion,
        mm.categoria,
        mm.costo_unitario,
        COALESCE(lt.lead_time_promedio_categoria, mm.lead_time_declarado_dias) AS lead_time_dias,
        COALESCE(cf.stock_fisico_contado, 0) AS stock_fisico_real,
        (COALESCE(ii.stock_inicial, 0) + COALESCE(ks.total_entradas, 0) - COALESCE(ks.total_salidas, 0) + COALESCE(ks.total_ajustes, 0)) AS saldo_teorico_kardex,
        COALESCE(abc.demanda_anual_d, 0) AS demanda_anual_d,
        COALESCE(abc.consumo_diario_d, 0) AS consumo_diario_d,
        COALESCE(abc.sigma_diario, 0) AS sigma_diario,
        COALESCE(ot.cantidad_en_transito, 0) AS stock_en_transito
    FROM public.maestro_materiales mm
    LEFT JOIN public.inventario_inicial ii ON mm.sku = ii.sku
    LEFT JOIN public.conteo_fisico cf ON mm.sku = cf.sku
    LEFT JOIN kardex_saldo ks ON mm.sku = ks.sku
    LEFT JOIN base_abc abc ON mm.sku = abc.sku
    LEFT JOIN lead_times lt ON mm.categoria = lt.categoria
    LEFT JOIN ordenes_transito ot ON mm.sku = ot.sku
),
calculos_finales AS (
    SELECT 
        c.*,
        (c.demanda_anual_d * c.costo_unitario) AS valor_consumo_anual,
        ROUND((1.645 * c.sigma_diario * SQRT(c.lead_time_dias))::numeric, 0) AS stock_seguridad_ss,
        ROUND(((c.consumo_diario_d * c.lead_time_dias) + (1.645 * c.sigma_diario * SQRT(c.lead_time_dias)))::numeric, 0) AS punto_reorden_rop,
        CASE 
            WHEN (c.costo_unitario * 0.22) > 0 AND c.demanda_anual_d > 0 
            THEN ROUND(SQRT((2.0 * c.demanda_anual_d * 150000.0) / (c.costo_unitario * 0.22))::numeric, 0)
            ELSE 0
        END AS lote_optimo_eoq,
        SUM(c.demanda_anual_d * c.costo_unitario) OVER (ORDER BY (c.demanda_anual_d * c.costo_unitario) DESC, c.sku ASC) AS valor_acumulado,
        SUM(c.demanda_anual_d * c.costo_unitario) OVER () AS valor_total_empresa
    FROM consolidado c
)
SELECT 
    sku,
    descripcion,
    categoria,
    costo_unitario,
    stock_fisico_real,
    saldo_teorico_kardex,
    stock_en_transito,
    stock_seguridad_ss,
    punto_reorden_rop,
    lote_optimo_eoq,
    CASE 
        WHEN (valor_acumulado / NULLIF(valor_total_empresa, 0) * 100) <= 80.0 THEN 'A'
        WHEN (valor_acumulado / NULLIF(valor_total_empresa, 0) * 100) <= 95.0 THEN 'B'
        ELSE 'C'
    END AS clase_abc,
    CASE 
        WHEN stock_fisico_real <= punto_reorden_rop AND stock_en_transito = 0 THEN '🔴 ALERTA ROJA: Quiebre Inminente (Emitir OC)'
        WHEN stock_fisico_real <= punto_reorden_rop AND stock_en_transito > 0 THEN '🟡 ALERTA AMARILLA: Bajo ROP con OC en Tránsito'
        WHEN ABS(saldo_teorico_kardex - stock_fisico_real) > (0.05 * NULLIF(stock_fisico_real, 0)) THEN '🟠 ALERTA AUDITORÍA: Descuadre ERI > 5%'
        ELSE '🟢 ESTADO NORMAL: Operación Saludable'
    END AS estado_operativo
FROM calculos_finales
ORDER BY 
    CASE 
        WHEN stock_fisico_real <= punto_reorden_rop AND stock_en_transito = 0 THEN 1
        WHEN stock_fisico_real <= punto_reorden_rop AND stock_en_transito > 0 THEN 2
        WHEN ABS(saldo_teorico_kardex - stock_fisico_real) > (0.05 * NULLIF(stock_fisico_real, 0)) THEN 3
        ELSE 4
    END,
    costo_unitario DESC,
    sku ASC;
