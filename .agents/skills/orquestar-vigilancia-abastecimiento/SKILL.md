---
name: orquestar-vigilancia-abastecimiento
description: Use when asked to perform end-to-end inventory monitoring, check stockout conditions (Stock <= ROP), audit cross-variable supply chain risks, or generate justified purchase order recommendations in natural language.
---

# 🤖 Skill: Orquestar Vigilancia de Abastecimiento

## 1. 🎯 Cuándo usarla:
- Cuando el usuario o la gerencia soliciten un diagnóstico integral del estado actual del almacén de materias primas.
- Para ejecutar la rutina automática de supervisión continua y detección de riesgos inminentes de quiebre de stock.
- Cuando se requiera emitir **recomendaciones de Órdenes de Compra formalmente justificadas en lenguaje natural** para el departamento de Compras.
- Para consolidar en un solo dictamen la salud del inventario cruzando saldos reales, parámetros $ROP/EOQ$, clasificación ABC y confiabilidad ERI.

---

## 🛠️ Herramientas Disponibles:
1. **Consulta SQL Directa a Supabase:**
   - Archivo SQL: [`sql/consulta_estado_vigilancia_abastecimiento.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/orquestar-vigilancia-abastecimiento/sql/consulta_estado_vigilancia_abastecimiento.sql)
   - Herramienta MCP: `execute_sql` cruzando todas las tablas canónicas del sistema.
2. **Script de Orquestación en Python:**
   - Archivo: [`scripts/orquestar_alertas.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/orquestar-vigilancia-abastecimiento/scripts/orquestar_alertas.py)
   - Ejecución: `python .agents/skills/orquestar-vigilancia-abastecimiento/scripts/orquestar_alertas.py`

---

## 2. 📋 Pasos Metodológicos:

### Paso 1: Invocación y Consolidación de Capas Lógicas
- Obtener el **Stock Físico Real** verificado desde `conteo_fisico` y el saldo formal del Kardex (`auditar-exactitud-eri`).
- Obtener los parámetros dinámicos de reposición: $SS_{95\%}$, $ROP$ y tamaño óptimo de lote $EOQ$ (`dimensionar-reposicion-rop-eoq`).
- Obtener la criticidad económica de cada material según su clase ABC por valor (`clasificar-materiales-abc`).
- Consultar las órdenes de compra en tránsito abiertas en `ordenes_compra`.

### Paso 2: Evaluación de Reglas de Disparo Operacional
- 🔴 **Condición Crítica de Quiebre:** $\text{Stock Real}_i \le ROP_i$ y $\text{Stock en Tránsito}_i = 0$.
- 🟡 **Advertencia en Tránsito:** $\text{Stock Real}_i \le ROP_i$ pero ya existe una OC emitida que cubre la brecha.
- 🟠 **Alerta de Auditoría ERI:** Descrepancia Kardex vs Físico $> \pm 5\%$ en materiales Clase A o B.
- 🟢 **Operación Saludable:** Stock por encima de $ROP$ y sin descuadres de auditoría.

### Paso 3: Redacción de Justificaciones en Lenguaje Natural (LLM)
Para cada material en alerta crítica de reorden, estructurar la recomendación ejecutiva:
> *"Se sugiere emitir Orden de Compra por **{EOQ}** unidades del SKU **{sku}** (**{descripcion}**), debido a que el stock físico disponible (**{stock_real}**) perforó el Punto de Reorden (**{ROP}**) ante la demanda anualizada de **{demanda_anual}** unidades. Insumo catalogado como **Clase {clase_abc}**."*

### Paso 4: Construcción del Payload Estructurado
Generar salida JSON y reporte ejecutivo priorizando materiales Clase A de mayor valor de inversión.

---

## 3. ✅ Cómo Verificar los Resultados:
1. **Cero Alucinaciones:** Todas las cantidades recomendadas ($EOQ$), puntos de reorden ($ROP$) y saldos reportados deben ser idénticos a las salidas de los modelos matemáticos determinísticos.
2. **Priorización por Criticidad:** Las alertas de materiales **Clase A** deben encabezar la lista de acciones inmediatas.
3. **Control de Duplicidad:** Si un material ya cuenta con una orden de compra en tránsito suficiente, no se debe generar una recomendación redundante de compra.
