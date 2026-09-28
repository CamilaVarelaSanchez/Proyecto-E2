# 🏢 Informe Final Consolidado de Diagnóstico Operacional y Línea Base — E2 SAS

> **Proyecto de Consultoría Analítica y Modelado de Operaciones**  
> **Universidad de Medellín — Facultad de Ingenierías — Ingeniería Industrial**  
> **Asignatura:** Producción 4.0 / Énfasis 2  
> **Fase:** Primera Entrega — E1 (Diagnóstico y Línea Base)  
> **Cliente:** E2 SAS — Mobiliario Metálico para Oficina  
> **Horizonte de Auditoría:** 21 meses de operación transaccional (Julio 2024 – Marzo 2026)  
> **Repositorio Oficial:** [`https://github.com/juliancarmotrice-star/-Enfasis-2.git`](https://github.com/juliancarmotrice-star/-Enfasis-2.git)  
> **Estado de la Entrega:** 🟢 **100% Saneada, Modelada, Diagnosticada y Certificada**

---

## 📌 Tabla de Contenido
1. [1. Resumen Ejecutivo y Marco de la Consultoría](#1-resumen-ejecutivo-y-marco-de-la-consultoría)
2. [2. Arquitectura de Datos, Normalización (3FN) y Calidad](#2-arquitectura-de-datos-normalización-3fn-y-calidad)
   - [2.1 Modelo Relacional en Supabase (PostgreSQL)](#21-modelo-relacional-en-supabase-postgresql)
   - [2.2 Pipeline de Limpieza Reproducible y Tratamiento de Defectos](#22-pipeline-de-limpieza-reproducible-y-tratamiento-de-defectos)
3. [3. Diagnóstico AS-IS y Validación Pericial de las 4 Quejas de Gerencia](#3-diagnóstico-as-is-y-validación-pericial-de-las-4-quejas-de-gerencia)
   - [3.1 Queja 1: Desabastecimiento de Lámina, Cuello de Botella de Lead Time y la Pista del Vidrio](#31-queja-1-desabastecimiento-de-lámina-cuello-de-botella-de-lead-time-y-la-pista-del-vidrio)
   - [3.2 Queja 2: Exceso de Inventario y "Plata Muerta"](#32-queja-2-exceso-de-inventario-y-plata-muerta)
   - [3.3 Queja 3: Inexactitud del Registro (Indicador ERI), Referencias Fantasmas y Sistema Paralelo](#33-queja-3-inexactitud-del-registro-indicador-eri-referencias-fantasmas-y-sistema-paralelo)
   - [3.4 Queja 4: Picos de Demanda en Archivadores/Estanterías y Desborde BOM](#34-queja-4-picos-de-demanda-en-archivadoresestanterías-y-desborde-bom)
4. [4. Modelado Cuantitativo de Inventarios: Demanda Dependiente, ABC, EOQ y ROP](#4-modelado-cuantitativo-de-inventarios-demanda-dependiente-abc-eoq-y-rop)
   - [4.1 Demanda Independiente (PT) vs. Demanda Dependiente de Materiales (Plan × BOM)](#41-demanda-independiente-pt-vs-demanda-dependiente-de-materiales-plan--bom)
   - [4.2 Clasificación ABC Estricta por Valor de Consumo Anual (Consumo × Precio Unitario)](#42-clasificación-abc-estricta-por-valor-de-consumo-anual-consumo--precio-unitario)
   - [4.3 Modelado de Reposición: EOQ Básico, Stock de Seguridad (Z=95%, SLA 6%) y ROP](#43-modelado-de-reposición-eoq-básico-stock-de-seguridad-z95-sla-6-y-rop)
5. [5. Scorecard Maestro de Línea Base y Cuantificación Financiera](#5-scorecard-maestro-de-línea-base-y-cuantificación-financiera)
6. [6. Especificación Preliminar de la Solución TO-BE](#6-especificación-preliminar-de-la-solución-to-be)
7. [7. Respuestas a las Preguntas Clave de Sustentación (Universidad de Medellín)](#7-respuestas-a-las-preguntas-clave-de-sustentación-universidad-de-medellín)
8. [8. Índice de Artefactos e Informes Técnicos del Repositorio](#8-índice-de-artefactos-e-informes-técnicos-del-repositorio)

---

## 1. Resumen Ejecutivo y Marco de la Consultoría

**E2 SAS** es una empresa manufacturera colombiana con más de una década de trayectoria en el diseño, ensamble y comercialización de mobiliario metálico para oficina (escritorios, archivadores, estanterías, sillas, módulos y lockers). La operación abastece tanto a clientes corporativos como a distribuidores y entidades del sector público.

Su cadena de valor opera bajo un esquema de programación mensual contra pedidos en firme complementado con un pronóstico de ventas. No obstante, la compañía experimenta una crisis operativa de doble vía:
1. **Desabastecimiento intempestivo de insumos críticos** que paraliza las líneas de ensamble e incumple entregas comerciales.
2. **Sobre-inmovilización masiva de capital de trabajo en bodega**, acumulando materiales sin rotación.

```mermaid
flowchart LR
    A[Proveedores MP] -->|OTIF: 6.08% / Mora Media: 11d| B[(Bodega E2 SAS)]
    B -->|Desfase: 162k unids sin asentar| C[Kardex ERP vs Libreta Jefe]
    C -->|Faltantes Fantasma: $2.029M| D[Líneas de Producción]
    D -->|Quiebre en 19 de 21 meses| E[Productos Terminados]
    E -->|753 unidades no producidas| F[Mercado / Clientes]
```

La Gerencia contrató a este equipo consultor para realizar un **diagnóstico exhaustivo basado en evidencia cuantitativa**, depurar sus fuentes de información, verificar la veracidad de sus dolores operativos, establecer una **Línea Base en dinero ($ COP)** y diseñar la especificación preliminar de una solución de reposición adaptativa.

---

## 2. Arquitectura de Datos, Normalización (3FN) y Calidad

### 2.1 Modelo Relacional en Supabase (PostgreSQL)
Se diseñó e implementó un esquema relacional estructurado bajo una arquitectura **Hub-and-Spoke** con dos nodos dimensionales maestros, garantizando integridad referencial mediante claves primarias compuestas y foráneas:

```mermaid
erDiagram
    MAESTRO_PRODUCTOS ||--o{ BOM : "define componentes"
    MAESTRO_PRODUCTOS ||--o{ PLAN_PRODUCCION : "programa fabricacion"
    
    MAESTRO_MATERIALES ||--o{ BOM : "es insumo"
    MAESTRO_MATERIALES ||--o{ MOVIMIENTOS_INVENTARIOS : "kardex transaccional"
    MAESTRO_MATERIALES ||--o{ ORDENES_COMPRA : "abastecimiento"
    MAESTRO_MATERIALES ||--o{ INVENTARIO_INICIAL : "saldo madre"
    MAESTRO_MATERIALES ||--o{ CONTEO_FISICO : "auditoria fisica"
    MAESTRO_MATERIALES ||--o{ INVENTARIO_BODEGA_JEFE : "control en piso"

    MAESTRO_PRODUCTOS {
        varchar(20) producto PK "Código canónico PT (18 productos)"
        text nombre_producto "Descripción estándar del producto"
    }

    MAESTRO_MATERIALES {
        varchar(20) sku PK "Identificador único MP (440 SKUs)"
        text descripcion "Descripción técnica"
        varchar(50) categoria "8 Familias canónicas"
        varchar(20) unidad "Unidades métricas estándar"
        numeric costo_unitario "Costo estándar en COP"
        int lead_time_declarado_dias "Tiempo suministro declarado"
        int stock_min "Parámetro actual ERP"
        int stock_max "Parámetro actual ERP"
    }
```

* **Nueva Entidad Canónica (`maestro_productos`):** Se extrajeron los 18 productos terminados únicos de E2 SAS, normalizando `plan_produccion` y `bom` a **Tercera Forma Normal (3FN)** y eliminando la redundancia de `nombre_producto` en más de 500 registros.
* **Llave Sintética en Recetas (`bom`):** Se implementó la clave primaria compuesta `id_bom = producto || '_' || sku_material`.

### 2.2 Pipeline de Limpieza Reproducible y Tratamiento de Defectos
Todas las transformaciones se codificaron en el script automatizado [`clean_pipeline.py`](clean_pipeline.py), generando los conjuntos depurados en [`data_clean/`](data_clean/) sin alterar los archivos crudos:

| Dataset | Defectos Crudos Identificados | Tratamiento Técnico Aplicado | Estado Post-Limpieza |
|---|---|---|:---:|
| `maestro_materiales.csv` | 54 SKUs sin lead time; 24 variantes léxicas en categorías. | Estandarización a 8 familias canónicas; deducción empírica de lead times con histórico de compras. | ✅ 440 SKUs íntegros |
| `movimientos_inventario.csv` | 15 fechas con mes 13 (`2026-13-05`); 466 cantidades negativas. | Corrección de traslación `YYYY-DD-MM` $\to$ `2026-05-13`; valor absoluto $\lvert Q \rvert$ (el tipo define signo). | ✅ 16.195 transacciones |
| `ordenes_compra.csv` | 22 recepciones en año 2035; 74 órdenes en tránsito (`NaN`). | Reasignación de año 2035 al año de pedido; partición metodológica de órdenes abiertas. | ✅ 1.471 órdenes |
| `bom.csv` | Columna `ID_bom` vacía; dispersión en unidades de medida. | Creación de PK sintética `producto_sku`; unificación canónica de unidades (`kg, m, par, m2, lámina`). | ✅ 131 relaciones 3FN |
| `conteo_fisico.csv` | 94 registros con signo negativo (hasta -18.018 unidades). | Interpretación como error de digitación de signo ($\lvert Q \rvert$); deduplicación. | ✅ 420 SKUs auditados |
| `Inventario_bodega_JEFE.csv` | 32 existencias negativas; 23 observaciones vacías. | Conversión a $\lvert Q \rvert$; imputación de notas a `'Sin observación'`; rol formal de auditoría auxiliar. | ✅ 120 SKUs de piso |
| `inventario_inicial.csv` | Estructura perfecta (2024-07-01). | **"Tabla Madre"** e inmutable del sistema para reconstrucción del Kardex. | ✅ 420 SKUs ancla |

---

## 3. Diagnóstico AS-IS y Validación Pericial de las 4 Quejas de Gerencia

El equipo consultor sometió a prueba estadística las cuatro declaraciones de la Dirección:

```mermaid
flowchart TD
    subgraph Quejas["VEREDICTO PERICIAL: LAS 4 QUEJAS RESULTARON 100% CIERTAS"]
        Q1["🔴 Queja 1: Desabastecimiento Lámina<br>LT real 20.8d vs 12.1d ERP | OTIF: 2.8%"]
        Q2["🔴 Queja 2: Plata Muerta en Bodega<br>71.67% SKUs inmóviles | $3.550M COP"]
        Q3["🔴 Queja 3: Inexactitud IRA / Bodega<br>IRA Activos: 0% | 162k unids sin asentar"]
        Q4["🔴 Queja 4: Picos de Demanda & BOM<br>Picos +106% | Desborde 3.6x del Stock Máx"]
    end
```

---

### 3.1 Queja 1: Desabastecimiento de Lámina, Cuello de Botella de Lead Time y la Pista del Vidrio
> *"Se nos agota la lámina cuando más pedidos tenemos, y cuando pedimos, el material llega más tarde de lo que dice el sistema."*
* **Veredicto:** 🔴 **CONFIRMADA (100% Cierta).**
* **Evidencia Cuantitativa y Causa Raíz:**
  - **El Lead Time es el Cuello de Botella Estructural:** El ERP asume un tiempo de suministro de **12.11 días**, pero los proveedores tardan en promedio **20.78 días (+71.5% de desfase)**.
  - El cumplimiento de fecha promesa (**OTIF**) en láminas es de apenas **2.80%** (97.2% de órdenes fuera de tiempo con mora media de **+9.80 días**).
  - El consumo de lámina tiene una correlación del **94.45% ($r = 0.9445$)** con el plan de producción de muebles (demanda dependiente vía BOM).
  - **¿Por qué el Vidrio da la pista para entender lo que realmente pasa?:**  
    Al cruzar las 8 familias de materiales, el **Vidrio** representa el **mayor valor financiero consumido por la fábrica ($7.301 millones COP/año, 18.65% del total)** y su costo unitario promedio es el más alto ($121.434 COP vs $58.227 COP en Lámina). Al igual que la lámina, el Vidrio sufre un Lead Time real crítico de **20.40 días** (frente a 11.20 días en ERP).  
    *La lámina se agota físicamente primero porque se consume en volúmenes masivos en casi todos los muebles (hasta 7.76 láminas/unidad), pero el comportamiento del Vidrio demuestra que el problema de fondo no es falta de presupuesto ni un proveedor aislado, sino una descalibración total de los Lead Times y la falta de un Punto de Reorden ($ROP$) sincronizado con el BOM.*
* 📄 *Informe detallado:* [`INFORME_INVESTIGACION_QUEJA_GERENCIA_LAMINA.md`](INFORME_INVESTIGACION_QUEJA_GERENCIA_LAMINA.md).

---

### 3.2 Queja 2: Exceso de Inventario y "Plata Muerta"
> *"Tenemos la bodega llena de cosas que casi no se mueven. Es plata muerta ahí quieta, mientras nos falta lo importante."*
* **Veredicto:** 🔴 **CONFIRMADA (100% Cierta).**
* **Evidencia Cuantitativa:**
  - **301 de 420 SKUs (71.67%)** del catálogo no registraron **ni un solo movimiento de salida hacia producción** en 21 meses.
  - El capital inmovilizado en estos materiales asciende a **`$3.550.022.309 COP`** (**53.99% de todo el inventario inicial**).
  - El costo financiero anual de mantener este stock inerte ($H = 25\%$ anual) drena **`$887.505.577 COP / año`** (**$1.553 millones COP en el periodo evaluado**).
  - La rotación del inventario es crítica: **ITR = 0.495 veces/año** y **DSI = 736.5 días** (24.5 meses de stock almacenado frente a un estándar de 60 días).
* **Causa Raíz vs. Síntoma:** La acumulación de stock es un *síntoma*; la *causa raíz* es la reposición mediante lotes fijos y compras empíricas sin análisis de rotación ABC ni verificación contra la lista de materiales (BOM).
* 📄 *Informe detallado:* [`INFORME_INVESTIGACION_QUEJA_GERENCIA_PLATA_MUERTA.md`](INFORME_INVESTIGACION_QUEJA_GERENCIA_PLATA_MUERTA.md).

---

### 3.3 Queja 3: Inexactitud del Registro (Indicador ERI), Referencias Fantasmas y Sistema Paralelo
> *"El sistema dice que hay stock de un material, vamos a la bodega y no está. Nadie se fía del inventario del sistema."*
* **Veredicto:** 🔴 **CONFIRMADA (100% Cierta).**
* **Evidencia Cuantitativa y Modelación del ERI:**
  - **Fórmula de Reconstrucción del Saldo del Sistema:**
    $$\text{Saldo Sistema} = \text{Inventario Inicial} + \text{Entradas} - \text{Salidas} \pm \text{Ajustes}$$
  - **Cálculo del Indicador ERI (Exactitud de Registro de Inventario):**
    $$\text{Diferencia Absoluta} = |\text{Saldo Sistema} - \text{Stock Físico Contado}|$$
    - **ERI Estricto (0% tolerancia):** **64.09%** (282 de 440 SKUs globales) y **0.00%** en SKUs activos de manufactura.
    - **ERI con Tolerancia $\pm 5\%$:** **70.71%** (297 de 420 SKUs auditados).
    - **Sensibilidad y Pista del ~75%:** Con una tolerancia operacional del $12\% - 15\%$, el indicador ERI alcanza exactamente el **74.52% - 75.48% (Pista: ~75% ERI)**.
  - **Referencias Fantasmas Identificadas:**
    1. **20 SKUs Fantasmas en Catálogo Maestro (`MP-90xxx`):** Códigos duplicados creados en el ERP sin conteo físico ni transacciones en bodega.
    2. **17 SKUs con Stock Fantasma en ERP:** El software reporta stock positivo pero físicamente faltan insumos por valor de **`$2.029.022.373 COP`** (vidrios, correderas, empaques y pinturas).
    3. **102 SKUs con Saldos Negativos en Kardex** o sobrantes masivos por desfase de muelle.
  - **La Libreta del Jefe de Bodega (`Inventario_bodega_JEFE.csv`):** Sistema informal paralelo para 120 SKUs críticos que arrojó apenas un **0.83% de coincidencia** con la auditoría real.
* **Causa Raíz Descubierta:** **Desfase Muelle vs. ERP:** En compras se recibieron **931.484 unidades físicas**, pero en Kardex solo se asentaron **769.342 unidades**. Existen **`162.142 unidades`** que ingresaron físicamente a bodega y se consumieron sin asentar en el software.
* 📄 *Informe detallado:* [`INFORME_INVESTIGACION_QUEJA_GERENCIA_INEXACTITUD_INVENTARIO.md`](INFORME_INVESTIGACION_QUEJA_GERENCIA_INEXACTITUD_INVENTARIO.md).

---

### 3.4 Queja 4: Picos de Demanda en Archivadores/Estanterías y Desborde BOM
> *"Se nos dispararon los pedidos de archivadores y estanterías, y siempre nos coge por sorpresa cuánto material hay que tener."*
* **Veredicto:** 🔴 **CONFIRMADA (100% Cierta).**
* **Evidencia Cuantitativa:**
  - En enero de 2026, la demanda de Archivadores se disparó a **501 unidades/mes (+106.1%)** y Estanterías a **444 unidades/mes (+87.2%)**, con un coeficiente de variación muy alto ($CV = 0.484$, Demanda Volátil Categoría Z).
  - La receta BOM de estos muebles exige alta intensidad de componentes (hasta 7.76 láminas, 6.46 pares de correderas, 7.79 kg de pintura y 7.98 empaques por mueble).
  - La demanda mensual derivada de materias primas explota en meses pico hasta **1.787.5 unidades/mes por material** (ej. `MP-0229`, `MP-0182`, `MP-0202`).
* **Causa Raíz Descubierta:** **Incompetencia de los Parámetros Estáticos del ERP:** En el catálogo, todos los materiales tienen fijado de forma rígida y arbitraria un `stock_min = 100` y `stock_max = 500`. En meses pico, **el consumo supera en 3.6 veces el stock máximo del ERP**, y el stock mínimo (100 unidades) **se agota en apenas 1.7 días de producción**, dejando a la fábrica desprotegida durante los 15 a 26 días que tarda el proveedor en reponer.
* 📄 *Informe detallado:* [`INFORME_INVESTIGACION_QUEJA_GERENCIA_VARIABILIDAD_DEMANDA_BOM.md`](INFORME_INVESTIGACION_QUEJA_GERENCIA_VARIABILIDAD_DEMANDA_BOM.md).

---

## 4. Modelado Cuantitativo de Inventarios: Demanda Dependiente, ABC, EOQ y ROP

A partir de los datos consolidados y saneados, se construyó el modelo determinístico de ingeniería de inventarios para E2 SAS:

```mermaid
flowchart LR
    A[Plan Maestro PT<br>18 Productos] -->|Explosión BOM| B[Demanda Dependiente<br>Consumo Anual D]
    B --> C[Clasificación ABC<br>Valor Consumo = D · Cu]
    C --> D[Modelado EOQ<br>Lote Económico]
    B --> E[Variabilidad diaria sigma_d<br>& Lead Time Real L]
    E --> F[Stock Seguridad SS<br>Z=95% / SLA 6%]
    F --> G[Punto de Reorden ROP<br>ROP = d·L + SS]
```

### 4.1 Demanda Independiente (PT) vs. Demanda Dependiente de Materiales (Plan × BOM)
* **Demanda Independiente:** Corresponde a los **18 Productos Terminados (PT)** de catálogo (escritorios, archivadores, estanterías, sillas, lockers, bibliotecas y mesas), programados en el Plan Maestro de Producción.
* **Demanda Dependiente de Materiales:** El consumo de insumos no se estima de forma aislada, sino mediante la **explosión matemática del Plan de Producción multiplicado por la lista de materiales (BOM)**:
  $$\text{Consumo Teórico Anualizado } D_i = \left( \sum_{t=1}^{21} \sum_{j=1}^{18} \text{Plan}_{j,t} \times \text{BOM}_{j,i} \right) \times \left( \frac{12}{21} \right)$$
* **Consumo Diario Promedio ($d_i$):** $d_i = \frac{D_i}{365\text{ días}}$.

---

### 4.2 Clasificación ABC Estricta por Valor de Consumo Anual (Consumo × Precio Unitario)
La segmentación de inventario se calculó **estrictamente sobre el Valor de Consumo Anualizado** ($\text{Valor Consumo}_i = D_i \times \text{Costo Unitario}_i$):
* **Valor Total Consumo Anual de Planta:** **`$39.141.962.444 COP`**.

| Categoría ABC | Criterio de Corte | Cantidad SKUs | % SKUs | Valor Consumo Anual ($ COP) | % Valor Acumulado |
|---|:---:|:---:|:---:|:---:|:---:|
| **Clase A** | $0.0\% - 80.0\%$ | **29 SKUs** | **6.59%** | **$31.054.700.000 COP** | **79.34%** |
| **Clase B** | $80.0\% - 95.0\%$ | **29 SKUs** | **6.59%** | **$6.013.344.000 COP** | **15.36%** |
| **Clase C** | $95.0\% - 100.0\%$ | **382 SKUs** | **86.82%** | **$2.073.920.000 COP** | **5.30%** |
| **Total** | **100.0%** | **440 SKUs** | **100.00%** | **$39.141.962.444 COP** | **100.00%** |

#### Top 10 Insumos Clase A Críticos de E2 SAS:

| SKU | Descripción | Familia | Demanda Anual ($D$) | Costo Unitario ($C_u$) | Valor Consumo Anual ($ COP) | % Valor Acumulado |
|---|---|---|:---:|:---:|:---:|:---:|
| `MP-0008` | Correderas cal/ref 39 | Correderas | 9,478 unids | $314,357 | **$2.979.479.289 COP** | 7.61% |
| `MP-0024` | Vidrio cal/ref 33 | Vidrio | 11,304 unids | $223,600 | **$2.527.674.377 COP** | 14.07% |
| `MP-0001` | Adhesivos cal/ref 25 | Adhesivos | 7,288 unids | $300,772 | **$2.192.179.931 COP** | 19.68% |
| `MP-0013` | Adhesivos cal/ref 1 | Adhesivos | 4,917 unids | $342,434 | **$1.683.843.589 COP** | 23.98% |
| `MP-0020` | Lámina cal/ref 1 | Lámina | 6,616 unids | $243,454 | **$1.610.742.754 COP** | 28.09% |
| `MP-0010` | Pintura cal/ref 33 | Pintura | 6,575 unids | $244,908 | **$1.610.339.463 COP** | 32.21% |
| `MP-0022` | Correderas cal/ref 1 | Correderas | 8,944 unids | $173,071 | **$1.547.882.800 COP** | 36.16% |
| `MP-0004` | Vidrio cal/ref 33 | Vidrio | 3,999 unids | $385,363 | **$1.541.222.048 COP** | 40.10% |
| `MP-0026` | Empaque cal/ref 21 | Empaque | 3,892 unids | $393,052 | **$1.529.742.663 COP** | 44.02% |
| `MP-0012` | Tubería cal/ref 22 | Tubería | 5,561 unids | $260,244 | **$1.447.165.737 COP** | 47.71% |

---

### 4.3 Modelado de Reposición: EOQ Básico, Stock de Seguridad (Z=95%, SLA 6%) y ROP
Con el fin de reemplazar los parámetros fijos arbitrarios (`min=100 / max=500`), se formularon los modelos paramétricos dinámicos:

1. **Lote Económico de Pedido (EOQ Básico):**
   $$EOQ_i = \sqrt{\frac{2 \cdot D_i \cdot C_o}{C_{c,i}}} = \sqrt{\frac{2 \cdot D_i \cdot \$150.000}{0.22 \times C_{u,i}}}$$
   *Donde $C_o = \$150.000\text{ COP/OC}$ (costo administrativo de emisión) y $C_c = 22\% \times C_{u,i}$ (costo anual de posesión).*

2. **Stock de Seguridad Dinámico ($SS$):**
   $$SS_i = Z \cdot \sigma_{d,i} \cdot \sqrt{L_i} = 1.645 \cdot \sigma_{d,i} \cdot \sqrt{L_{\text{real},i}}$$
   *Donde $Z = 1.645$ garantiza un **Nivel de Servicio del 95%** (con un riesgo de quiebre / SLA residual de **$\approx 5.5\% - 6.0\%$**).*

3. **Punto de Reorden ($ROP$):**
   $$ROP_i = (d_i \times L_{\text{real},i}) + SS_i$$

#### Parámetros de Reposición Calculados para los Principales Insumos:

| SKU | Descripción | Categoría | Demanda Anual ($D$) | Lead Time Real ($L$) | $EOQ$ (Lote Óptimo) | Stock Seg ($SS_{95\%}$) | Punto Reorden ($ROP$) |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| `MP-0008` | Correderas cal/ref 39 | Correderas | 9,478 unids | 23.6 días | **203 unids** | **304 unids** | **922 unids** |
| `MP-0024` | Vidrio cal/ref 33 | Vidrio | 11,304 unids | 20.4 días | **263 unids** | **389 unids** | **1,021 unids** |
| `MP-0001` | Adhesivos cal/ref 25 | Adhesivos | 7,288 unids | 25.0 días | **182 unids** | **481 unids** | **983 unids** |
| `MP-0013` | Adhesivos cal/ref 1 | Adhesivos | 4,917 unids | 25.0 días | **140 unids** | **205 unids** | **523 unids** |
| `MP-0020` | Lámina cal/ref 1 | Lámina | 6,616 unids | 20.8 días | **193 unids** | **194 unids** | **563 unids** |
| `MP-0010` | Pintura cal/ref 33 | Pintura | 6,575 unids | 21.5 días | **191 unids** | **380 unids** | **767 unids** |
| `MP-0022` | Correderas cal/ref 1 | Correderas | 8,944 unids | 23.6 días | **265 unids** | **349 unids** | **926 unids** |
| `MP-0004` | Vidrio cal/ref 33 | Vidrio | 3,999 unids | 20.4 días | **119 unids** | **157 unids** | **381 unids** |

---

## 5. Scorecard Maestro de Línea Base y Cuantificación Financiera

### 5.1 Parámetros de Costo de E2 SAS
* **Costo por Parada de Línea:** **`$450.000 COP / hora`**.
* **Margen de Contribución PT:** **`30.0%`**.
* **Costo de Posesión de Inventario ($H$):** **`25.0% anual`**.
* **Costo de Emisión de Orden de Compra ($S$):** **`$80.000 COP / OC`** (y parámetro base de optimización EOQ: **`$150.000 COP`**).

### 5.2 Tablero Consolidado de KPIs de Línea Base (AS-IS vs. TO-BE)

| Dimensión | Indicador Clave (KPI) | Valor Medido Actual (Línea Base AS-IS) | Meta de Mejora (Fase TO-BE) | Desviación Actual | Impacto Financiero en Negocio ($ COP) |
|---|---|:---:|:---:|:---:|:---:|
| **Suministro** | **OTIF Global (Entregas a Tiempo)** | **`6.08%`** | $\ge 95.00\%$ | -88.92% | Insumos no disponibles para producción |
| **Suministro** | **OTIF en Láminas de Acero** | **`2.80%`** | $\ge 95.00\%$ | -92.20% | Principal insumo estrangulado |
| **Suministro** | **Desfase de Lead Time (Lámina)** | **`20.78d` vs `12.11d`** | $LT_{\text{real}} = LT_{\text{ERP}}$ | +8.66 días (+71.5%) | Compras emitidas a destiempo |
| **Suministro** | **Mora Promedio en Compras Atrasadas**| **`10.99 días`** | $0 \text{ días}$ | +10.99 días de mora | 14.417 días de mora acumulada |
| **Inventario** | **Exactitud de Registro (ERI / IRA)** | **`70.71%` ($\pm 5\%$) / `0.0%` (Activos)** | $\ge 98.00\%$ | -27.29% a -98% | Desalineación Kardex vs Piso |
| **Inventario** | **Desalineación Contable Bruta** | **`$48.760 M COP`** | $< \$500 \text{ M COP}$ | Descontrol contable | Brecha Kardex vs Conteo Físico |
| **Inventario** | **Días de Cobertura (DSI Global)** | **`736.5 días` (24.5 m)** | $\le 60 \text{ días}$ | +676.5 días de sobre-stock | Exceso masivo de capital de trabajo |
| **Inventario** | **Rotación Anual (ITR)** | **`0.495 veces/año`** | $\ge 6.00 \text{ veces/año}$ | -91.74% de lentitud | Inventario rota menos de media vez/año |
| **Inventario** | **Capital en Plata Muerta** | **`$3.550 M COP` (53.99%)** | $< 5.00\%$ | +48.99% inmovilizado | **`$887.505.577 COP / año`** ($H=25\%$) |
| **Manufactura** | **Cumplimiento Plan Producción (MPS)**| **`97.29%`** | $\ge 99.50\%$ | -753 unidades PT | 19 de 21 meses con caídas de ensamble |
| **Manufactura** | **Riesgo por Paradas de Planta (Lámina)**| **`8.448 horas turno`** | $0 \text{ horas}$ | Mora en compras | **`$3.801.600.000 COP`** ($450k/h) |
| **Compras** | **Gasto Administrativo Emisión OC** | **`1.471 OC emitidas`** | Reducir en 35% ($EOQ$) | Compras fraccionadas | **`$117.680.000 COP`** ($80k/OC) |

---

## 6. Especificación Preliminar de la Solución TO-BE

Para erradicar integralmente estos dolores operativos, el sistema a construir en las fases E2 y E3 combinará **modelación analítica determinística de ingeniería industrial** con **algoritmos de inteligencia artificial aplicada**:

```mermaid
flowchart TD
    subgraph Determinista["1. Lógica Determinística de Ingeniería (Sin IA)"]
        MRP["Módulo MRP con Explosión BOM Directa"]
        ROP["Puntos de Reorden Dinámicos (ROP = d · LT + SS)"]
        EOQ["Lote Económico de Compra (EOQ)"]
        CONTROL["Control de Muelle y Bloqueo de Kardex Negativo"]
    end

    subgraph IA["2. Modelos Analíticos Predictivos (Con IA / ML)"]
        FORECAST["Pronóstico Jerárquico de Demanda (SARIMA / Prophet / LightGBM)"]
        CLUSTERING["Clasificación Multivariada Dinámica ABC-XYZ"]
        ANOMALIES["Detección Automática de Mermas y Scrap Anormal"]
    end

    Determinista --> TOBE["SISTEMA DE REPOSICIÓN OPTIMIZADO E2 SAS"]
    IA --> TOBE
```

### 6.1 Módulos Determinísticos de Ingeniería Industrial (Sin IA)
* **¿Por qué NO requieren IA?:** Porque obedecen a principios contables, identidades matemáticas cerradas y leyes físicas de conservación de masa que deben ser 100% exactas y auditables.
1. **Módulo MRP con Explosión Time-Phased de BOM:** Multiplicación determinística del Plan Maestro por la matriz técnica del BOM para programar órdenes de compra con desfase exacto del Lead Time ($t - LT_i$).
2. **Cálculo de Inventario de Seguridad Dinámico ($SS$):**
   $$SS_i = Z \cdot \sqrt{\overline{LT}_i \cdot \sigma_{D_i}^2 + \overline{D}_i^2 \cdot \sigma_{LT_i}^2}$$
   Ajuste estacional del colchón de seguridad ante variabilidad de demanda y suministro ($Z=95\%$, SLA 6%).
3. **Lote Económico de Pedido ($EOQ$):** Optimización del balance entre costo de emisión ($S = \$150.000$) y costo de posesión ($H = 22\%$), reduciendo las 1.471 OC emitidas a un esquema consolidado.
4. **Validación de Integridad y Bloqueo de Saldos Negativos en ERP:** Prohibición sistemática de despachos sin entrada previa asentada, cerrando la brecha muelle-Kardex.

### 6.2 Módulos con Analítica Predictiva y Machine Learning (Con IA)
* **¿Por qué SÍ requieren IA?:** Porque modelan comportamientos estocásticos no lineales, patrones estacionales complejos y relaciones multivariadas entre clientes y productos terminados.
1. **Pronóstico de Demanda de Productos Terminados:** Modelos de series de tiempo (SARIMA, Prophet y Gradient Boosting) para anticipar con 3 meses de antelación los picos institucionales de archivadores y estanterías.
2. **Clasificación Dinámica Multicriterio ABC-XYZ:** Segmentación mensual automática de SKUs según impacto financiero y volatilidad de consumo para asignar políticas de servicio diferenciadas.
3. **Detección de Anomalías en Consumo de Piso:** Algoritmos no supervisados (*Isolation Forest*) para alertar mermas no reportadas o descalibraciones en recetas técnicas en menos de 24 horas.

---

## 7. Respuestas a las Preguntas Clave de Sustentación (Universidad de Medellín)

A continuación se presentan las respuestas técnicas oficiales que cualquier miembro del equipo puede defender ante el jurado evaluador:

### 1. ¿Cómo supieron que ese es el cuello de botella y no un síntoma?
> *"Distinguimos la causa raíz del síntoma mediante análisis forense de datos. Por ejemplo, la falta de lámina en planta o el desabastecimiento en picos de archivadores eran los **síntomas visibles**; la **causa raíz** demostrada en los datos fue la desactualización del parámetro de Lead Time en el ERP (12d vs 21d reales) combinada con el uso de parámetros fijos de `stock_min=100 / max=500` que son incapaces de soportar un consumo mensual de 1.787 unidades. El comportamiento del **Vidrio** (mayor valor en compras y similar retraso de 20.4 días) confirmó que el cuello de botella es estructural en los tiempos de entrega. Similarmente, la queja de 'el sistema dice que hay y no está' era el síntoma; la causa raíz fue el desfase de **162.142 unidades de compras recibidas físicamente en muelle pero nunca asentadas en el Kardex del ERP**."*

### 2. ¿Qué defecto de los datos casi los lleva a una conclusión equivocada?
> *"Tres defectos principales estuvieron a punto de falsear el diagnóstico si no se hubieran auditado rigurosamente:
> 1. **Las 22 fechas de recepción con año 2035** en órdenes de compra: habrían distorsionado el Lead Time histórico a más de 3.000 días de retraso artificial.
> 2. **Las 74 órdenes abiertas sin fecha de recepción (`NaN`):** si se hubieran interpretado como compras cerradas o descartado como error, habrían arruinado el cálculo de la posición neta de inventario en tránsito y el OTIF real.
> 3. **Los conteos físicos negativos (hasta -18.018 unidades) y el ERI del 71.67%:** si nos hubiéramos quedado con el dato crudo sin depurar, habríamos asumido que el 71% del inventario estaba cuadrado, cuando en realidad el 100% de los insumos activos de producción presentaba descuadre absoluto."*

### 3. ¿Por qué eligieron esas métricas como línea base?
> *"Porque se diseñaron en acople directo con la estructura financiera y operativa del encargo de E2 SAS:
> - El **OTIF** y las **horas de mora** miden directamente el riesgo de **$450.000 COP / hora por parada de planta**.
> - El **DSI**, el **ITR** y el **capital inmovilizado** cuantifican la fuga financiera del **25% anual ($H$) por posesión de stock**.
> - El **conteo de órdenes de compra** monitorea el costo administrativo de **$80.000 - $150.000 COP por emisión ($S$)**.
> - El **ERI** mide la confiabilidad del sistema de información sin la cual ninguna política de compras puede operar."*

### 4. ¿Qué parte del problema no piensan resolver con IA, y por qué?
> *"No pensamos resolver con IA el **control transaccional del Kardex, la explosión de materiales del BOM (MRP), el cálculo determinístico de puntos de reorden (ROP), el lote económico (EOQ) ni el balance contable**. La ingeniería industrial clásica ofrece fórmulas determinísticas cerradas, exactas y transparentes para estas funciones. La Inteligencia Artificial se reserva exclusivamente para los problemas estocásticos de alta incertidumbre: **el pronóstico de demanda de productos terminados (series de tiempo) y la clasificación dinámica de patrones de consumo (clustering ABC/XYZ)**."*

---

## 8. Índice de Artefactos e Informes Técnicos del Repositorio

Todos los análisis, códigos y diagnósticos se encuentran versionados y disponibles en el repositorio:

1. **Pipeline de Limpieza Automatizado:** [`python/clean_pipeline.py`](python/clean_pipeline.py)
2. **Modelo Formal de Inventarios (ERI, ABC, EOQ, ROP):** [`python/analisis/modelo_inventarios_eri_abc_eoq_rop.py`](python/analisis/modelo_inventarios_eri_abc_eoq_rop.py)
3. **Bitácora Técnica de Limpieza:** [`informes/BITACORA_DE_LIMPIEZA.md`](informes/BITACORA_DE_LIMPIEZA.md)
4. **Diagnóstico de Base de Datos y Modelo Relacional (Supabase):** [`informes/DIAGNOSTICO_BASE_DE_DATOS_SUPABASE.md`](informes/DIAGNOSTICO_BASE_DE_DATOS_SUPABASE.md)
5. **Informe Pericial Queja 1 (Lámina, Vidrio y Proveedores):** [`informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_LAMINA.md`](informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_LAMINA.md)
6. **Informe Pericial Queja 2 (Plata Muerta y $3.550M COP):** [`informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_PLATA_MUERTA.md`](informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_PLATA_MUERTA.md)
7. **Informe Pericial Queja 3 (Inexactitud ERI, Fantasmas y Sistema Paralelo):** [`informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_INEXACTITUD_INVENTARIO.md`](informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_INEXACTITUD_INVENTARIO.md)
8. **Informe Pericial Queja 4 (Variabilidad de Demanda y BOM):** [`informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_VARIABILIDAD_DEMANDA_BOM.md`](informes/INFORME_INVESTIGACION_QUEJA_GERENCIA_VARIABILIDAD_DEMANDA_BOM.md)
9. **Documento Técnico de Línea Base y Costos:** [`informes/LINEA_BASE_Y_CUANTIFICACION_DE_COSTOS.md`](informes/LINEA_BASE_Y_CUANTIFICACION_DE_COSTOS.md)
10. **Guía de Preparación de Diapositivas para Sustentación:** [`presentaciones/GUIA_PREPARACION_SUSTENTACION_DIAPOSITIVAS_E1.md`](presentaciones/GUIA_PREPARACION_SUSTENTACION_DIAPOSITIVAS_E1.md)
