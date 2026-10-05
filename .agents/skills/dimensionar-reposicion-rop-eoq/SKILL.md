---
name: dimensionar-reposicion-rop-eoq
description: Use when asked to calculate replenishment parameters, explode BOM recipes against master production schedules, compute dynamic safety stock (SS), reorder point (ROP), or economic order quantity (EOQ) for Complaint 4.
---

# ⚙️ Skill: Dimensionar Reposición ROP y EOQ

## 1. 🎯 Cuándo usarla:
- Cuando se requiera definir con rigor matemático **cuánto pedir ($EOQ$)** y **cuándo pedir ($ROP$)** para evitar quiebres de stock.
- Cuando se presenten picos de producción en Producto Terminado (archivadores/estanterías) y se necesite calcular la **demanda dependiente** a través de la matriz BOM.
- Para calcular el **Stock de Seguridad ($SS$) dinámico** que absorba la volatilidad de la demanda y los tiempos de entrega ($L$).
- Para resolver la Queja 4 de Gerencia sobre desborde multiplicativo en materiales compartidos (láminas, correderas, tornillería).

---

## 🛠️ Herramientas Disponibles:
1. **Consulta SQL Directa a Supabase:**
   - Archivo SQL: [`sql/consulta_parametros_rop_eoq.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/dimensionar-reposicion-rop-eoq/sql/consulta_parametros_rop_eoq.sql)
   - Herramienta MCP: `execute_sql` sobre tablas `plan_produccion`, `bom`, `maestro_materiales` y `ordenes_compra`.
2. **Script Automatizado en Python:**
   - Archivo: [`scripts/dimensionar_reposicion.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/dimensionar-reposicion-rop-eoq/scripts/dimensionar_reposicion.py)
   - Ejecución: `python .agents/skills/dimensionar-reposicion-rop-eoq/scripts/dimensionar_reposicion.py`

---

## 2. 📋 Pasos Metodológicos:

### Paso 1: Explosión Matricial del Plan Maestro sobre la Matriz BOM
Calcular la demanda dependiente de cada insumo multiplicando los volúmenes del plan maestro por los coeficientes de ensamble:
$$D_{\text{bruta}, i} = \sum_{j \in \text{Productos}} \Big( \text{PlanProduccion}_j \times \text{CoeficienteBOM}_{j,i} \Big) \times \frac{12}{21}$$

### Paso 2: Cálculo de Consumo Diario y Variabilidad
- Consumo promedio diario: $d_i = \frac{D_{\text{anual}, i}}{365 \text{ días}}$.
- Desviación estándar del consumo diario ($\sigma_{d,i}$): evaluando la variabilidad de la demanda periódica mensual ($\sigma_{\text{mensual}} / \sqrt{30}$).

### Paso 3: Cálculo del Stock de Seguridad Dinámico ($SS$)
$$SS_i = Z \times \sigma_{d,i} \times \sqrt{L_i}$$
*(donde $Z = 1.645$ para nivel de servicio del 95% / riesgo de quiebre $\le 6\%$, y $L_i$ es el Lead Time real del proveedor en días).*

### Paso 4: Cálculo del Punto de Reorden ($ROP$)
$$ROP_i = (d_i \times L_i) + SS_i$$

### Paso 5: Cálculo del Lote Económico de Compra ($EOQ$)
$$EOQ_i = \sqrt{\frac{2 \times D_i \times C_o}{i \times C_{u,i}}}$$
*(con costo de emisión de orden $C_o = \$150.000\text{ COP}$ y tasa de mantenimiento de inventario $i = 22\%\text{ anual}$).*

---

## 3. ✅ Cómo Verificar los Resultados:
1. **No Negatividad:** Ningún parámetro ($SS, ROP, EOQ$) puede ser negativo ni nulo para insumos con demanda positiva.
2. **Relación Lógica Fundamental:** Siempre se debe cumplir que $ROP_i > SS_i$ para insumos con tiempo de entrega $L_i > 0$.
3. **Amortiguación de Volatilidad:** Materiales con mayor volatilidad de demanda ($\sigma_d$) y mayor Lead Time ($L$) deben presentar proporcionalmente mayores colchones de $SS$.
4. **Resumen de Resultados:** Entregar tabla ordenada por $ROP$ descendente indicando: SKU, descripción, $D_{\text{anual}}$, $SS_{95\%}$, $ROP$, $EOQ$ y Lead Time real.
