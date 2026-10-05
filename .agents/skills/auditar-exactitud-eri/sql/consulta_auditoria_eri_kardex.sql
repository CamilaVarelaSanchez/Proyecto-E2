-- ==============================================================================
-- Consulta Analítica: Reconstrucción de Kardex y Auditoría de Exactitud ERI / IRA
-- Base de Datos: Supabase PostgreSQL (E2 SAS)
-- Solución a la Queja 3 de Gerencia: Discrepancias Físico vs. Sistema, Desfase Muelle y Fantasmas
-- ==============================================================================

WITH movimientos_agrupados AS (
    SELECT 
        m.sku,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'entrada' THEN m.cantidad ELSE 0 END), 0) AS total_entradas,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'salida' THEN m.cantidad ELSE 0 END), 0) AS total_salidas,
        COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'ajuste' THEN m.cantidad ELSE 0 END), 0) AS total_ajustes
    FROM public.movimientos_inventario m
    GROUP BY m.sku
),
balance_kardex AS (
    SELECT 
        mm.sku,
        mm.descripcion,
        mm.categoria,
        mm.costo_unitario,
        COALESCE(ii.stock_inicial, 0) AS stock_inicial,
        COALESCE(ma.total_entradas, 0) AS total_entradas,
        COALESCE(ma.total_salidas, 0) AS total_salidas,
        COALESCE(ma.total_ajustes, 0) AS total_ajustes,
        -- Fórmula Canónica del Saldo Teórico:
        (COALESCE(ii.stock_inicial, 0) + COALESCE(ma.total_entradas, 0) - COALESCE(ma.total_salidas, 0) + COALESCE(ma.total_ajustes, 0)) AS saldo_teorico_sistema,
        cf.stock_fisico_contado
    FROM public.maestro_materiales mm
    LEFT JOIN public.inventario_inicial ii ON mm.sku = ii.sku
    LEFT JOIN movimientos_agrupados ma ON mm.sku = ma.sku
    LEFT JOIN public.conteo_fisico cf ON mm.sku = cf.sku
),
calculo_eri AS (
    SELECT 
        b.*,
        (b.saldo_teorico_sistema - COALESCE(b.stock_fisico_contado, 0)) AS discrepancia_neta,
        ABS(b.saldo_teorico_sistema - COALESCE(b.stock_fisico_contado, 0)) AS discrepancia_absoluta,
        (ABS(b.saldo_teorico_sistema - COALESCE(b.stock_fisico_contado, 0)) * b.costo_unitario) AS impacto_financiero_cop,
        CASE 
            WHEN b.stock_fisico_contado IS NULL THEN 'No Auditado en Piso'
            WHEN (ABS(b.saldo_teorico_sistema - b.stock_fisico_contado) <= (0.05 * b.stock_fisico_contado)) 
                 OR (b.saldo_teorico_sistema = b.stock_fisico_contado) THEN 'Concordante (+-5%)'
            WHEN b.saldo_teorico_sistema > b.stock_fisico_contado THEN 'Material Fantasma (Kardex > Fisico)'
            ELSE 'Desfase Muelle / Sobrante Fisico (Fisico > Kardex)'
        END AS diagnostico_eri
    FROM balance_kardex b
)
SELECT 
    sku,
    descripcion,
    categoria,
    costo_unitario,
    stock_inicial,
    total_entradas,
    total_salidas,
    total_ajustes,
    saldo_teorico_sistema,
    stock_fisico_contado,
    discrepancia_neta,
    discrepancia_absoluta,
    ROUND(impacto_financiero_cop::numeric, 2) AS impacto_financiero_cop,
    diagnostico_eri
FROM calculo_eri
ORDER BY impacto_financiero_cop DESC, sku ASC;
