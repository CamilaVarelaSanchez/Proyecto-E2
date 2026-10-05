---
name: auditar-exactitud-eri
description: Use when asked to audit inventory record accuracy (ERI / IRA), calculate Kardex theoretical balances, identify ghost materials (phantom inventory), diagnose receiving dock lag discrepancies, or resolve Complaint 3.
---

# 🔍 Skill: Auditar Exactitud ERI

## 1. 🎯 Cuándo usarla:
- Cuando la gerencia o auditoría pregunte por la confiabilidad del inventario o el indicador **ERI / IRA (Exactitud de Registro de Inventario)**.
- Cuando se sospeche de **"materiales fantasmas"** (el sistema dice que hay pero la bodega física está vacía, con riesgo de parada de planta).
- Cuando se presenten saldos negativos en Kardex causados por desfases en el muelle de recepción (órdenes de compra recibidas físicamente pero no cargadas al sistema).
- Para contrastar y conciliar el saldo teórico del Kardex contra el conteo físico real de bodega.

---

## 🛠️ Herramientas Disponibles:
1. **Consulta SQL Directa a Supabase:**
   - Archivo SQL: [`sql/consulta_auditoria_eri_kardex.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/auditar-exactitud-eri/sql/consulta_auditoria_eri_kardex.sql)
   - Herramienta MCP: `execute_sql` sobre `maestro_materiales`, `inventario_inicial`, `movimientos_inventario` y `conteo_fisico`.
2. **Script Automatizado en Python:**
   - Archivo: [`scripts/auditar_eri.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/auditar-exactitud-eri/scripts/auditar_eri.py)
   - Ejecución: `python .agents/skills/auditar-exactitud-eri/scripts/auditar_eri.py`

---

## 2. 📋 Pasos Metodológicos:

### Paso 1: Reconstrucción del Saldo Teórico del Kardex
Consultar `inventario_inicial` y agrupar transacciones de `movimientos_inventario` por `sku`:
$$\text{Saldo Teórico}_i = \text{Inventario Inicial}_i + \sum \text{Entradas}_i - \sum \text{Salidas}_i \pm \sum \text{Ajustes}_i$$

### Paso 2: Cruce contra Auditoría Física en Piso
Vincular con la tabla `conteo_fisico` a través del `sku` para obtener el `stock_fisico_contado`.

### Paso 3: Cálculo de Discrepancias y Tolerancia ($\pm 5\%$)
- Discrepancia absoluta: $\Delta_i = |\text{Saldo Teórico}_i - \text{Conteo Físico}_i|$.
- Condición de concordancia:
  $$\text{Concordante}_i = \begin{cases} \text{VERDADERO} & \text{si } \Delta_i \le 0.05 \times \text{Conteo Físico}_i \text{ o } \Delta_i = 0 \\ \text{FALSO} & \text{en otro caso} \end{cases}$$

### Paso 4: Cálculo del Indicador ERI Global
$$\text{ERI}_{\pm 5\%} = \left( \frac{\text{Número de SKUs concordantes dentro de tolerancia}}{\text{Total de SKUs auditados}} \right) \times 100\%$$

### Paso 5: Tipificación de Fallas e Impacto Financiero
- **Material Fantasma:** $\text{Saldo Teórico} > \text{Conteo Físico}$ (El sistema sobrestima el stock disponible; riesgo inminente de parada de ensamble).
- **Desfase de Muelle / Sobrante Físico:** $\text{Conteo Físico} > \text{Saldo Teórico}$ (El sistema subestima el stock por demoras en asentar recepciones de órdenes de compra).
- **Impacto Financiero:** $\text{Impacto COP}_i = \Delta_i \times C_{u,i}$.

---

## 3. ✅ Cómo Verificar los Resultados:
1. **Consistencia Matemática:** Todo SKU auditado debe clasificarse exactamente en: *Concordante ($\pm 5\%$)*, *Material Fantasma* o *Desfase de Muelle*.
2. **Score ERI Cuantificado:** El ERI debe coincidir con las referencias empíricas de la línea base (ERI $\pm 5\% \approx 70.71\%$ global, o $0\%$ en insumos activos de ensamble sin tolerancia).
3. **Impacto Financiero Total:** Cuantificar el monto total en COP de los faltantes y sobrantes.
4. **Top de Alertas Críticas:** Listar el Top 10 de materiales fantasmas más costosos indicando SKU, descripción, faltante físico y valor en COP.
