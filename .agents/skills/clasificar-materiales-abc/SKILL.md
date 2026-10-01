---
name: clasificar-materiales-abc
description: Use when asked to classify materials by importance, calculate annual consumption value, perform Pareto ABC segmentation (80-15-5), or analyze material criticality for inventory management.
---

# 📦 Skill: Clasificar Materiales ABC

## 🎯 Cuándo usarla:
**Usar esta skill cuando pidan clasificar materiales por importancia**, jerarquizar insumos por valor económico, calcular la segmentación ABC (Pareto) o definir políticas de control de inventario.

---

## 🛠️ Herramientas Disponibles:
1. **Consultas SQL Directas a Supabase:**
   - Archivo SQL: [`sql/consultas/consulta_clasificacion_abc_materiales.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/sql/consultas/consulta_clasificacion_abc_materiales.sql)
   - Herramienta MCP: `execute_sql` sobre tablas `maestro_materiales`, `plan_produccion`, `bom` y `movimientos_inventario`.
2. **Script Automatizado en Python:**
   - Archivo: [`skill/clasificar-materiales-abc/scripts/clasificar_abc.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/skill/clasificar-materiales-abc/scripts/clasificar_abc.py)
   - Ejecución: `python skill/clasificar-materiales-abc/scripts/clasificar_abc.py`

---

## 📋 Pasos Metodológicos:

### 1. Traer consumo del periodo y costo unitario de cada material
- Extraer `sku`, `descripcion`, `categoria` y `costo_unitario` desde `maestro_materiales`.
- Obtener el consumo total del periodo evaluado:
  - **Vía Explosión BOM:** Consumo planeado = $\sum (Plan_j \times BOM_{j,i})$ anualizado a 12 meses (factor $12/21$).
  - **Vía Kardex Transaccional:** Suma de transacciones donde `tipo_movimiento = 'salida'` anualizado a 12 meses.
- **Excluir materiales duplicados antes de calcular** asegurando unicidad por `sku` (`DISTINCT` / `GROUP BY`).

### 2. Calcular Valor de Consumo
$$\text{Valor de Consumo Anual} = \text{Consumo Anual } (D_i) \times \text{Costo Unitario } (C_{u,i})$$

### 3. Ordenar de mayor a menor y acumular el porcentaje
- Ordenar la tabla de materiales de forma **descendente** por `Valor de Consumo`.
- Calcular la suma acumulada de valor: $\text{Valor Acumulado}_k = \sum_{i=1}^{k} \text{Valor}_i$.
- Calcular el porcentaje acumulado sobre el total general:
$$\% \text{ Valor Acumulado}_k = \left( \frac{\text{Valor Acumulado}_k}{\text{Valor Total General}} \right) \times 100\%$$

### 4. Asignar Clasificación ABC (Regla de Pareto 80-15-5)
- 🔴 **Clase A:** Hasta el **80.0%** acumulado del valor total.
- 🟡 **Clase B:** Desde el 80.01% hasta el **95.0%** acumulado del valor total.
- 🟢 **Clase C:** El resto (desde el 95.01% hasta el **100.0%**).

### 5. Excluir materiales duplicados antes de calcular
- Garantizar que cada SKU se procese exactamente una sola vez agrupando registros maestros y eliminando redundancias previas.

---

## ✅ Cómo Verificar los Resultados:
1. **Suma de Porcentajes:** Los porcentajes acumulados deben llegar exactamente al **100.0%** al final de la tabla.
2. **Distribución de Pareto:** La **Clase A** debe concentrar **pocos materiales** (típicamente entre 5% y 15% de los SKUs) con la **mayor parte del valor financiero** (~80%).
3. **Reporte Obligatorio:** En la salida siempre se debe reportar:
   - Cuántos SKUs pertenecen a cada clase ($A, B, C$).
   - Qué porcentaje de SKUs representa cada clase.
   - Qué monto en dinero (COP) y qué porcentaje del valor total concentra cada clase.
