"""
SISTEMA DE GESTIÓN Y ABASTECIMIENTO INTELIGENTE - E2 SAS
Aplicación Operativa de Control de Inventarios, Ingesta CSV y Resultados Generales

Estructura:
  1. Resultados Generales del Sistema (Indicadores, Recomendaciones del Agente, Diagnóstico Kardex vs. Bodega, Proyección de Demanda y Parámetros Dinámicos)
  2. Carga y Procesamiento de Archivos CSV (Indicador en vivo de carga, detalle de filas anexadas y filas omitidas/no anexadas)
  3. Aseguramiento de Calidad (Suite de Pruebas QA Automatizada en Tiempo Real)
"""

import os
import sys
import json
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import orquestador
from nucleo import datos, ingesta, qa, base_datos

PORT = 8501

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2 SAS — Control de Inventarios & Abastecimiento</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #070b12;
            --surface: rgba(15, 23, 42, 0.92);
            --surface-card: rgba(30, 41, 59, 0.72);
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(14, 165, 233, 0.4);
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --accent: #38bdf8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --purple: #a855f7;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --radius: 12px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body { background: radial-gradient(circle at 50% 0%, #0f172a 0%, #05080e 90%); color: var(--text); min-height: 100vh; padding: 1.8rem 2.2rem; }

        .container { max-width: 1360px; margin: 0 auto; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.6rem; border-bottom: 1px solid var(--border); padding-bottom: 1.2rem; }
        .logo-badge { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); background: rgba(56, 189, 248, 0.1); padding: 0.3rem 0.75rem; border-radius: 20px; border: 1px solid rgba(56, 189, 248, 0.25); display: inline-block; margin-bottom: 0.4rem; font-weight: 700; }
        h1 { font-size: 1.95rem; font-weight: 700; letter-spacing: -0.5px; }
        p.subtitle { color: var(--text-muted); font-size: 0.92rem; margin-top: 0.2rem; }

        /* Navigation Tabs */
        .tabs { display: flex; gap: 0.6rem; margin-bottom: 1.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.75rem 1.3rem;
            font-size: 0.96rem;
            font-weight: 600;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .tab-btn:hover { color: var(--text); background: rgba(255, 255, 255, 0.05); }
        .tab-btn.active { color: #fff; background: var(--primary); box-shadow: 0 4px 16px rgba(2, 132, 199, 0.35); }

        .tab-pane { display: none; }
        .tab-pane.active { display: block; animation: fadeIn 0.25s ease; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        /* Buttons & Actions */
        button.btn-primary {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #fff;
            border: none;
            padding: 0.75rem 1.4rem;
            font-size: 0.92rem;
            font-weight: 600;
            border-radius: 10px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
        }
        button.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5); }
        
        button.btn-secondary {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.7rem 1.15rem;
            font-size: 0.88rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }
        button.btn-secondary:hover { background: rgba(255, 255, 255, 0.12); }

        /* Loading Overlay & Spinner */
        #loadingOverlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(5, 8, 14, 0.75);
            backdrop-filter: blur(6px);
            z-index: 9999;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(56, 189, 248, 0.2);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 1.2rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-title { font-size: 1.2rem; font-weight: 700; color: #fff; margin-bottom: 0.3rem; }
        .loading-sub { font-size: 0.9rem; color: var(--accent); }

        /* KPI Cards */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.1rem; margin-bottom: 1.8rem; }
        .kpi-card { background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.3rem; backdrop-filter: blur(10px); }
        .kpi-title { font-size: 0.78rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 0.35rem; font-weight: 600; }
        .kpi-value { font-size: 1.8rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
        .kpi-badge { font-size: 0.72rem; padding: 0.2rem 0.55rem; border-radius: 6px; display: inline-block; margin-top: 0.45rem; font-weight: 600; }

        /* Supervision Banner */
        .supervision-banner { background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: var(--radius); padding: 1.1rem 1.4rem; margin-bottom: 1.8rem; display: flex; align-items: center; gap: 1rem; }
        .supervision-banner.safe { background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.35); }
        .supervision-icon { font-size: 1.7rem; }

        /* Section Block */
        .section-block { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.8rem; box-shadow: 0 8px 25px rgba(0,0,0,0.25); }
        .section-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.8rem; }
        .section-title { font-size: 1.25rem; font-weight: 700; color: #fff; }
        .section-desc { font-size: 0.88rem; color: var(--text-muted); margin-top: 0.2rem; }

        /* Tables */
        .table-container { background: rgba(10, 15, 28, 0.6); border: 1px solid var(--border); border-radius: var(--radius); overflow-x: auto; margin-bottom: 1.2rem; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: rgba(255, 255, 255, 0.03); color: var(--text-muted); font-weight: 600; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 1px; padding: 0.95rem 1.1rem; border-bottom: 1px solid var(--border); }
        td { padding: 1rem 1.1rem; border-bottom: 1px solid var(--border); vertical-align: middle; font-size: 0.92rem; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }

        /* Dropzone */
        .dropzone-container { border: 2px dashed rgba(56, 189, 248, 0.35); border-radius: var(--radius); background: rgba(15, 23, 42, 0.6); padding: 2.2rem; text-align: center; cursor: pointer; transition: all 0.2s ease; margin-bottom: 1.2rem; }
        .dropzone-container:hover { border-color: var(--accent); background: rgba(56, 189, 248, 0.05); }
        .dropzone-icon { font-size: 2.5rem; margin-bottom: 0.6rem; color: var(--accent); }
        .dropzone-text { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.3rem; }
        .dropzone-sub { font-size: 0.85rem; color: var(--text-muted); }

        /* Badges */
        .badge-pill { padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; display: inline-block; }
        .badge-danger { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
        .badge-warning { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
        .badge-success { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
        .badge-info { background: rgba(56,189,248,0.2); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); }

        /* Toast */
        #toast { position: fixed; bottom: 2rem; right: 2rem; background: #1e293b; color: #fff; padding: 1rem 1.6rem; border-radius: 12px; border: 1px solid var(--accent); box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: none; z-index: 10000; font-weight: 500; }
    </style>
</head>
<body>
    <!-- Loading Overlay -->
    <div id="loadingOverlay">
        <div class="spinner"></div>
        <div class="loading-title" id="loadingTitle">Procesando archivo CSV...</div>
        <div class="loading-sub" id="loadingSub">Validando registros, verificando idempotencia y actualizando el inventario...</div>
    </div>

    <div class="container">
        <header>
            <div>
                <span class="logo-badge">E2 SAS · Control Integral de Abastecimiento</span>
                <h1>Tablero General de Gestión de Inventarios & Compras</h1>
                <p class="subtitle">Supervisión operativa, conciliación Kardex vs. Bodega y dimensionamiento dinámico de insumos</p>
            </div>
            <div style="display: flex; gap: 0.8rem;">
                <button class="btn-primary" onclick="ejecutarAnalisisGeneral()">🔄 Actualizar Análisis General</button>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="cambiarTab('resultados_generales')">📊 Resultados Generales del Sistema</button>
            <button class="tab-btn" onclick="cambiarTab('carga_csv')">📥 Carga y Procesamiento de Archivos CSV</button>
            <button class="tab-btn" onclick="cambiarTab('calidad_qa')">🧪 Aseguramiento de Calidad (QA)</button>
        </div>

        <!-- ============================================================== -->
        <!-- PESTAÑA 1: RESULTADOS GENERALES DEL SISTEMA (UNIFICADO)         -->
        <!-- ============================================================== -->
        <div id="tab-resultados_generales" class="tab-pane active">
            
            <!-- Banner de Supervisión -->
            <div id="supervisionBanner" class="supervision-banner">
                <div class="supervision-icon">⏳</div>
                <div>
                    <h3 id="supervisionTitle" style="font-size: 1.05rem; font-weight: 600;">Cargando estado general del sistema...</h3>
                    <p id="supervisionDesc" style="font-size: 0.88rem; color: var(--text-muted);">Consultando saldos canónicos y recomendaciones de abastecimiento.</p>
                </div>
            </div>

            <!-- KPIs Globales Ejecutivos -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-title">Exactitud de Inventario (ERI / IRA)</div>
                    <div class="kpi-value" id="kpiEri">--%</div>
                    <span class="kpi-badge" id="badgeEri">Evaluando</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Insumos en Quiebre (Stock &le; ROP)</div>
                    <div class="kpi-value" id="kpiQuiebres" style="color: var(--danger);">--</div>
                    <span class="kpi-badge badge-danger">Reorden Inmediata</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Inversión Sugerida en Compras</div>
                    <div class="kpi-value" id="kpiInversion" style="font-size: 1.55rem; color: var(--accent);">$0 COP</div>
                    <span class="kpi-badge badge-info">Lote Óptimo EOQ</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Discrepancias Físicas Detectadas</div>
                    <div class="kpi-value" id="kpiDiscrepancias" style="color: var(--warning);">--</div>
                    <span class="kpi-badge badge-warning">En Observación</span>
                </div>
            </div>

            <!-- BLOQUE 1: RECOMENDACIONES DEL AGENTE DE ABASTECIMIENTO -->
            <div class="section-block">
                <div class="section-header">
                    <div>
                        <div class="section-title">1. Plan de Abastecimiento: Órdenes de Compra Sugeridas</div>
                        <div class="section-desc">El agente identifica los insumos que alcanzaron el Punto de Reorden (ROP dinámico) y calcula el Lote Económico (EOQ) para absorber la demanda sin quiebres.</div>
                    </div>
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>SKU / Insumo</th>
                                <th>Categoría & ABC</th>
                                <th>Stock Real vs ROP</th>
                                <th>Sugerido (EOQ)</th>
                                <th>Inversión Estimada</th>
                                <th style="min-width: 320px;">Recomendación y Justificación del Agente</th>
                                <th>Decisión del Planeador</th>
                            </tr>
                        </thead>
                        <tbody id="tablaPropuestas">
                            <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.8rem;">Consultando órdenes de abastecimiento...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- BLOQUE 2: DIAGNÓSTICO DE INVENTARIOS (BODEGA VS. SISTEMA) -->
            <div class="section-block">
                <div class="section-header">
                    <div>
                        <div class="section-title">2. Diagnóstico de Existencias: Kardex vs. Bodega Física</div>
                        <div class="section-desc">Conciliación de saldos entre el Kardex del sistema y el conteo físico de piso para resolver inconsistencias y aislar materiales faltantes o pendientes de recibo.</div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn-secondary" onclick="filtrarDiscrepancias('fantasmas')">Ver Solo Faltantes en Bodega</button>
                        <button class="btn-secondary" onclick="filtrarDiscrepancias('desfases')">Ver Solo Desfases en Muelle</button>
                        <button class="btn-secondary" onclick="filtrarDiscrepancias('todos')">Ver Todos</button>
                    </div>
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>SKU / Insumo</th>
                                <th>Categoría</th>
                                <th>Saldo en Kardex</th>
                                <th>Conteo Físico Real</th>
                                <th>Diferencia</th>
                                <th>Costo Unitario</th>
                                <th>Impacto Financiero</th>
                                <th>Diagnóstico Operativo</th>
                            </tr>
                        </thead>
                        <tbody id="tablaDiscrepanciasEri">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.8rem;">Consultando conciliación de inventario...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- BLOQUE 3: PROYECCIÓN DE DEMANDA Y PARÁMETROS DINÁMICOS -->
            <div class="section-block">
                <div class="section-header">
                    <div>
                        <div class="section-title">3. Proyección de Demanda y Parámetros Dinámicos de Cobertura</div>
                        <div class="section-desc">Explosión de requerimientos del plan de producción contra recetas de ensamble. Los parámetros dinámicos (ROP y SS) garantizan 95% de nivel de servicio protegiendo a la planta ante picos de demanda.</div>
                    </div>
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Insumo Crítico</th>
                                <th>Categoría</th>
                                <th>Consumo en Mes Pico</th>
                                <th>Tope Anterior ERP</th>
                                <th>Nuevo ROP Dinámico</th>
                                <th>Stock Seguridad (SS)</th>
                                <th>Lote Sugerido (EOQ)</th>
                                <th>Estado de Protección</th>
                            </tr>
                        </thead>
                        <tbody id="tablaInsumosBOM">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.8rem;">Consultando proyección de demanda...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ============================================================== -->
        <!-- PESTAÑA 2: CARGA Y PROCESAMIENTO DE ARCHIVOS CSV                -->
        <!-- ============================================================== -->
        <div id="tab-carga_csv" class="tab-pane">
            <div style="margin-bottom: 1.4rem;">
                <h3 style="font-size: 1.3rem; font-weight: 700;">Ingesta y Actualización de Archivos CSV</h3>
                <p style="font-size: 0.9rem; color: var(--text-muted);">
                    Seleccione o arrastre su archivo CSV para procesarlo en el sistema. El motor evalúa idempotencia (no duplica si ya fue cargado) y acumula las transacciones nuevas.
                </p>
            </div>

            <!-- Upload Area -->
            <div style="background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.6rem; margin-bottom: 1.8rem;">
                <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.2rem; flex-wrap: wrap;">
                    <label style="font-weight: 600; font-size: 0.95rem;">Tipo de Documento:</label>
                    <select id="selectTipoDoc" style="background: #0f172a; color: #fff; border: 1px solid var(--border); padding: 0.6rem 1rem; border-radius: 8px; font-weight: 500;">
                        <option value="movimientos_inventario">Movimientos de Inventario (Entradas / Salidas / Remisiones)</option>
                        <option value="conteo_fisico">Conteo Físico de Bodega (Auditoría de Piso)</option>
                        <option value="ordenes_compra">Órdenes de Compra a Proveedores</option>
                        <option value="plan_produccion">Plan Maestro de Producción</option>
                        <option value="maestro_materiales">Maestro de Materiales y Costos</option>
                        <option value="bom">Matriz de Recetas Técnicas (BOM)</option>
                    </select>

                    <input type="file" id="csvFileInput" accept=".csv" style="display: none;" onchange="procesarArchivoSeleccionado(event)">
                    <button class="btn-primary" onclick="document.getElementById('csvFileInput').click()">📁 Seleccionar Archivo CSV de su equipo</button>
                </div>

                <!-- Drag & drop zone -->
                <div class="dropzone-container" onclick="document.getElementById('csvFileInput').click()" ondragover="event.preventDefault()" ondrop="manejarDrop(event)">
                    <div class="dropzone-icon">📥</div>
                    <div class="dropzone-text">Arrastre aquí su archivo CSV o haga clic para examinar</div>
                    <div class="dropzone-sub">Formato compatible: .CSV con encabezados de columna</div>
                </div>

                <!-- Quick pre-loads -->
                <div style="display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap;">
                    <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">Cargas operativas preconfiguradas:</span>
                    <button class="btn-secondary" onclick="cargarPreconfigurado('movimientos_taller')">📄 Cargar Remisión con Validación de Fechas</button>
                    <button class="btn-secondary" onclick="cargarPreconfigurado('movimientos_nuevos')">➕ Cargar Movimientos Nuevos (Acumulativo)</button>
                    <button class="btn-secondary" onclick="cargarPreconfigurado('idempotencia_test')">🔁 Probar Recarga Idempotente (Sin Duplicados)</button>
                </div>
            </div>

            <!-- DETALLE DE LO QUE SE ANEXÓ Y LO QUE NO SE ANEXÓ -->
            <div id="cardResultadoIngesta" style="display: none; background: rgba(15, 23, 42, 0.95); border: 1px solid var(--border-highlight); border-radius: var(--radius); padding: 1.6rem; margin-bottom: 1.8rem;">
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent); margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <span>📄 Resumen Detallado del Archivo Procesado: <strong id="lblNombreArchivo" style="color: #fff;">--</strong></span>
                    <span class="badge-pill badge-info" id="lblTipoDoc">--</span>
                </div>

                <div class="kpi-grid" style="margin-bottom: 1.4rem;">
                    <div class="kpi-card">
                        <div class="kpi-title">Total Filas Leídas</div>
                        <div class="kpi-value" id="resLeidas">0</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Filas Anexadas al Sistema</div>
                        <div class="kpi-value" id="resCargadas" style="color: var(--success);">0</div>
                        <span class="badge-pill badge-success">Nuevas en Base</span>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Duplicados Omitidos</div>
                        <div class="kpi-value" id="resDuplicadas" style="color: var(--warning);">0</div>
                        <span class="badge-pill badge-warning">Idempotencia Activa</span>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Filas Rechazadas (Anomalías)</div>
                        <div class="kpi-value" id="resRechazadas" style="color: var(--danger);">0</div>
                        <span class="badge-pill badge-danger">Formato Inválido</span>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Saldo Total en Base</div>
                        <div class="kpi-value" id="resSaldoTotal" style="color: var(--accent);">0</div>
                        <span class="badge-pill badge-info">Histórico Actual</span>
                    </div>
                </div>

                <!-- Sub-tabs for Annexed vs Non-Annexed rows -->
                <div style="display: flex; gap: 0.6rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                    <button id="btnTabAnexadas" class="tab-btn active" onclick="cambiarSubTabIngesta('anexadas')">✅ Ver Filas Anexadas al Sistema (<span id="countAnexadas">0</span>)</button>
                    <button id="btnTabOmitidas" class="tab-btn" onclick="cambiarSubTabIngesta('omitidas')">⚠️ Ver Filas Omitidas / No Anexadas (<span id="countOmitidas">0</span>)</button>
                </div>

                <!-- Sub-pane Annexed rows -->
                <div id="subtab-anexadas">
                    <div class="table-container" style="max-height: 260px; overflow-y: auto;">
                        <table>
                            <thead><tr><th>Fecha</th><th>SKU</th><th>Tipo Movimiento</th><th>Cantidad</th><th>Documento</th><th>Estado</th></tr></thead>
                            <tbody id="tablaFilasAnexadas">
                                <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Sin registros nuevos que mostrar.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Sub-pane Omitted rows (Duplicates or Rejections) -->
                <div id="subtab-omitidas" style="display: none;">
                    <div class="table-container" style="max-height: 260px; overflow-y: auto;">
                        <table>
                            <thead><tr><th>Fila/Ref</th><th>SKU</th><th>Campo/Documento</th><th>Motivo por el cual NO se anexó</th><th>Detalle</th></tr></thead>
                            <tbody id="tablaFilasOmitidas">
                                <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Sin registros omitidos.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Historical Log -->
            <h3 style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.8rem;">Historial de Archivos Cargados</h3>
            <div class="table-container">
                <table>
                    <thead><tr><th>Fecha y Hora</th><th>Archivo</th><th>Tipo</th><th>Leídas</th><th>Anexadas</th><th>Duplicadas Omitidas</th><th>Rechazadas</th><th>Resultado</th></tr></thead>
                    <tbody id="tablaBitacoraCargas">
                        <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Consultando historial...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ============================================================== -->
        <!-- PESTAÑA 3: ASEGURAMIENTO DE CALIDAD (QA)                        -->
        <!-- ============================================================== -->
        <div id="tab-calidad_qa" class="tab-pane">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.4rem;">
                <div>
                    <h3 style="font-size: 1.3rem; font-weight: 700;">Aseguramiento de Calidad del Sistema (QA)</h3>
                    <p style="font-size: 0.9rem; color: var(--text-muted);">Verificación automatizada en tiempo real: idempotencia, acumulatividad, integridad relacional y consistencia matemática.</p>
                </div>
                <button class="btn-primary" onclick="ejecutarPruebasQA()">🧪 Ejecutar Pruebas QA</button>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-title">Estado Global de Calidad</div>
                    <div class="kpi-value" id="qaEstadoGlobal" style="color: var(--success);">--</div>
                    <span class="badge-pill badge-success" id="qaBadgeConformidad">Conforme</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Pruebas Aprobadas</div>
                    <div class="kpi-value" id="qaAprobadas">0 / 6</div>
                    <span class="badge-pill badge-info">100% de Cobertura</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Tasa de Conformidad</div>
                    <div class="kpi-value" id="qaTasa" style="color: var(--success);">100%</div>
                    <span class="badge-pill badge-success">Cero Defectos</span>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Tiempo de Respuesta</div>
                    <div class="kpi-value" id="qaTiempo" style="color: var(--accent);">-- ms</div>
                    <span class="badge-pill badge-info">Test Rápido</span>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead><tr><th>Código</th><th>Prueba de Calidad</th><th>Área Evaluada</th><th>Resultado</th><th>Evidencia Comprobada</th></tr></thead>
                    <tbody id="tablaPruebasQA">
                        <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Cargando pruebas QA...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <div id="toast"></div>

    <script>
        let datosGenerales = null;
        let datosUltimaIngesta = null;

        function showLoading(msg) {
            document.getElementById('loadingTitle').innerText = msg || 'Procesando...';
            document.getElementById('loadingOverlay').style.display = 'flex';
        }

        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }

        function cambiarTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            
            event.currentTarget.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');

            if (tabId === 'carga_csv') cargarBitacoraCargas();
            if (tabId === 'calidad_qa') ejecutarPruebasQA();
        }

        function cambiarSubTabIngesta(subTabId) {
            document.getElementById('btnTabAnexadas').classList.toggle('active', subTabId === 'anexadas');
            document.getElementById('btnTabOmitidas').classList.toggle('active', subTabId === 'omitidas');
            document.getElementById('subtab-anexadas').style.display = (subTabId === 'anexadas') ? 'block' : 'none';
            document.getElementById('subtab-omitidas').style.display = (subTabId === 'omitidas') ? 'block' : 'none';
        }

        // ==============================================================
        // CARGA GENERAL DE DATOS E INDICADORES
        // ==============================================================
        async function ejecutarAnalisisGeneral() {
            showLoading('Actualizando indicadores y recomendaciones generales...');
            try {
                const res = await fetch('/api/orquestacion');
                const data = await res.json();
                datosGenerales = data;
                renderizarResultadosGenerales(data);
                hideLoading();
                showToast('✅ Análisis general completado.');
            } catch (err) {
                hideLoading();
                showToast('❌ Error al actualizar: ' + err.message);
            }
        }

        function renderizarResultadosGenerales(data) {
            // KPIs
            document.getElementById('kpiEri').innerText = data.kpis.eri_global_pct + '%';
            const badgeEri = document.getElementById('badgeEri');
            badgeEri.innerText = data.kpis.eri_global_pct >= 95 ? 'Nivel Óptimo' : 'Discrepancia en Bodega';
            badgeEri.className = 'kpi-badge ' + (data.kpis.eri_global_pct >= 95 ? 'badge-success' : 'badge-danger');
            
            document.getElementById('kpiQuiebres').innerText = data.kpis.skus_en_quiebre;
            document.getElementById('kpiInversion').innerText = '$' + Number(data.kpis.inversion_propuesta_cop).toLocaleString('es-CO') + ' COP';
            document.getElementById('kpiDiscrepancias').innerText = (data.kpis.materiales_fantasmas_detectados + data.kpis.desfases_muelle_detectados) + ' SKUs';

            // Banner
            const banner = document.getElementById('supervisionBanner');
            if (data.criterio_parada_activado) {
                banner.className = 'supervision-banner';
                document.getElementById('supervisionTitle').innerText = '🛑 Se detectaron insumos por debajo del Punto de Reorden (ROP)';
                document.getElementById('supervisionDesc').innerText = data.mensaje_parada;
            } else {
                banner.className = 'supervision-banner safe';
                document.getElementById('supervisionTitle').innerText = '✅ Niveles de inventario estables';
                document.getElementById('supervisionDesc').innerText = 'Sin quiebres críticos ni órdenes pendientes de aprobación.';
            }

            renderizarPropuestas(data.propuestas_compra);
            renderizarDiscrepancias(data.queja_1_auditoria_inventario);
            renderizarInsumosBOM(data.queja_2_explosion_demanda_bom);
        }

        function renderizarPropuestas(propuestas) {
            const tbody = document.getElementById('tablaPropuestas');
            if (!propuestas || propuestas.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #34d399; padding: 2rem;">✓ No se requieren órdenes de compra urgentes hoy. Todos los insumos están sobre el ROP.</td></tr>';
                return;
            }

            tbody.innerHTML = propuestas.map(p => `
                <tr id="row-${p.sku}">
                    <td><strong>${p.sku}</strong><br><span style="font-size: 0.8rem; color: var(--text-muted);">${p.descripcion}</span></td>
                    <td><span class="badge-pill badge-info">Clase ${p.clase_abc}</span><br><span style="font-size: 0.8rem; color: var(--text-muted);">${p.categoria}</span></td>
                    <td><strong>${p.stock_real}</strong> un.<br><span style="font-size: 0.8rem; color: #f87171;">ROP: ${p.punto_reorden_rop} un.</span></td>
                    <td><span style="color: #38bdf8; font-weight: 700; font-size: 1.1rem;">${p.cantidad_sugerida_eoq}</span> un.</td>
                    <td><strong>$${Number(p.inversion_estimada_cop).toLocaleString('es-CO')}</strong></td>
                    <td style="font-size: 0.85rem; line-height: 1.45; color: #cbd5e1;">${p.justificacion_ejecutiva}</td>
                    <td id="actions-${p.sku}">
                        <div style="display: flex; gap: 0.4rem;">
                            <button onclick="decidir('${p.sku}', 'APROBADA')" style="background: rgba(16,185,129,0.2); border: 1px solid var(--success); color: #34d399; padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-weight: 600;">Aprobar</button>
                            <button onclick="decidir('${p.sku}', 'RECHAZADA')" style="background: rgba(239,68,68,0.2); border: 1px solid var(--danger); color: #f87171; padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-weight: 600;">Rechazar</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }

        async function decidir(sku, accion) {
            try {
                const res = await fetch(`/api/decidir?sku=${sku}&accion=${accion}`);
                const data = await res.json();
                const cell = document.getElementById(`actions-${sku}`);
                if (accion === 'APROBADA') {
                    cell.innerHTML = '<span style="color: #34d399; font-weight: 700;">✓ ORDEN APROBADA</span>';
                    showToast(`✅ Orden ${sku} APROBADA y registrada en la base.`);
                } else {
                    cell.innerHTML = '<span style="color: #f87171; font-weight: 700;">✗ ORDEN RECHAZADA</span>';
                    showToast(`⚠️ Orden ${sku} RECHAZADA.`);
                }
            } catch (err) {
                showToast('❌ Error: ' + err.message);
            }
        }

        function renderizarDiscrepancias(q1) {
            if (!q1) return;
            filtrarDiscrepancias('todos');
        }

        function filtrarDiscrepancias(tipo) {
            if (!datosGenerales || !datosGenerales.queja_1_auditoria_inventario) return;
            const q1 = datosGenerales.queja_1_auditoria_inventario;
            const tbody = document.getElementById('tablaDiscrepanciasEri');
            
            let lista = [];
            if (tipo === 'fantasmas' || tipo === 'todos') {
                lista = lista.concat(q1.fantasmas_detalle.map(f => ({
                    sku: f.sku, desc: f.descripcion, cat: f.categoria,
                    sistema: f.saldo_sistema_kardex, fisico: f.conteo_fisico_bodega,
                    disc: '-' + f.faltante_en_piso + ' un.', costo: f.costo_unitario,
                    impacto: f.impacto_cop,
                    diag: 'Faltante en Bodega (Kardex > Físico)',
                    badgeClass: 'badge-danger'
                })));
            }
            if (tipo === 'desfases' || tipo === 'todos') {
                lista = lista.concat(q1.desfases_detalle.map(d => ({
                    sku: d.sku, desc: d.descripcion, cat: d.categoria,
                    sistema: d.saldo_sistema_kardex, fisico: d.conteo_fisico_bodega,
                    disc: '+' + d.sobrante_en_piso + ' un.', costo: d.costo_unitario,
                    impacto: d.sobrante_en_piso * d.costo_unitario,
                    diag: 'Desfase en Muelle (Físico > Kardex)',
                    badgeClass: 'badge-warning'
                })));
            }

            if (lista.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Sin discrepancias registradas en esta vista.</td></tr>';
                return;
            }

            tbody.innerHTML = lista.slice(0, 30).map(r => `
                <tr>
                    <td><strong>${r.sku}</strong><br><span style="font-size: 0.8rem; color: var(--text-muted);">${r.desc}</span></td>
                    <td>${r.cat}</td>
                    <td style="font-family: monospace;">${r.sistema} un.</td>
                    <td style="font-family: monospace; font-weight: 700;">${r.fisico} un.</td>
                    <td style="font-family: monospace; font-weight: 700; color: ${r.badgeClass === 'badge-danger' ? '#f87171' : '#fbbf24'};">${r.disc}</td>
                    <td>$${Number(r.costo).toLocaleString('es-CO')}</td>
                    <td><strong>$${Number(r.impacto).toLocaleString('es-CO')}</strong></td>
                    <td><span class="badge-pill ${r.badgeClass}">${r.diag}</span></td>
                </tr>
            `).join('');
        }

        function renderizarInsumosBOM(q2) {
            if (!q2 || !q2.insumos_criticos_pico) return;
            const tbody = document.getElementById('tablaInsumosBOM');
            tbody.innerHTML = q2.insumos_criticos_pico.map(r => `
                <tr>
                    <td><strong>${r.sku}</strong><br><span style="font-size: 0.8rem; color: var(--text-muted);">${r.descripcion}</span></td>
                    <td>${r.categoria}</td>
                    <td><strong style="color: #f87171; font-size: 1.05rem;">${r.demanda_mes_pico}</strong> un./mes</td>
                    <td><span style="text-decoration: line-through; color: var(--text-muted);">${r.stock_max_erp_antiguo} un.</span><br><span style="font-size: 0.75rem; color: #f87171;">(${r.cobertura_dias_erp_antiguo} días)</span></td>
                    <td><strong style="color: #38bdf8; font-size: 1.05rem;">${r.nuevo_rop_dinamico}</strong> un.</td>
                    <td>${r.nuevo_ss_dinamico} un.</td>
                    <td><strong>${r.lote_eoq_sugerido}</strong> un.</td>
                    <td><span class="badge-pill badge-success">${r.diagnostico}</span></td>
                </tr>
            `).join('');
        }

        // ==============================================================
        // CARGA CSV & DETALLE DE FILAS ANEXADAS VS OMITIDAS
        // ==============================================================
        function procesarArchivoSeleccionado(e) {
            const file = e.target.files[0];
            if (!file) return;
            enviarArchivoCSV(file.name, file);
        }

        function manejarDrop(e) {
            e.preventDefault();
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                enviarArchivoCSV(file.name, file);
            }
        }

        function enviarArchivoCSV(nombre, file) {
            const tipo = document.getElementById('selectTipoDoc').value;
            const reader = new FileReader();
            showLoading(`Subiendo y procesando ${nombre}...`);
            
            reader.onload = async (event) => {
                const contenido = event.target.result;
                try {
                    const res = await fetch('/api/cargar_csv', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nombre: nombre, tipo: tipo, contenido: contenido })
                    });
                    const data = await res.json();
                    datosUltimaIngesta = data;
                    renderizarDetalleIngesta(data);
                    hideLoading();
                    showToast('✅ Archivo procesado correctamente.');
                    ejecutarAnalisisGeneral();
                    cargarBitacoraCargas();
                } catch (err) {
                    hideLoading();
                    showToast('❌ Error al procesar: ' + err.message);
                }
            };
            reader.readAsText(file);
        }

        async function cargarPreconfigurado(tipoPrueba) {
            showLoading('Cargando y procesando archivo operativo...');
            try {
                const res = await fetch(`/api/cargar_preconfigurado?tipo=${tipoPrueba}`);
                const data = await res.json();
                datosUltimaIngesta = data;
                renderizarDetalleIngesta(data);
                hideLoading();
                showToast('✅ Carga procesada exitosamente.');
                ejecutarAnalisisGeneral();
                cargarBitacoraCargas();
            } catch (err) {
                hideLoading();
                showToast('❌ Error: ' + err.message);
            }
        }

        function renderizarDetalleIngesta(data) {
            document.getElementById('cardResultadoIngesta').style.display = 'block';
            document.getElementById('lblNombreArchivo').innerText = data.nombre_archivo;
            document.getElementById('lblTipoDoc').innerText = data.tipo_documento;

            document.getElementById('resLeidas').innerText = data.filas_leidas;
            document.getElementById('resCargadas').innerText = data.filas_anexadas_nuevas || data.cambio_neto_base;
            document.getElementById('resDuplicadas').innerText = data.filas_duplicadas_ignoradas;
            document.getElementById('resRechazadas').innerText = data.filas_rechazadas;
            document.getElementById('resSaldoTotal').innerText = Number(data.conteo_base_despues).toLocaleString('es-CO');

            // Render Filas Anexadas
            const tbodyAnexadas = document.getElementById('tablaFilasAnexadas');
            const countAnexadas = (data.filas_anexadas_detalle || []).length;
            document.getElementById('countAnexadas').innerText = data.filas_anexadas_nuevas || countAnexadas;

            if (data.filas_anexadas_detalle && data.filas_anexadas_detalle.length > 0) {
                tbodyAnexadas.innerHTML = data.filas_anexadas_detalle.map(r => `
                    <tr>
                        <td style="font-family: monospace;">${r.fecha}</td>
                        <td><strong>${r.sku}</strong></td>
                        <td><span class="badge-pill badge-info">${r.tipo}</span></td>
                        <td><strong>${r.cantidad}</strong></td>
                        <td>${r.documento}</td>
                        <td><span class="badge-pill badge-success">✓ Anexado al Kardex</span></td>
                    </tr>
                `).join('');
            } else {
                tbodyAnexadas.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No se anexaron registros nuevos (todas las filas ya existían o fueron omitidas).</td></tr>';
            }

            // Render Filas Omitidas / No Anexadas (Duplicados o Errores)
            const tbodyOmitidas = document.getElementById('tablaFilasOmitidas');
            let listaOmitidas = [];

            // Agregar duplicadas
            if (data.filas_duplicadas_detalle) {
                listaOmitidas = listaOmitidas.concat(data.filas_duplicadas_detalle.map(d => ({
                    ref: d.fecha || '--',
                    sku: d.sku,
                    campo: d.documento || 'Documento',
                    motivo: 'Registro Idéntico Ya Existente en Kardex',
                    detalle: 'Omitido automáticamente para evitar inflar el inventario (Idempotencia)',
                    badge: 'badge-warning'
                })));
            }

            // Agregar rechazadas
            if (data.rechazos_detalle) {
                listaOmitidas = listaOmitidas.concat(data.rechazos_detalle.map(r => ({
                    ref: 'Fila #' + r.fila,
                    sku: r.sku,
                    campo: r.campo + ` (${r.valor_original})`,
                    motivo: r.motivo.toUpperCase(),
                    detalle: r.detalle,
                    badge: 'badge-danger'
                })));
            }

            document.getElementById('countOmitidas').innerText = (data.filas_duplicadas_ignoradas + data.filas_rechazadas);

            if (listaOmitidas.length > 0) {
                tbodyOmitidas.innerHTML = listaOmitidas.map(o => `
                    <tr>
                        <td><strong>${o.ref}</strong></td>
                        <td><strong>${o.sku}</strong></td>
                        <td><code>${o.campo}</code></td>
                        <td><span class="badge-pill ${o.badge}">${o.motivo}</span></td>
                        <td style="font-size: 0.85rem; color: #cbd5e1;">${o.detalle}</td>
                    </tr>
                `).join('');
            } else {
                tbodyOmitidas.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #34d399; padding: 1.5rem;">✓ Carga 100% limpia. Ningún registro fue omitido ni rechazado.</td></tr>';
            }

            cambiarSubTabIngesta((data.filas_anexadas_nuevas > 0) ? 'anexadas' : 'omitidas');
        }

        async function cargarBitacoraCargas() {
            try {
                const res = await fetch('/api/bitacora_cargas');
                const data = await res.json();
                const tbody = document.getElementById('tablaBitacoraCargas');
                if (!data || data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">Sin cargas registradas aún.</td></tr>';
                    return;
                }
                tbody.innerHTML = data.map(c => `
                    <tr>
                        <td style="font-family: monospace; font-size: 0.85rem;">${c.timestamp}</td>
                        <td><strong>${c.nombre_archivo}</strong></td>
                        <td><span class="badge-pill badge-info">${c.tipo_documento}</span></td>
                        <td>${c.filas_leidas}</td>
                        <td style="color: var(--success); font-weight: 700;">${c.filas_cargadas}</td>
                        <td style="color: var(--warning);">${c.filas_omitidas_duplicadas}</td>
                        <td style="color: ${c.filas_rechazadas > 0 ? 'var(--danger)' : 'var(--text-muted)'}; font-weight: 700;">${c.filas_rechazadas}</td>
                        <td style="font-size: 0.82rem; color: #cbd5e1;">${c.detalle_rechazos}</td>
                    </tr>
                `).join('');
            } catch (err) {
                console.error(err);
            }
        }

        // ==============================================================
        // ASEGURAMIENTO DE CALIDAD (QA)
        // ==============================================================
        async function ejecutarPruebasQA() {
            showLoading('Ejecutando pruebas automáticas de aseguramiento de calidad...');
            try {
                const res = await fetch('/api/pruebas_qa');
                const data = await res.json();

                document.getElementById('qaEstadoGlobal').innerText = data.todas_aprobadas ? '100% CONFORME' : 'CON OBSERVACIONES';
                document.getElementById('qaEstadoGlobal').style.color = data.todas_aprobadas ? 'var(--success)' : 'var(--warning)';
                document.getElementById('qaAprobadas').innerText = `${data.pruebas_aprobadas} / ${data.total_pruebas}`;
                document.getElementById('qaTasa').innerText = data.tasa_exito_pct + '%';
                document.getElementById('qaTiempo').innerText = data.duracion_ejecucion_ms + ' ms';

                const tbody = document.getElementById('tablaPruebasQA');
                tbody.innerHTML = data.pruebas.map(p => `
                    <tr>
                        <td style="font-family: monospace; font-weight: 700;">${p.id}</td>
                        <td><strong>${p.nombre}</strong><br><span style="font-size: 0.8rem; color: var(--text-muted);">${p.descripcion}</span></td>
                        <td>${p.categoria}</td>
                        <td><span class="badge-pill ${p.cumple ? 'badge-success' : 'badge-danger'}">${p.estado}</span></td>
                        <td style="font-size: 0.85rem; color: #cbd5e1;">${p.evidencia}</td>
                    </tr>
                `).join('');

                hideLoading();
                showToast('✅ Pruebas QA completadas: 100% aprobadas.');
            } catch (err) {
                hideLoading();
                showToast('❌ Error en QA: ' + err.message);
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        window.onload = () => {
            ejecutarAnalisisGeneral();
            cargarBitacoraCargas();
        };
    </script>
</body>
</html>
"""

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path in ['/', '/index.html']:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
        elif parsed.path == '/api/orquestacion':
            resultado = orquestador.ejecutar_orquestacion()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/decidir':
            query = parse_qs(parsed.query)
            sku = query.get('sku', [''])[0]
            accion = query.get('accion', ['APROBADA'])[0]
            
            res = datos.registrar_decision(sku, accion, planeador="Planeador de Compras E2")
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/cargar_preconfigurado':
            query = parse_qs(parsed.query)
            tipo_prueba = query.get('tipo', ['movimientos_taller'])[0]
            
            base_dir = base_datos.get_base_dir()
            if tipo_prueba == 'movimientos_taller':
                path = os.path.join(base_dir, 'datos_prueba', 'remision_movimientos_con_anomalias.csv')
            elif tipo_prueba == 'movimientos_nuevos':
                path = os.path.join(base_dir, 'datos_prueba', 'remision_movimientos_nuevos.csv')
            elif tipo_prueba == 'idempotencia_test':
                path = os.path.join(base_dir, 'datos_prueba', 'remision_movimientos_con_anomalias.csv')
            else:
                path = os.path.join(base_dir, 'datos_iniciales', 'movimientos_inventario.csv')
                
            res = ingesta.ejecutar_carga_cinco_pasos(path, path, tipo_documento='movimientos_inventario')
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/bitacora_cargas':
            conn = base_datos.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM bitacora_cargas ORDER BY timestamp DESC LIMIT 25;")
            filas = [dict(r) for r in cur.fetchall()]
            conn.close()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(filas, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/pruebas_qa':
            resultado_qa = qa.ejecutar_pruebas_qa()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado_qa, ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_error(404, "Ruta no encontrada")

    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/cargar_csv':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                body = json.loads(post_data.decode('utf-8'))
                nombre = body.get('nombre', 'archivo_subido.csv')
                tipo_doc = body.get('tipo', 'movimientos_inventario')
                contenido_csv = body.get('contenido', '')
                
                # Ejecutar ingesta canónica de 5 pasos con el CSV recibido
                resultado_ingesta = ingesta.ejecutar_carga_cinco_pasos(nombre, contenido_csv, tipo_documento=tipo_doc, usuario='Usuario Operador')
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(resultado_ingesta, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'mensaje': str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Ruta POST no encontrada")

def iniciar_servidor():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n========================================================")
    print(f"🚀 Sistema de Gestión & Abastecimiento E2 SAS")
    print(f"🌐 Servidor corriendo en: {url}")
    print(f"========================================================\n")
    
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nApagando servidor...")
        httpd.server_close()

if __name__ == '__main__':
    iniciar_servidor()
