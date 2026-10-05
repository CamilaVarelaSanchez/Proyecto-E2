---
name: validar-calidad-datos
description: Use when asked to validate dataset hygiene, verify 3NF relational integrity, detect nulls or orphaned SKUs, audit database constraints, or ensure data sanitization in Supabase (Layer 0).
---

# 🧹 Skill: Validar Calidad de Datos

## 1. 🎯 Cuándo usarla:
- Antes de procesar cualquier cálculo determinístico cuando se carguen nuevos datos crudos o se actualicen tablas en Supabase.
- Cuando se sospeche de registros huérfanos, llaves foráneas rotas, duplicados en maestros o valores nulos en costos.
- Para auditar y garantizar la sanidad del esquema relacional en Tercera Forma Normal (3FN).

---

## 🛠️ Herramientas Disponibles:
1. **Consulta SQL Directa a Supabase:**
   - Archivo SQL: [`sql/consulta_sanidad_datos_supabase.sql`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/validar-calidad-datos/sql/consulta_sanidad_datos_supabase.sql)
   - Herramienta MCP: `execute_sql` ejecutando uniones de auditoría de llaves foráneas.
2. **Script de Verificación en Python:**
   - Archivo: [`scripts/validar_datos.py`](file:///c:/Users/Laptop%20-%20Camila/OneDrive/Documentos/Proyecto%20E2/.agents/skills/validar-calidad-datos/scripts/validar_datos.py)
   - Ejecución: `python .agents/skills/validar-calidad-datos/scripts/validar_datos.py`

---

## 2. 📋 Pasos Metodológicos:

### Paso 1: Auditoría de Llaves Primarias y Duplicados
Verificar unicidad estricta de `sku` en `maestro_materiales`, `id_producto` en `maestro_productos` y de la clave compuesta `(producto, sku_material)` en la tabla `bom`.

### Paso 2: Auditoría de Integridad Referencial
Comprobar que el 100% de los identificadores `sku` presentes en `movimientos_inventario`, `conteo_fisico`, `ordenes_compra` y `bom` existan previamente en `maestro_materiales`.

### Paso 3: Auditoría de Valores Nulos y Tipos de Datos
Detectar la presencia de campos nulos o inconsistentes en variables críticas:
- `costo_unitario > 0`
- `lead_time_declarado_dias >= 0`
- `cantidad > 0` en movimientos y transacciones.

### Paso 4: Verificación de Consistencia Cronológica
Validar que las fechas de recepción de órdenes de compra correspondan a fechas posteriores a la fecha de emisión del pedido (`fecha_recepcion >= fecha_pedido`).

---

## 3. ✅ Cómo Verificar los Resultados:
1. **Matriz de Cero Inconsistencias:** El reporte de auditoría debe arrojar **$0$ llaves rotas**, **$0$ registros huérfanos** y **$0$ duplicados**.
2. **Trazabilidad de Reglas de Negocio:** Todo campo corregido o imputado debe constar en la bitácora de saneamiento.
3. **Confirmación Previa:** Confirmar que todas las tablas canónicas en Supabase responden con códigos de estado exitosos antes de correr los módulos de optimización.
