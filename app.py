"""
APLICATIVO EMPRESARIAL DE GESTIÓN DE ABASTECIMIENTO, INVENTARIOS Y CONTROL
E2 SAS — Manufactura de Mobiliario Metálico para Oficina
Producción 4.0 · Énfasis II · Universidad de Medellín

Módulos integrados:
  1. Tablero de Control y Supervisión Humana (Criterio de Parada y Aprobación)
  2. Análisis de Demanda y Parámetros Analíticos (BOM, Pareto ABC, ROP, EOQ, SS)
  3. Centro de Ingesta y Validación CSV (Los 5 Pasos, Trazabilidad Fila a Fila e Idempotencia)
  4. Instrumentación y Telemetría del Sistema ("El Sistema se Mide Solo" y Bitácoras)
"""

import os
import sys
import json
import base64
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import orquestador
from nucleo import datos, ingesta, instrumentacion, base_datos

PORT = 8501

HTML_EMPRESARIAL = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2 SAS — Sistema Integral de Abastecimiento y Control Operativo</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-canvas: #090d16;
            --bg-surface: #111827;
            --bg-surface-elevated: #162032;
            --border-subtle: #1f293d;
            --border-focus: #3b82f6;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --primary-light: rgba(37, 99, 235, 0.12);
            --success: #10b981;
            --success-surface: rgba(16, 185, 129, 0.1);
            --success-border: rgba(16, 185, 129, 0.3);
            --warning: #f59e0b;
            --warning-surface: rgba(245, 158, 11, 0.1);
            --warning-border: rgba(245, 158, 11, 0.3);
            --danger: #ef4444;
            --danger-surface: rgba(239, 68, 68, 0.1);
            --danger-border: rgba(239, 68, 68, 0.3);
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --radius-md: 8px;
            --radius-lg: 12px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        body { background-color: var(--bg-canvas); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }

        /* Navegación y Encabezado */
        header { background-color: var(--bg-surface); border-bottom: 1px solid var(--border-subtle); padding: 1rem 2rem; position: sticky; top: 0; z-index: 100; }
        .header-content { max-width: 1380px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .brand-block { display: flex; align-items: center; gap: 1rem; }
        .brand-logo { background: var(--primary); color: #fff; font-weight: 700; font-size: 1rem; padding: 0.4rem 0.75rem; border-radius: var(--radius-md); letter-spacing: 0.5px; }
        .brand-titles h1 { font-size: 1.15rem; font-weight: 600; color: var(--text-main); }
        .brand-titles p { font-size: 0.8rem; color: var(--text-secondary); }

        .nav-tabs { display: flex; gap: 0.5rem; background: var(--bg-canvas); padding: 0.3rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); }
        .tab-btn { background: transparent; border: none; color: var(--text-secondary); padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 0.5rem; }
        .tab-btn:hover { color: var(--text-main); }
        .tab-btn.active { background: var(--bg-surface-elevated); color: #fff; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); }

        /* Contenedor Principal */
        main { max-width: 1380px; width: 100%; margin: 1.5rem auto; padding: 0 2rem; flex: 1; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Tarjetas y Paneles */
        .card { background-color: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle); }
        .card-title { font-size: 1.05rem; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem; }
        .card-subtitle { font-size: 0.825rem; color: var(--text-secondary); margin-top: 0.2rem; }

        /* Grid de KPIs */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .kpi-card { background-color: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.25rem; }
        .kpi-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 0.5rem; }
        .kpi-value { font-size: 1.85rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: var(--text-main); }
        .kpi-footer { font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.5rem; display: flex; align-items: center; gap: 0.4rem; }
        .kpi-badge { padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 600; font-size: 0.7rem; }
        .badge-success { background: var(--success-surface); color: var(--success); border: 1px solid var(--success-border); }
        .badge-warning { background: var(--warning-surface); color: var(--warning); border: 1px solid var(--warning-border); }
        .badge-danger { background: var(--danger-surface); color: var(--danger); border: 1px solid var(--danger-border); }
        .badge-neutral { background: var(--primary-light); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.25); }

        /* Banners Semánticos */
        .alert-banner { border-radius: var(--radius-md); padding: 1rem 1.25rem; margin-bottom: 1.5rem; display: flex; align-items: flex-start; gap: 0.85rem; }
        .alert-warning { background-color: var(--warning-surface); border: 1px solid var(--warning-border); color: #fef3c7; }
        .alert-success { background-color: var(--success-surface); border: 1px solid var(--success-border); color: #d1fae5; }
        .alert-title { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.2rem; }
        .alert-body { font-size: 0.85rem; color: #cbd5e1; line-height: 1.45; }

        /* Tablas */
        .table-responsive { overflow-x: auto; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--bg-surface); }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }
        th { background-color: var(--bg-surface-elevated); color: var(--text-secondary); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; padding: 0.85rem 1rem; border-bottom: 1px solid var(--border-subtle); white-space: nowrap; }
        td { padding: 0.85rem 1rem; border-bottom: 1px solid var(--border-subtle); vertical-align: middle; color: var(--text-main); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background-color: rgba(255, 255, 255, 0.015); }
        .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }

        /* Botones */
        .btn { padding: 0.55rem 1.1rem; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: all 0.15s ease-in-out; display: inline-flex; align-items: center; gap: 0.5rem; border: 1px solid transparent; }
        .btn-primary { background-color: var(--primary); color: #fff; }
        .btn-primary:hover { background-color: var(--primary-hover); }
        .btn-outline { background-color: transparent; border-color: var(--border-subtle); color: var(--text-secondary); }
        .btn-outline:hover { color: var(--text-main); border-color: var(--text-secondary); background: rgba(255, 255, 255, 0.02); }
        .btn-success { background-color: var(--success); color: #fff; }
        .btn-success:hover { background-color: #059669; }
        .btn-danger-outline { background: transparent; border: 1px solid var(--danger-border); color: #f87171; }
        .btn-danger-outline:hover { background: var(--danger-surface); }
        .btn-sm { padding: 0.35rem 0.65rem; font-size: 0.75rem; border-radius: 6px; }

        /* Formularios y Carga */
        .form-group { margin-bottom: 1rem; }
        .form-label { display: block; font-size: 0.8rem; font-weight: 500; color: var(--text-secondary); margin-bottom: 0.35rem; }
        .form-select, .form-input { width: 100%; max-width: 320px; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); color: var(--text-main); padding: 0.5rem 0.75rem; border-radius: var(--radius-md); font-size: 0.85rem; }
        .form-select:focus, .form-input:focus { outline: none; border-color: var(--border-focus); }
        
        .dropzone { border: 2px dashed var(--border-subtle); border-radius: var(--radius-lg); padding: 2rem; text-align: center; background: rgba(255, 255, 255, 0.01); transition: all 0.2s; cursor: pointer; }
        .dropzone:hover { border-color: var(--primary); background: var(--primary-light); }
        .dropzone-icon { width: 40px; height: 40px; margin: 0 auto 0.75rem; color: var(--text-secondary); }

        /* Barra de Filtros */
        .filter-bar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
        .search-input { min-width: 250px; background: var(--bg-surface); border: 1px solid var(--border-subtle); color: var(--text-main); padding: 0.5rem 0.85rem; border-radius: var(--radius-md); font-size: 0.85rem; }

        /* Justificación Ejecutiva */
        .justification-card { background: rgba(0, 0, 0, 0.2); border-left: 3px solid var(--primary); padding: 0.65rem 0.85rem; border-radius: 4px; font-size: 0.825rem; line-height: 1.45; color: #cbd5e1; margin-top: 0.35rem; }

        /* Notificación Toast */
        #toast { position: fixed; bottom: 2rem; right: 2rem; background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); color: #fff; padding: 0.85rem 1.25rem; border-radius: var(--radius-md); box-shadow: 0 10px 25px rgba(0,0,0,0.5); font-size: 0.85rem; display: none; z-index: 9999; }
        
        /* Spinner */
        .spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <header>
        <div class="header-content">
            <div class="brand-block">
                <div class="brand-logo">E2 SAS</div>
                <div class="brand-titles">
                    <h1>Mobiliario Metálico para Oficina — Control de Abastecimiento</h1>
                    <p>Producción 4.0 · Sistema Asistido de Reposición e Ingesta Idempotente</p>
                </div>
            </div>
            <nav class="nav-tabs">
                <button class="tab-btn active" onclick="cambiarPestana('tab-control')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
                    Tablero de Control
                </button>
                <button class="tab-btn" onclick="cambiarPestana('tab-demanda')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                    Demanda y Parámetros
                </button>
                <button class="tab-btn" onclick="cambiarPestana('tab-ingesta')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    Ingesta de Datos (5 Pasos)
                </button>
                <button class="tab-btn" onclick="cambiarPestana('tab-telemetria')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    Instrumentación y Auditoría
                </button>
            </nav>
        </div>
    </header>

    <main>
        <!-- ======================================================== -->
        <!-- PESTAÑA 1: TABLERO DE CONTROL Y SUPERVISIÓN HUMANA        -->
        <!-- ======================================================== -->
        <div id="tab-control" class="tab-content active">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <div>
                    <h2 style="font-size: 1.25rem; font-weight: 600;">Estado General de la Operación</h2>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">Supervisión de inventario físico, reconciliación contable y generación de órdenes de compra.</p>
                </div>
                <div>
                    <button id="btnEjecutarOrquestacion" class="btn btn-primary" onclick="ejecutarAnalisisIntegral()">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        <span>Ejecutar Análisis Integral</span>
                    </button>
                </div>
            </div>

            <!-- Grid de Indicadores Clave -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Exactitud de Inventario (ERI)</div>
                    <div id="kpiEri" class="kpi-value">-- %</div>
                    <div class="kpi-footer">
                        <span id="badgeEri" class="kpi-badge badge-neutral">Tolerancia ±5%</span>
                        <span>Saldo Kardex vs Físico</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Materiales en Riesgo de Quiebre</div>
                    <div id="kpiQuiebres" class="kpi-value" style="color: #f87171;">--</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-danger">Stock Real ≤ ROP</span>
                        <span>Requiere reposición</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Presupuesto Sugerido (EOQ)</div>
                    <div id="kpiInversion" class="kpi-value" style="font-size: 1.55rem; color: #60a5fa;">$ --</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-neutral">Costo de Emisión $80k</span>
                        <span>Lote Económico</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Discrepancias de Bodega</div>
                    <div id="kpiDiscrepancias" class="kpi-value" style="color: #fbbf24;">--</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-warning">Desfases Auditados</span>
                        <span>Fantasmas y Muelle</span>
                    </div>
                </div>
            </div>

            <!-- Banner de Criterio de Parada y Supervisión Humana -->
            <div id="bannerSupervision" class="alert-banner alert-warning">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 2px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <div>
                    <div id="supervisionTitulo" class="alert-title">Supervisión Requerida — Criterio de Parada Activo</div>
                    <div id="supervisionMensaje" class="alert-body">
                        El sistema ha detectado necesidades críticas de abastecimiento. Por política corporativa, ninguna orden de compra compromete recursos financieros sin la aprobación explícita del planeador.
                    </div>
                </div>
            </div>

            <!-- Tabla de Propuestas de Compra -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Recomendaciones de Abastecimiento Emitidas por el Asistente</div>
                        <div class="card-subtitle">Analice la justificación analítica y confirme o desestime cada requerimiento para asentar en la base de datos.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Insumo / Referencia</th>
                                <th>Clasificación</th>
                                <th>Stock Físico</th>
                                <th>Punto Reorden (ROP)</th>
                                <th>Cantidad Sugerida (EOQ)</th>
                                <th style="width: 44%;">Justificación Analítica Cuantitativa</th>
                                <th>Acción Requerida</th>
                            </tr>
                        </thead>
                        <tbody id="tablaPropuestasBody">
                            <tr>
                                <td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                                    Presione <strong>"Ejecutar Análisis Integral"</strong> para evaluar el estado actual del inventario.
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- PESTAÑA 2: ANÁLISIS DE DEMANDA Y PARÁMETROS               -->
        <!-- ======================================================== -->
        <div id="tab-demanda" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Distribución Pareto ABC de Materiales (Demanda por Valor D × Cu)</div>
                        <div class="card-subtitle">Segmentación financiera acumulada según la metodología 80-15-5.</div>
                    </div>
                </div>
                <div class="kpi-grid" id="paretoGrid">
                    <div class="kpi-card">
                        <div class="kpi-label">Clase A (Alta Inversión)</div>
                        <div id="paretoA_skus" class="kpi-value" style="color: #f87171;">-- SKUs</div>
                        <div id="paretoA_valor" class="kpi-footer">$ -- COP (80% valor)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Clase B (Inversión Media)</div>
                        <div id="paretoB_skus" class="kpi-value" style="color: #fbbf24;">-- SKUs</div>
                        <div id="paretoB_valor" class="kpi-footer">$ -- COP (15% valor)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Clase C (Baja Inversión)</div>
                        <div id="paretoC_skus" class="kpi-value" style="color: #34d399;">-- SKUs</div>
                        <div id="paretoC_valor" class="kpi-footer">$ -- COP (5% valor)</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Matriz Detallada de Reposición y Explosión BOM</div>
                        <div class="card-subtitle">Cálculos matemáticos de consumo diario (d), variabilidad (σd), stock de seguridad (SS) y punto de reorden (ROP).</div>
                    </div>
                    <div class="filter-bar">
                        <input type="text" id="filtroSkuDemanda" class="search-input" placeholder="Buscar material o SKU..." oninput="filtrarTablaDemanda()">
                        <select id="filtroClaseAbc" class="form-select" style="max-width: 140px;" onchange="filtrarTablaDemanda()">
                            <option value="">Todas las clases</option>
                            <option value="A">Clase A</option>
                            <option value="B">Clase B</option>
                            <option value="C">Clase C</option>
                        </select>
                    </div>
                </div>
                <div class="table-responsive" style="max-height: 520px;">
                    <table>
                        <thead>
                            <tr>
                                <th>SKU</th>
                                <th>Descripción</th>
                                <th>Familia</th>
                                <th>Clase</th>
                                <th>Demanda Anual (D)</th>
                                <th>Consumo Diario (d)</th>
                                <th>Desviación (σd)</th>
                                <th>Lead Time (LT)</th>
                                <th>Stock Seg. (SS)</th>
                                <th>Punto Reorden (ROP)</th>
                                <th>Lote Econ. (EOQ)</th>
                                <th>Stock Actual</th>
                            </tr>
                        </thead>
                        <tbody id="tablaDemandaBody">
                            <tr><td colspan="12" style="text-align: center; padding: 2rem; color: var(--text-muted);">Cargando matriz analítica...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- PESTAÑA 3: CENTRO DE INGESTA Y VALIDACIÓN CSV (5 PASOS)   -->
        <!-- ======================================================== -->
        <div id="tab-ingesta" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Flujo de Ingesta y Validación en Cinco Pasos</div>
                        <div class="card-subtitle">Procesamiento determinístico, validación estructural, normalización y escritura idempotente en base de datos.</div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                    <div>
                        <div class="form-group">
                            <label class="form-label">Tipo de Documento a Procesar:</label>
                            <select id="ingestaTipoDoc" class="form-select" onchange="limpiarEstadoIngesta()">
                                <option value="movimientos_inventario">Movimientos de Inventario (Kardex Transaccional)</option>
                                <option value="ordenes_compra">Órdenes de Compra (Histórico de Adquisiciones)</option>
                                <option value="conteo_fisico">Conteo Físico Auditado en Bodega</option>
                                <option value="maestro_materiales">Catálogo Maestro de Materiales</option>
                            </select>
                        </div>

                        <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
                            <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem;">Haga clic o arrastre el archivo CSV aquí</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">Archivos delimitados por coma o punto y coma (.csv)</div>
                            <input type="file" id="fileInput" accept=".csv" style="display: none;" onchange="manejarSeleccionArchivo(this.files[0])">
                        </div>

                        <div id="archivoMeta" style="margin-top: 0.75rem; font-size: 0.825rem; color: var(--text-secondary); display: none;">
                            Archivo: <strong id="lblNombreArchivo" style="color: #fff;">--</strong> (<span id="lblTamanoArchivo">-- KB</span>)
                        </div>

                        <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                            <button id="btnPrevisualizar" class="btn btn-outline" onclick="iniciarPrevisualizacion()" disabled>
                                <span>Paso 1 y 2: Validar y Previsualizar</span>
                            </button>
                            <button id="btnConfirmarCarga" class="btn btn-primary" onclick="confirmarIngesta()" disabled>
                                <span>Paso 3, 4 y 5: Normalizar y Asentar</span>
                            </button>
                        </div>
                    </div>

                    <div>
                        <div class="card" style="background: var(--bg-surface-elevated); margin-bottom: 0; height: 100%;">
                            <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem;">Diagnóstico Estructural de Entrada</div>
                            <div id="diagnosticoEstructural" style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
                                Seleccione un archivo CSV para inspeccionar delimitadores, codificación y verificar la presencia de las columnas requeridas según el modelo relacional.
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Resumen de Rendición de Cuentas (Paso 4) -->
                <div id="panelRendicionCuentas" style="display: none; margin-top: 1.5rem;">
                    <div class="kpi-grid">
                        <div class="kpi-card">
                            <div class="kpi-label">Filas Leídas del Archivo</div>
                            <div id="rcLeidas" class="kpi-value">0</div>
                            <div class="kpi-footer">Total de registros evaluados</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Filas Insertadas en Base</div>
                            <div id="rcInsertadas" class="kpi-value" style="color: #34d399;">0</div>
                            <div class="kpi-footer">Transacciones nuevas agregadas</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Omitidas por Idempotencia</div>
                            <div id="rcOmitidas" class="kpi-value" style="color: #60a5fa;">0</div>
                            <div class="kpi-footer">Duplicados prevenidos</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Filas Rechazadas</div>
                            <div id="rcRechazadas" class="kpi-value" style="color: #f87171;">0</div>
                            <div class="kpi-footer">Fechas o datos corruptos</div>
                        </div>
                    </div>

                    <!-- Trazabilidad Fila a Fila -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0;">
                        <div style="font-weight: 600; font-size: 0.95rem;">Auditoría y Trazabilidad Fila a Fila</div>
                        <div class="filter-bar" style="margin-bottom: 0;">
                            <select id="filtroEstadoFila" class="form-select" style="max-width: 180px;" onchange="filtrarTrazabilidad()">
                                <option value="">Todos los estados</option>
                                <option value="INSERTADA">Insertadas</option>
                                <option value="OMITIDA">Omitidas / Duplicadas</option>
                                <option value="RECHAZADA">Rechazadas</option>
                            </select>
                            <button class="btn btn-outline btn-sm" onclick="descargarInformeAuditoria()">Descargar Reporte CSV</button>
                        </div>
                    </div>

                    <div class="table-responsive" style="max-height: 400px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Fila</th>
                                    <th>Identificador</th>
                                    <th>Estado Final</th>
                                    <th>Motivo del Resultado</th>
                                    <th>Detalle Pericial</th>
                                </tr>
                            </thead>
                            <tbody id="tablaTrazabilidadBody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- PESTAÑA 4: INSTRUMENTACIÓN Y AUDITORÍA                   -->
        <!-- ======================================================== -->
        <div id="tab-telemetria" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Instrumentación del Sistema — "El Sistema se Mide Solo"</div>
                        <div class="card-subtitle">Cinco dimensiones de telemetría operativa para control continuo y autodiagnóstico.</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="cargarMetricasInstrumentacion()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                        Actualizar Métricas
                    </button>
                </div>

                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">1. Calidad del Dato de Entrada</div>
                        <div id="teleTasaRechazo" class="kpi-value">0.0 %</div>
                        <div class="kpi-footer">Tasa de rechazo en cargas</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">2. Trabajo Ahorrado</div>
                        <div id="teleHorasAhorro" class="kpi-value" style="color: #60a5fa;">-- h</div>
                        <div class="kpi-footer">Horas estimadas de planeación</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">3. Calibración de Paradas</div>
                        <div id="teleTasaParadas" class="kpi-value" style="color: #fbbf24;">-- %</div>
                        <div class="kpi-footer">Corridas con parada activa</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">4. Tasa de Acierto Humano</div>
                        <div id="teleAciertoHumano" class="kpi-value" style="color: #34d399;">-- %</div>
                        <div class="kpi-footer">Órdenes autorizadas por planeador</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">5. Costo Computacional</div>
                        <div id="teleTiempoProm" class="kpi-value" style="font-size: 1.55rem;">-- ms</div>
                        <div class="kpi-footer">Tiempo medio de ejecución</div>
                    </div>
                </div>
            </div>

            <!-- Bitácora de Corridas -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Bitácora Oficial de Corridas de Orquestación</div>
                        <div class="card-subtitle">Registro transaccional de ejecuciones del sistema con fecha, duración y resultado.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha y Hora</th>
                                <th>ID Corrida</th>
                                <th>Duración</th>
                                <th>SKUs Evaluados</th>
                                <th>ERI Global</th>
                                <th>Quiebres</th>
                                <th>Inversión COP</th>
                                <th>Estado de Parada</th>
                            </tr>
                        </thead>
                        <tbody id="tablaBitacoraCorridasBody">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay registros históricos en la bitácora.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Bitácora de Cargas -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Bitácora Oficial de Ingesta de Archivos</div>
                        <div class="card-subtitle">Historial de archivos procesados, filas leídas, aceptadas y rechazadas.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha y Hora</th>
                                <th>Archivo</th>
                                <th>Tipo de Documento</th>
                                <th>Leídas</th>
                                <th>Insertadas</th>
                                <th>Omitidas (Idempotencia)</th>
                                <th>Rechazadas</th>
                                <th>Detalle Pericial</th>
                            </tr>
                        </thead>
                        <tbody id="tablaBitacoraCargasBody">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay registros de ingesta aún.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <div id="toast"></div>

    <script>
        let archivoSeleccionadoContenido = null;
        let archivoSeleccionadoNombre = '';
        let trazabilidadActual = [];
        let matrizDemandaActual = [];

        function cambiarPestana(idTab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(idTab).classList.add('active');
            
            // Marcar botón activo
            const idx = ['tab-control', 'tab-demanda', 'tab-ingesta', 'tab-telemetria'].indexOf(idTab);
            document.querySelectorAll('.tab-btn')[idx].classList.add('active');

            if (idTab === 'tab-demanda' && matrizDemandaActual.length === 0) {
                cargarMatrizDemanda();
            } else if (idTab === 'tab-telemetria') {
                cargarMetricasInstrumentacion();
            }
        }

        async function ejecutarAnalisisIntegral() {
            const btn = document.getElementById('btnEjecutarOrquestacion');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Ejecutando análisis...';

            try {
                const res = await fetch('/api/correr');
                const data = await res.json();
                renderTableroControl(data);
                showToast('Análisis integral completado exitosamente.');
            } catch (err) {
                showToast('Error al ejecutar análisis: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> <span>Ejecutar Análisis Integral</span>';
            }
        }

        function renderTableroControl(data) {
            if (data.status !== 'completado') {
                showToast('Atención: ' + data.mensaje);
                return;
            }

            const kpis = data.kpis;
            document.getElementById('kpiEri').innerText = kpis.eri_global_pct + ' %';
            document.getElementById('kpiQuiebres').innerText = kpis.skus_en_quiebre;
            document.getElementById('kpiInversion').innerText = '$ ' + Number(kpis.inversion_propuesta_cop).toLocaleString('es-CO');
            document.getElementById('kpiDiscrepancias').innerText = (kpis.materiales_fantasmas_detectados + kpis.desfases_muelle_detectados);

            const banner = document.getElementById('bannerSupervision');
            const titulo = document.getElementById('supervisionTitulo');
            const msg = document.getElementById('supervisionMensaje');
            if (data.criterio_parada_activado) {
                banner.className = 'alert-banner alert-warning';
                titulo.innerText = 'Supervisión Requerida — Criterio de Parada Activo';
                msg.innerText = data.mensaje_parada;
            } else {
                banner.className = 'alert-banner alert-success';
                titulo.innerText = 'Operación en Parámetros Normales';
                msg.innerText = 'No se registraron quiebres de inventario inminentes. Los saldos satisfacen los puntos de reorden vigentes.';
            }

            const tbody = document.getElementById('tablaPropuestasBody');
            tbody.innerHTML = '';

            if (data.propuestas_compra.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: #10b981;">No hay insumos que requieran reorden en este ciclo de operación.</td></tr>';
                return;
            }

            data.propuestas_compra.forEach(p => {
                const tr = document.createElement('tr');
                tr.id = 'propuesta-' + p.sku;
                tr.innerHTML = `
                    <td>
                        <span class="mono" style="font-weight: 700; color: #60a5fa;">${p.sku}</span><br>
                        <strong>${p.descripcion}</strong><br>
                        <small style="color: var(--text-secondary);">${p.categoria}</small>
                    </td>
                    <td>
                        <span class="kpi-badge ${p.clase_abc === 'A' ? 'badge-danger' : (p.clase_abc === 'B' ? 'badge-warning' : 'badge-success')}">
                            Clase ${p.clase_abc}
                        </span><br>
                        <small style="color: var(--text-muted);">Prioridad ${p.prioridad || 'Media'}</small>
                    </td>
                    <td><span class="mono">${Number(p.stock_real).toLocaleString('es-CO')}</span> ${p.unidad || 'und'}</td>
                    <td><span class="mono" style="color: #fbbf24;">${Number(p.punto_reorden_rop).toLocaleString('es-CO')}</span> ${p.unidad || 'und'}</td>
                    <td>
                        <strong class="mono" style="color: #60a5fa; font-size: 1.05rem;">${Number(p.cantidad_sugerida_eoq).toLocaleString('es-CO')}</strong> ${p.unidad || 'und'}<br>
                        <small style="color: var(--text-muted);">$ ${Number(p.inversion_estimada_cop).toLocaleString('es-CO')}</small>
                    </td>
                    <td>
                        <div class="justification-card">
                            ${p.justificacion_ejecutiva}
                        </div>
                    </td>
                    <td id="acciones-${p.sku}" style="white-space: nowrap;">
                        <button class="btn btn-success btn-sm" onclick="tomarDecision('${p.sku}', 'APROBADA')">Autorizar</button>
                        <button class="btn btn-danger-outline btn-sm" onclick="tomarDecision('${p.sku}', 'RECHAZADA')">Desestimar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function tomarDecision(sku, accion) {
            try {
                const res = await fetch(`/api/decidir?sku=${sku}&accion=${accion}`);
                const data = await res.json();
                const celda = document.getElementById('acciones-' + sku);
                if (accion === 'APROBADA') {
                    celda.innerHTML = '<span style="color: #10b981; font-weight: 600;">✓ Orden Autorizada</span>';
                    showToast(`Orden de compra para ${sku} autorizada y asentada en base.`);
                } else {
                    celda.innerHTML = '<span style="color: #f87171; font-weight: 600;">✕ Orden Desestimada</span>';
                    showToast(`Recomendación para ${sku} desestimada.`);
                }
            } catch (err) {
                showToast('Error al registrar decisión: ' + err.message);
            }
        }

        async function cargarMatrizDemanda() {
            try {
                const res = await fetch('/api/demanda');
                const data = await res.json();
                matrizDemandaActual = data.materiales;

                // Actualizar Pareto
                const p = data.resumen_abc;
                document.getElementById('paretoA_skus').innerText = p.A.skus + ' SKUs';
                document.getElementById('paretoA_valor').innerText = '$ ' + Number(p.A.valor_cop).toLocaleString('es-CO') + ' COP (' + p.A.pct_valor.toFixed(1) + '%)';
                document.getElementById('paretoB_skus').innerText = p.B.skus + ' SKUs';
                document.getElementById('paretoB_valor').innerText = '$ ' + Number(p.B.valor_cop).toLocaleString('es-CO') + ' COP (' + p.B.pct_valor.toFixed(1) + '%)';
                document.getElementById('paretoC_skus').innerText = p.C.skus + ' SKUs';
                document.getElementById('paretoC_valor').innerText = '$ ' + Number(p.C.valor_cop).toLocaleString('es-CO') + ' COP (' + p.C.pct_valor.toFixed(1) + '%)';

                renderTablaDemanda(matrizDemandaActual);
            } catch (err) {
                console.error(err);
            }
        }

        function renderTablaDemanda(lista) {
            const tbody = document.getElementById('tablaDemandaBody');
            tbody.innerHTML = '';
            lista.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="mono" style="font-weight: 600; color: #60a5fa;">${m.sku}</td>
                    <td>${m.descripcion}</td>
                    <td><small style="color: var(--text-secondary);">${m.categoria}</small></td>
                    <td><span class="kpi-badge ${m.clasificacion_abc === 'A' ? 'badge-danger' : (m.clasificacion_abc === 'B' ? 'badge-warning' : 'badge-success')}">Clase ${m.clasificacion_abc}</span></td>
                    <td class="mono">${Number(m.demanda_anual_d).toLocaleString('es-CO', {maximumFractionDigits: 1})}</td>
                    <td class="mono">${Number(m.consumo_diario_d).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono">${Number(m.sigma_diario).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono">${m.lead_time_usado} d</td>
                    <td class="mono" style="color: #34d399;">${Number(m.SS_95).toLocaleString('es-CO')}</td>
                    <td class="mono" style="color: #fbbf24; font-weight: 600;">${Number(m.ROP).toLocaleString('es-CO')}</td>
                    <td class="mono" style="color: #60a5fa; font-weight: 600;">${Number(m.EOQ).toLocaleString('es-CO')}</td>
                    <td class="mono">${Number(m.stock_real).toLocaleString('es-CO')}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filtrarTablaDemanda() {
            const query = document.getElementById('filtroSkuDemanda').value.toLowerCase();
            const clase = document.getElementById('filtroClaseAbc').value;
            const filtrados = matrizDemandaActual.filter(m => {
                const coincideTexto = m.sku.toLowerCase().includes(query) || m.descripcion.toLowerCase().includes(query) || m.categoria.toLowerCase().includes(query);
                const coincideClase = clase === '' || m.clasificacion_abc === clase;
                return coincideTexto && coincideClase;
            });
            renderTablaDemanda(filtrados);
        }

        // ==========================================
        // MÓDULO DE INGESTA (5 PASOS)
        // ==========================================
        function manejarSeleccionArchivo(file) {
            if (!file) return;
            archivoSeleccionadoNombre = file.name;
            const reader = new FileReader();
            reader.onload = (e) => {
                archivoSeleccionadoContenido = e.target.result;
                document.getElementById('lblNombreArchivo').innerText = file.name;
                document.getElementById('lblTamanoArchivo').innerText = (file.size / 1024).toFixed(1) + ' KB';
                document.getElementById('archivoMeta').style.display = 'block';
                document.getElementById('btnPrevisualizar').disabled = false;
                document.getElementById('btnConfirmarCarga').disabled = true;
            };
            reader.readAsText(file);
        }

        async function iniciarPrevisualizacion() {
            const tipo = document.getElementById('ingestaTipoDoc').value;
            const btn = document.getElementById('btnPrevisualizar');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Validando estructura...';

            try {
                const res = await fetch('/api/previsualizar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        nombre_archivo: archivoSeleccionadoNombre,
                        tipo_documento: tipo,
                        contenido: archivoSeleccionadoContenido
                    })
                });
                const data = await res.json();
                
                const diag = document.getElementById('diagnosticoEstructural');
                if (data.valido) {
                    diag.innerHTML = `
                        <div style="color: #34d399; font-weight: 600; margin-bottom: 0.5rem;">✓ Estructura de archivo conforme para importación</div>
                        <p><strong>Delimitador detectado:</strong> '${data.delimitador}' | <strong>Codificación:</strong> ${data.codificacion.toUpperCase()} | <strong>Filas leídas:</strong> ${data.filas_total}</p>
                        <p style="margin-top: 0.4rem; color: #cbd5e1;">Columnas requeridas presentes: <em>${data.columnas_esperadas.join(', ')}</em>.</p>
                    `;
                    document.getElementById('btnConfirmarCarga').disabled = false;
                    showToast('Validación estructural aprobada. Listo para asentar.');
                } else {
                    diag.innerHTML = `
                        <div style="color: #f87171; font-weight: 600; margin-bottom: 0.5rem;">✕ Inconsistencia en estructura del archivo</div>
                        <p>${data.mensaje}</p>
                    `;
                    document.getElementById('btnConfirmarCarga').disabled = true;
                }
            } catch (err) {
                showToast('Error en validación: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>Paso 1 y 2: Validar y Previsualizar</span>';
            }
        }

        async function confirmarIngesta() {
            const tipo = document.getElementById('ingestaTipoDoc').value;
            const btn = document.getElementById('btnConfirmarCarga');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Procesando e insertando...';

            try {
                const res = await fetch('/api/importar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        nombre_archivo: archivoSeleccionadoNombre,
                        tipo_documento: tipo,
                        contenido: archivoSeleccionadoContenido
                    })
                });
                const data = await res.json();
                
                // Mostrar panel de rendición de cuentas
                document.getElementById('panelRendicionCuentas').style.display = 'block';
                document.getElementById('rcLeidas').innerText = data.filas_leidas;
                document.getElementById('rcInsertadas').innerText = data.filas_insertadas;
                document.getElementById('rcOmitidas').innerText = data.filas_omitidas_duplicadas;
                document.getElementById('rcRechazadas').innerText = data.filas_rechazadas;

                trazabilidadActual = data.trazabilidad_filas || [];
                renderTablaTrazabilidad(trazabilidadActual);
                showToast(`Carga finalizada: ${data.filas_insertadas} nuevas insertadas, ${data.filas_omitidas_duplicadas} omitidas.`);
            } catch (err) {
                showToast('Error durante la importación: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>Paso 3, 4 y 5: Normalizar y Asentar</span>';
            }
        }

        function renderTablaTrazabilidad(filas) {
            const tbody = document.getElementById('tablaTrazabilidadBody');
            tbody.innerHTML = '';
            filas.forEach(f => {
                const tr = document.createElement('tr');
                const badgeClass = f.estado === 'INSERTADA' ? 'badge-success' : (f.estado.includes('OMITIDA') ? 'badge-neutral' : 'badge-danger');
                tr.innerHTML = `
                    <td class="mono">${f.fila}</td>
                    <td class="mono" style="font-weight: 600;">${f.identificador}</td>
                    <td><span class="kpi-badge ${badgeClass}">${f.estado}</span></td>
                    <td>${f.motivo}</td>
                    <td style="color: var(--text-secondary); font-size: 0.8rem;">${f.detalle}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filtrarTrazabilidad() {
            const estado = document.getElementById('filtroEstadoFila').value;
            const filtradas = estado === '' ? trazabilidadActual : trazabilidadActual.filter(f => f.estado.includes(estado));
            renderTablaTrazabilidad(filtradas);
        }

        function descargarInformeAuditoria() {
            if (trazabilidadActual.length === 0) return;
            let csvContent = "data:text/csv;charset=utf-8,Fila,Identificador,Estado,Motivo,Detalle\\n";
            trazabilidadActual.forEach(r => {
                csvContent += `"${r.fila}","${r.identificador}","${r.estado}","${r.motivo}","${r.detalle.replace(/"/g, '""')}"\\n`;
            });
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `auditoria_carga_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function limpiarEstadoIngesta() {
            document.getElementById('panelRendicionCuentas').style.display = 'none';
            document.getElementById('diagnosticoEstructural').innerText = 'Seleccione un archivo CSV para inspeccionar delimitadores, codificación y estructura.';
            document.getElementById('btnConfirmarCarga').disabled = true;
        }

        // ==========================================
        // MÓDULO DE TELEMETRÍA E INSTRUMENTACIÓN
        // ==========================================
        async function cargarMetricasInstrumentacion() {
            try {
                const res = await fetch('/api/instrumentacion');
                const data = await res.json();

                const c = data.instrumento_1_carga;
                document.getElementById('teleTasaRechazo').innerText = c.tasa_rechazo_pct.toFixed(1) + ' %';
                document.getElementById('teleHorasAhorro').innerText = data.instrumento_2_corrida.trabajo_ahorrado_horas_est + ' h';
                document.getElementById('teleTasaParadas').innerText = data.instrumento_3_paradas.tasa_paradas_pct.toFixed(0) + ' %';
                document.getElementById('teleAciertoHumano').innerText = data.instrumento_4_decision.tasa_acierto_pct.toFixed(0) + ' %';
                document.getElementById('teleTiempoProm').innerText = data.instrumento_5_costo.duracion_promedio_ms.toFixed(1) + ' ms';

                // Render Bitácora Corridas
                const tbodyCorridas = document.getElementById('tablaBitacoraCorridasBody');
                tbodyCorridas.innerHTML = '';
                if (data.bitacora_corridas.length === 0) {
                    tbodyCorridas.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay corridas registradas en la bitácora aún.</td></tr>';
                } else {
                    data.bitacora_corridas.forEach(c => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><small>${c.timestamp}</small></td>
                            <td class="mono" style="font-size: 0.75rem;">${c.id.substring(0, 12)}...</td>
                            <td class="mono">${c.duracion_ms} ms</td>
                            <td class="mono">${c.total_skus}</td>
                            <td class="mono">${c.eri_global_pct}%</td>
                            <td class="mono" style="color: #f87171; font-weight: 600;">${c.skus_en_quiebre}</td>
                            <td class="mono">$ ${Number(c.inversion_total_cop).toLocaleString('es-CO')}</td>
                            <td><span class="kpi-badge ${c.criterio_parada_activado ? 'badge-warning' : 'badge-success'}">${c.criterio_parada_activado ? 'Parada Activa' : 'Normal'}</span></td>
                        `;
                        tbodyCorridas.appendChild(tr);
                    });
                }

                // Render Bitácora Cargas
                const tbodyCargas = document.getElementById('tablaBitacoraCargasBody');
                tbodyCargas.innerHTML = '';
                if (data.bitacora_cargas.length === 0) {
                    tbodyCargas.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay ingestas registradas aún.</td></tr>';
                } else {
                    data.bitacora_cargas.forEach(cg => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><small>${cg.timestamp}</small></td>
                            <td><strong>${cg.nombre_archivo}</strong></td>
                            <td><small style="color: var(--text-secondary);">${cg.tipo_documento}</small></td>
                            <td class="mono">${cg.filas_leidas}</td>
                            <td class="mono" style="color: #34d399;">${cg.filas_cargadas}</td>
                            <td class="mono" style="color: #60a5fa;">${cg.filas_omitidas_duplicadas}</td>
                            <td class="mono" style="color: #f87171;">${cg.filas_rechazadas}</td>
                            <td style="font-size: 0.8rem; color: var(--text-secondary);">${cg.detalle_rechazos}</td>
                        `;
                        tbodyCargas.appendChild(tr);
                    });
                }
            } catch (err) {
                console.error(err);
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        // Carga inicial
        window.onload = () => {
            ejecutarAnalisisIntegral();
        };
    </script>
</body>
</html>
"""

class EnterpriseRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_EMPRESARIAL.encode('utf-8'))
            
        elif parsed.path == '/api/correr':
            resultado = orquestador.ejecutar_orquestacion()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/demanda':
            resultado = datos.obtener_analisis_demanda()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/decidir':
            query = parse_qs(parsed.query)
            sku = query.get('sku', [''])[0]
            accion = query.get('accion', ['APROBADA'])[0]
            corrida_id = query.get('corrida_id', [None])[0]
            
            res = datos.registrar_decision(sku, accion, planeador="Planeador de Compras E2", corrida_id=corrida_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/instrumentacion':
            res = instrumentacion.obtener_metricas_instrumentacion()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_error(404, "Ruta no encontrada")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}
            
        if parsed.path == '/api/previsualizar':
            nombre_archivo = payload.get('nombre_archivo', 'archivo.csv')
            tipo_documento = payload.get('tipo_documento', 'movimientos_inventario')
            contenido = payload.get('contenido', '')
            
            contenido_bytes = contenido.encode('utf-8') if isinstance(contenido, str) else b''
            res = ingesta.previsualizar_archivo(nombre_archivo, contenido_bytes, tipo_documento)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/importar':
            nombre_archivo = payload.get('nombre_archivo', 'archivo.csv')
            tipo_documento = payload.get('tipo_documento', 'movimientos_inventario')
            contenido = payload.get('contenido', '')
            
            res = ingesta.ejecutar_carga_cinco_pasos(nombre_archivo, contenido, tipo_documento)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_error(404, "Endpoint POST no encontrado")

def iniciar_servidor():
    base_datos.poblar_estado_inicial_si_vacio()
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, EnterpriseRequestHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n========================================================")
    print(f"  SISTEMA EMPRESARIAL DE GESTION DE INVENTARIOS E2 SAS")
    print(f"  Servidor local activo en: {url}")
    print(f"  Para finalizar la ejecucion: Presione Ctrl+C")
    print(f"========================================================\n")
    
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nFinalizando servidor local...")
        httpd.server_close()

if __name__ == '__main__':
    iniciar_servidor()
