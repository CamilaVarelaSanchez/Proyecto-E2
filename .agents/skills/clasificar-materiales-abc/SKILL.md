---
name: clasificar-materiales-abc
description: Use when asked to classify materials by economic importance, calculate annual consumption value (D * Cu), perform Pareto ABC segmentation (80-15-5), or prioritize inventory control in E2 SAS.
---

# 📦 Skill: Clasificar Materiales ABC

## 1. 🎯 Cuándo usarla:
- Cuando se solicite clasificar los materiales según su importancia económica.
- Cuando se requiera priorizar el control de compras y almacenamiento enfocando el capital en los insumos críticos.
- Cuando se necesite calcular la **Demanda Anualizada por Valor Monetario** ($\text{Valor Anual} = D_i \times C_{u,i}$) y aplicar el principio de Pareto (80-15-5).
- Como insumo previo antes de dimensionar políticas de inventario diferenciadas por tipo de material (SS, ROP, EOQ).

---

## 🛠️ Herramientas Disponibles:
1. **Consulta SQL Directa a Supabase:**
   - Archivo SQL: [`sql/consulta_clasificacion_abc_materiales.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/clasificar-materiales-abc/sql/consulta_clasificacion_abc_materiales.sql)
   - Herramienta MCP: `execute_sql` sobre tablas `maestro_materiales`, `plan_produccion`, `bom` y `movimientos_inventario`.
2. **Script Automatizado en Python:**
   - Archivo: [`scripts/clasificar_abc.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/clasificar-materiales-abc/scripts/clasificar_abc.py)
   - Ejecución: `python .agents/skills/clasificar-materiales-abc/scripts/clasificar_abc.py`

---

## 2. 📋 Pasos Metodológicos:

### Paso 1: Extracción y Consolidación de Datos
- Consultar en Supabase (`maestro_materiales`, `plan_produccion`, `bom`, `movimientos_inventario`) el costo unitario ($C_{u,i}$) y el consumo del periodo de cada SKU.
- Excluir materiales duplicados asegurando unicidad por `sku`.

### Paso 2: Cálculo de la Demanda Anualizada ($D_i$)
- **Vía Plan Maestro $\times$ BOM:**
  $$D_i = \sum_{j} (\text{PlanProduccion}_j \times \text{BOM}_{j,i}) \times \frac{12}{21}$$
- **Vía Kardex Histórico:** Suma de transacciones donde `tipo_movimiento = 'salida'` anualizado (factor $12/21$).

### Paso 3: Cálculo de Demanda Anualizada por Valor
$$\text{Valor Anual}_i = D_i \times C_{u,i}$$

### Paso 4: Ordenamiento y Acumulación
- Ordenar los SKUs de forma descendente según $\text{Valor Anual}_i$.
- Calcular el valor acumulado y el porcentaje acumulado sobre el valor total general:
  $$\% \text{ Valor Acumulado}_k = \left( \frac{\sum_{i=1}^k \text{Valor Anual}_i}{\text{Valor Total General}} \right) \times 100\%$$

### Paso 5: Asignación de Clase ABC (Regla de Pareto 80-15-5)
- 🔴 **Clase A:** Hasta el **80.0%** del valor acumulado.
- 🟡 **Clase B:** Del **80.01% al 95.0%** del valor acumulado.
- 🟢 **Clase C:** Del **95.01% al 100.0%** (incluye "Plata Muerta").

---

## 3. ✅ Cómo Verificar los Resultados:
1. **Cierre del 100%:** El porcentaje acumulado de la última fila debe ser exactamente el **100.0%**.
2. **Distribución de Pareto:** La Clase A debe concentrar una minoría de SKUs (~10% del catálogo) y representar el ~80% del dinero total.
3. **Unicidad:** No deben existir SKUs duplicados en la tabla de salida (conteo total = 420 SKUs).
4. **Reporte Obligatorio de Resumen:** En la salida siempre se debe presentar la tabla consolidada:
   - Cantidad de SKUs por clase ($A, B, C$).
   - Porcentaje de SKUs que representa cada clase.
   - Monto total en COP y porcentaje del valor total por clase.
