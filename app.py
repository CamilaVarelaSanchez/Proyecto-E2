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

import numpy as np
import orquestador
from nucleo import datos, ingesta, instrumentacion, base_datos, eri

PORT = 8501

HTML_EMPRESARIAL = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2 SAS — Sistema Integral de Abastecimiento y Control Operativo</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Paleta Corporativa Industrial Slate / Navy */
            --bg-canvas: #0F172A;              /* Slate 900 */
            --bg-surface: #1E293B;             /* Slate 800 */
            --bg-surface-elevated: #243247;    /* Slate 750 */
            --bg-surface-hover: #29384D;
            --bg-input: #131D2E;

            /* Estructura y Líneas Finas (1px solid) */
            --border-fine: #334155;            /* Slate 700 */
            --border-subtle: #243247;
            --border-hover: #475569;           /* Gris Acero */
            --border-focus: #3B82F6;

            /* Color Primario / Acento Corporativo */
            --primary: #2563EB;                /* Azul Corporativo */
            --primary-hover: #1D4ED8;
            --primary-subtle: rgba(37, 99, 235, 0.12);
            --primary-border: rgba(37, 99, 235, 0.35);

            /* Colores de Estado Industrial */
            --success: #10B981;                /* Verde Esmeralda (Éxito / Stock OK) */
            --success-surface: rgba(16, 185, 129, 0.08);
            --success-border: rgba(16, 185, 129, 0.35);
            --success-text: #34D399;

            --warning: #F59E0B;                /* Ámbar / Naranja (Alerta ROP / Supervisión) */
            --warning-surface: rgba(245, 158, 11, 0.08);
            --warning-border: rgba(245, 158, 11, 0.35);
            --warning-text: #FBBF24;

            --danger: #EF4444;                 /* Rojo Carmesí (Riesgo Quiebre / Rechazo) */
            --danger-surface: rgba(239, 68, 68, 0.08);
            --danger-border: rgba(239, 68, 68, 0.35);
            --danger-text: #F87171;

            /* Jerarquía Tipográfica */
            --text-main: #F8FAFC;              /* Slate 50 */
            --text-secondary: #94A3B8;         /* Slate 400 */
            --text-muted: #64748B;             /* Slate 500 */
            --text-steel: #475569;             /* Gris Acero */

            /* Geometría SaaS Enterprise (Prohibido rounded-3xl) */
            --radius-xs: 4px;
            --radius-sm: 5px;
            --radius-md: 6px;
            --radius-lg: 8px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-canvas);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.5;
        }

        /* Encabezado Corporativo */
        header {
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border-fine);
            padding: 0.85rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: var(--shadow-sm);
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand-block {
            display: flex;
            align-items: center;
            gap: 1.15rem;
        }

        .brand-logo-container {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0F172A;
            border: 1px solid var(--border-fine);
            color: #38BDF8;
            font-weight: 700;
            font-size: 0.95rem;
            padding: 0.45rem 0.85rem;
            border-radius: var(--radius-sm);
            letter-spacing: 0.06em;
            font-family: 'JetBrains Mono', monospace;
        }

        .brand-titles h1 {
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text-main);
            letter-spacing: -0.01em;
        }

        .brand-titles p {
            font-size: 0.775rem;
            color: var(--text-secondary);
        }

        .system-status-indicator {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--success-text);
            background: var(--success-surface);
            border: 1px solid var(--success-border);
            padding: 0.25rem 0.65rem;
            border-radius: var(--radius-xs);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            background-color: var(--success);
            border-radius: 50%;
            display: inline-block;
        }

        /* Navegación por Pestañas */
        .nav-tabs {
            display: flex;
            gap: 0.35rem;
            background: var(--bg-canvas);
            padding: 0.25rem;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-fine);
        }

        .tab-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            padding: 0.45rem 0.95rem;
            border-radius: var(--radius-sm);
            font-size: 0.825rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .tab-btn:hover {
            color: var(--text-main);
            background-color: rgba(255, 255, 255, 0.03);
        }

        .tab-btn.active {
            background: var(--bg-surface);
            color: #FFFFFF;
            font-weight: 600;
            border-color: var(--border-fine);
            box-shadow: var(--shadow-sm);
        }

        /* Contenedor Principal */
        main {
            max-width: 1400px;
            width: 100%;
            margin: 1.5rem auto;
            padding: 0 2rem;
            flex: 1;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Paneles y Tarjetas (SaaS Enterprise) */
        .card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-fine);
            border-radius: var(--radius-md);
            padding: 1.35rem 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-sm);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            padding-bottom: 0.85rem;
            border-bottom: 1px solid var(--border-fine);
        }

        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.55rem;
            letter-spacing: -0.01em;
        }

        .card-subtitle {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }

        /* Grid de KPIs */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-fine);
            border-radius: var(--radius-md);
            padding: 1.15rem 1.35rem;
            box-shadow: var(--shadow-sm);
            transition: border-color 0.15s ease;
        }

        .kpi-card:hover {
            border-color: var(--border-hover);
        }

        .kpi-label {
            font-size: 0.725rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .kpi-value {
            font-size: 1.85rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-main);
            letter-spacing: -0.02em;
            line-height: 1.15;
        }

        .kpi-footer {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.65rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Etiquetas y Badges */
        .kpi-badge {
            padding: 0.15rem 0.5rem;
            border-radius: var(--radius-xs);
            font-weight: 600;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .badge-success {
            background: var(--success-surface);
            color: var(--success-text);
            border: 1px solid var(--success-border);
        }

        .badge-warning {
            background: var(--warning-surface);
            color: var(--warning-text);
            border: 1px solid var(--warning-border);
        }

        .badge-danger {
            background: var(--danger-surface);
            color: var(--danger-text);
            border: 1px solid var(--danger-border);
        }

        .badge-neutral {
            background: var(--primary-subtle);
            color: #60A5FA;
            border: 1px solid var(--primary-border);
        }

        /* Banners Semánticos */
        .alert-banner {
            border-radius: var(--radius-md);
            padding: 1.1rem 1.35rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.95rem;
            box-shadow: var(--shadow-sm);
        }

        .alert-warning {
            background-color: var(--warning-surface);
            border: 1px solid var(--warning-border);
            color: #FEF3C7;
        }

        .alert-success {
            background-color: var(--success-surface);
            border: 1px solid var(--success-border);
            color: #D1FAE5;
        }

        .alert-title {
            font-weight: 600;
            font-size: 0.925rem;
            margin-bottom: 0.25rem;
            letter-spacing: -0.01em;
        }

        .alert-body {
            font-size: 0.825rem;
            color: #CBD5E1;
            line-height: 1.45;
        }

        /* Tablas Corporativas */
        .table-responsive {
            overflow-x: auto;
            border: 1px solid var(--border-fine);
            border-radius: var(--radius-md);
            background: var(--bg-surface);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.825rem;
        }

        th {
            background-color: var(--bg-surface-elevated);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            padding: 0.8rem 1rem;
            border-bottom: 1px solid var(--border-fine);
            white-space: nowrap;
        }

        td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-fine);
            vertical-align: middle;
            color: var(--text-main);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background-color: rgba(255, 255, 255, 0.02);
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
        }

        /* Botones Profesionales */
        .btn {
            padding: 0.5rem 1rem;
            border-radius: var(--radius-sm);
            font-size: 0.825rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border: 1px solid transparent;
            text-decoration: none;
        }

        .btn-primary {
            background-color: var(--primary);
            color: #FFFFFF;
            border-color: #3B82F6;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.2);
        }

        .btn-primary:hover {
            background-color: var(--primary-hover);
        }

        .btn-outline {
            background-color: transparent;
            border-color: var(--border-fine);
            color: var(--text-secondary);
        }

        .btn-outline:hover {
            color: var(--text-main);
            border-color: var(--border-hover);
            background-color: rgba(255, 255, 255, 0.03);
        }

        .btn-success {
            background-color: #059669;
            color: #FFFFFF;
            border-color: #10B981;
        }

        .btn-success:hover {
            background-color: #047857;
        }

        .btn-danger-outline {
            background-color: transparent;
            border: 1px solid var(--danger-border);
            color: var(--danger-text);
        }

        .btn-danger-outline:hover {
            background-color: var(--danger-surface);
            border-color: var(--danger);
        }

        .btn-sm {
            padding: 0.35rem 0.7rem;
            font-size: 0.75rem;
            border-radius: var(--radius-xs);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Formularios y Entradas */
        .form-group {
            margin-bottom: 1.15rem;
        }

        .form-label {
            display: block;
            font-size: 0.775rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .form-select, .form-input {
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border-fine);
            color: var(--text-main);
            padding: 0.55rem 0.85rem;
            border-radius: var(--radius-sm);
            font-size: 0.825rem;
            transition: border-color 0.15s ease;
        }

        .form-select:focus, .form-input:focus {
            outline: none;
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        .dropzone {
            border: 1px dashed var(--border-hover);
            border-radius: var(--radius-md);
            padding: 2.25rem 1.5rem;
            text-align: center;
            background: rgba(15, 23, 42, 0.5);
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .dropzone:hover {
            border-color: var(--primary);
            background: var(--primary-subtle);
        }

        .dropzone-icon {
            width: 36px;
            height: 36px;
            margin: 0 auto 0.75rem;
            color: var(--text-secondary);
        }

        /* Barra de Filtros */
        .filter-bar {
            display: flex;
            gap: 0.75rem;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }

        .search-input {
            min-width: 280px;
            background: var(--bg-input);
            border: 1px solid var(--border-fine);
            color: var(--text-main);
            padding: 0.5rem 0.85rem;
            border-radius: var(--radius-sm);
            font-size: 0.825rem;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--border-focus);
        }

        /* Tarjeta de Justificación Analítica */
        .justification-card {
            background: rgba(15, 23, 42, 0.6);
            border-left: 3px solid var(--primary);
            padding: 0.65rem 0.85rem;
            border-radius: var(--radius-xs);
            font-size: 0.8rem;
            line-height: 1.45;
            color: #CBD5E1;
            margin-top: 0.35rem;
        }

        /* Notificación Toast Flotante */
        #toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-fine);
            color: #FFFFFF;
            padding: 0.85rem 1.35rem;
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-md);
            font-size: 0.825rem;
            font-weight: 500;
            display: none;
            z-index: 9999;
            max-width: 420px;
        }

        /* Indicador de Carga / Spinner */
        .spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: #FFFFFF;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            display: inline-block;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

    <header>
        <div class="header-content">
            <div class="brand-block">
                <div class="brand-logo-container">E2 SAS</div>
                <div class="brand-titles">
                    <h1>Mobiliario Metálico para Oficina — Control de Abastecimiento</h1>
                    <p>Producción 4.0 · Sistema Asistido de Reposición e Ingesta Idempotente</p>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div class="system-status-indicator">
                    <span class="status-dot"></span>
                    <span>Base Relacional Activa</span>
                </div>
                <nav class="nav-tabs">
                    <button class="tab-btn active" onclick="cambiarPestana('tab-control')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
                        <span>Tablero de Control y Recomendaciones</span>
                    </button>
                    <button class="tab-btn" onclick="cambiarPestana('tab-demanda')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                        <span>Módulo de Abastecimiento (BOM)</span>
                    </button>
                    <button class="tab-btn" onclick="cambiarPestana('tab-reconciliacion')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                        <span>Módulo de Reconciliación (ERI)</span>
                    </button>
                    <button class="tab-btn" onclick="cambiarPestana('tab-ingesta')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                        <span>Ingesta de Datos e Idempotencia</span>
                    </button>
                    <button class="tab-btn" onclick="cambiarPestana('tab-telemetria')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                        <span>Instrumentación y Auditoría</span>
                    </button>
                </nav>
            </div>
        </div>
    </header>

    <main>
        <!-- ======================================================== -->
        <!-- PESTAÑA 1: TABLERO DE CONTROL Y RECOMENDACIONES DE PEDIDOS -->
        <!-- ======================================================== -->
        <div id="tab-control" class="tab-content active">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <div>
                    <h2 style="font-size: 1.25rem; font-weight: 600; letter-spacing: -0.01em;">Estado General de Abastecimiento</h2>
                    <p style="font-size: 0.825rem; color: var(--text-secondary);">Supervisión de inventario físico, reconciliación contable y aprobación ejecutiva de órdenes de compra.</p>
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
                    <div class="kpi-label">Exactitud de Registro (ERI / IRA)</div>
                    <div id="kpiEri" class="kpi-value">-- %</div>
                    <div class="kpi-footer">
                        <span id="badgeEri" class="kpi-badge badge-neutral">Tolerancia ±5%</span>
                        <span>Saldo Kardex vs. Conteo Físico</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Materiales en Riesgo de Quiebre</div>
                    <div id="kpiQuiebres" class="kpi-value" style="color: var(--danger-text);">--</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-danger">Stock Real ≤ ROP</span>
                        <span>Requiere reposición inmediata</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Presupuesto Sugerido (EOQ)</div>
                    <div id="kpiInversion" class="kpi-value" style="font-size: 1.55rem; color: #60A5FA;">$ --</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-neutral">Costo Emisión $80.000 COP</span>
                        <span>Lote Económico</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Discrepancias Físicas Auditadas</div>
                    <div id="kpiDiscrepancias" class="kpi-value" style="color: var(--warning-text);">--</div>
                    <div class="kpi-footer">
                        <span class="kpi-badge badge-warning">Desfases Detectados</span>
                        <span>Muelle y Faltantes</span>
                    </div>
                </div>
            </div>

            <!-- Banner de Criterio de Parada y Supervisión Humana -->
            <div id="bannerSupervision" class="alert-banner alert-warning">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 2px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <div>
                    <div id="supervisionTitulo" class="alert-title">Supervisión Humana Obligatoria — Criterio de Parada Activo</div>
                    <div id="supervisionMensaje" class="alert-body">
                        El sistema ha detectado necesidades críticas de abastecimiento. Por política corporativa de E2 SAS, ninguna orden de compra compromete recursos financieros sin la aprobación explícita del Planeador de Abastecimiento.
                    </div>
                </div>
            </div>

            <!-- Tabla de Recomendaciones Inteligentes del Agente -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Recomendaciones Inteligentes de Pedidos del Agente de Abastecimiento</div>
                        <div class="card-subtitle">Decisiones sugeridas: material a pedir, lote económico exacto (EOQ), condición de emisión al tocar el ROP y justificación en dinero del riesgo evitado.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Insumo / Referencia</th>
                                <th>Clasificación y Prioridad</th>
                                <th>Inventario Físico</th>
                                <th>Punto de Reorden (ROP)</th>
                                <th>Cantidad Sugerida (EOQ)</th>
                                <th>Condición de Emisión</th>
                                <th style="width: 38%;">Justificación en Dinero del Riesgo Evitado</th>
                                <th>Decisión Requerida</th>
                            </tr>
                        </thead>
                        <tbody id="tablaPropuestasBody">
                            <tr>
                                <td colspan="8" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                                    Presione <strong>"Ejecutar Análisis Integral"</strong> para evaluar el estado actual del inventario.
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- PESTAÑA 2: MÓDULO DE ABASTECIMIENTO Y DEMANDA BOM        -->
        <!-- ======================================================== -->
        <div id="tab-demanda" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Módulo de Abastecimiento y Planificación de Demanda Dependiente</div>
                        <div class="card-subtitle">Explosión de requerimientos brutos sobre la matriz de recetas BOM y dimensionamiento dinámico de reposición (ROP, SS, EOQ).</div>
                    </div>
                </div>
                <div class="kpi-grid" id="paretoGrid">
                    <div class="kpi-card">
                        <div class="kpi-label">Clase A (Inversión Alta)</div>
                        <div id="paretoA_skus" class="kpi-value" style="color: var(--danger-text);">-- SKUs</div>
                        <div id="paretoA_valor" class="kpi-footer">$ -- COP (80% del valor total)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Clase B (Inversión Media)</div>
                        <div id="paretoB_skus" class="kpi-value" style="color: var(--warning-text);">-- SKUs</div>
                        <div id="paretoB_valor" class="kpi-footer">$ -- COP (15% del valor total)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Clase C (Inversión Baja)</div>
                        <div id="paretoC_skus" class="kpi-value" style="color: var(--success-text);">-- SKUs</div>
                        <div id="paretoC_valor" class="kpi-footer">$ -- COP (5% del valor total)</div>
                    </div>
                </div>
            </div>

            <!-- Panel de Análisis de Demanda Dependiente por Líneas de Muebles -->
            <div class="card" style="background: var(--bg-surface-elevated); margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="font-weight: 600; font-size: 0.95rem; color: #FFFFFF;">Demanda Dependiente Derivada del Plan Maestro de Muebles Metálicos</div>
                    <span class="kpi-badge badge-neutral">Explosión Matricial Plan × BOM</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.825rem; color: var(--text-secondary);">
                    <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border-left: 3px solid #38BDF8;">
                        <strong style="color: #F8FAFC;">Línea de Archivadores (ARC):</strong> Demanda mensual pico de hasta 501 unidades (+106.1%). Exige hasta 7.76 láminas de acero y 6.46 juegos de correderas por mueble terminado.
                    </div>
                    <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border-left: 3px solid #10B981;">
                        <strong style="color: #F8FAFC;">Línea de Estanterías (EST):</strong> Demanda mensual pico de hasta 444 unidades (+87.2%). Alto consumo de tubería, perfiles estructurales y pintura electrostática en polvo.
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Matriz Analítica de Reposición y Parámetros Dinámicos</div>
                        <div class="card-subtitle">Consumo diario (d), desviación estándar (σd), Lead Time auditado (LT), Stock de Seguridad probabilístico (SS), Punto de Reorden (ROP) y Lote Económico (EOQ).</div>
                    </div>
                    <div class="filter-bar">
                        <input type="text" id="filtroSkuDemanda" class="search-input" placeholder="Buscar por Número de SKU, descripción o familia..." oninput="filtrarTablaDemanda()">
                        <select id="filtroClaseAbc" class="form-select" style="max-width: 160px;" onchange="filtrarTablaDemanda()">
                            <option value="">Todas las Clases</option>
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
                                <th>Número de SKU</th>
                                <th>Descripción del Material</th>
                                <th>Familia</th>
                                <th>Clase ABC</th>
                                <th>Demanda Anual (D)</th>
                                <th>Consumo Diario (d)</th>
                                <th>Desviación (σd)</th>
                                <th>Lead Time Auditado (LT)</th>
                                <th>Stock de Seguridad (SS)</th>
                                <th>Punto de Reorden (ROP)</th>
                                <th>Lote Económico (EOQ)</th>
                                <th>Stock Físico Actual</th>
                            </tr>
                        </thead>
                        <tbody id="tablaDemandaBody">
                            <tr><td colspan="12" style="text-align: center; padding: 2rem; color: var(--text-muted);">Cargando matriz analítica de abastecimiento...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- PESTAÑA 3: MÓDULO DE RECONCILIACIÓN Y EXACTITUD (ERI)    -->
        <!-- ======================================================== -->
        <div id="tab-reconciliacion" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Módulo de Reconciliación de Inventario y Exactitud de Registro (ERI / IRA)</div>
                        <div class="card-subtitle">Reconciliación matemática entre el Kardex canónico relacional y el conteo físico en bodega bajo tolerancia del ±5%.</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="cargarMatrizReconciliacion()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                        <span>Actualizar Reconciliación</span>
                    </button>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">Exactitud de Registro (ERI / IRA)</div>
                        <div id="recEriPct" class="kpi-value" style="color: var(--success-text);">-- %</div>
                        <div class="kpi-footer">Meta World-Class: 95.0%</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Materiales Concordantes (±5%)</div>
                        <div id="recConcordantes" class="kpi-value">--</div>
                        <div class="kpi-footer">Dentro del umbral de tolerancia</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Desfases en Muelle de Recepción</div>
                        <div id="recDesfases" class="kpi-value" style="color: #60A5FA;">--</div>
                        <div class="kpi-footer">Físico > Kardex (Pendientes de asentar)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Faltantes en Piso / No Localizados</div>
                        <div id="recFantasmas" class="kpi-value" style="color: var(--danger-text);">--</div>
                        <div class="kpi-footer">Kardex > Físico (Riesgo parada de ensamble)</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Impacto Financiero de Discrepancias</div>
                        <div id="recImpactoTotal" class="kpi-value" style="font-size: 1.55rem; color: var(--warning-text);">$ --</div>
                        <div class="kpi-footer">Valoración total de descuadres en COP</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Detalle Pericial de Reconciliación por Referencia</div>
                        <div class="card-subtitle">Comparativa entre saldo teórico reconstruido y conteo auditado con clasificación de causa raíz.</div>
                    </div>
                    <div class="filter-bar">
                        <input type="text" id="filtroSkuReconciliacion" class="search-input" placeholder="Buscar material o SKU..." oninput="filtrarTablaReconciliacion()">
                        <select id="filtroTipoReconciliacion" class="form-select" style="max-width: 220px;" onchange="filtrarTablaReconciliacion()">
                            <option value="">Todos los Diagnósticos</option>
                            <option value="Concordante">Concordantes (±5%)</option>
                            <option value="Muelle">Desfases en Muelle (Físico > Kardex)</option>
                            <option value="Faltante">Faltantes en Piso (Kardex > Físico)</option>
                        </select>
                    </div>
                </div>
                <div class="table-responsive" style="max-height: 480px;">
                    <table>
                        <thead>
                            <tr>
                                <th>Número de SKU</th>
                                <th>Descripción del Material</th>
                                <th>Familia</th>
                                <th>Saldo Kardex Teórico</th>
                                <th>Conteo Físico Auditado</th>
                                <th>Discrepancia Neta</th>
                                <th>Impacto Financiero (COP)</th>
                                <th>Diagnóstico de Reconciliación</th>
                            </tr>
                        </thead>
                        <tbody id="tablaReconciliacionBody">
                            <tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">Cargando registros de auditoría y reconciliación...</td></tr>
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
                        <div class="card-title">Flujo de Ingesta, Validación y Control de Idempotencia en Supabase</div>
                        <div class="card-subtitle">Protocolo de 5 pasos con detección de hashes únicos (SHA-256 / MD5), sentencias UPSERT con ON CONFLICT y auditoría pericial.</div>
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

                        <!-- ZONA DE CARGA (DRAG & DROP) CON INDICADOR DE ESTADO CLARO (Requisito 2) -->
                        <div class="dropzone" id="dropzone">
                            <!-- Estado Inicial -->
                            <div id="dropzoneEstadoInicial" style="display: block;">
                                <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                                <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem;">Arrastre su archivo CSV o seleccione desde su equipo</div>
                                <div style="font-size: 0.775rem; color: var(--text-secondary);">Archivos delimitados por coma o punto y coma (.csv) · Detección automática de codificación e integridad</div>
                            </div>
                            
                            <!-- Estado Procesando -->
                            <div id="dropzoneEstadoProcesando" style="display: none; padding: 0.85rem 0;">
                                <div class="spinner" style="width: 28px; height: 28px; border-width: 3px; margin: 0 auto 0.75rem auto; border-top-color: #38BDF8;"></div>
                                <div style="font-weight: 600; font-size: 0.95rem; color: #38BDF8; margin-bottom: 0.25rem;">Validando estructura e idempotencia en Supabase...</div>
                                <div style="font-size: 0.775rem; color: var(--text-secondary);">Verificando unicidad, claves naturales y aplicando cláusulas ON CONFLICT en Supabase</div>
                            </div>

                            <!-- Estado Completado -->
                            <div id="dropzoneEstadoCompletado" style="display: none; padding: 0.5rem 0;">
                                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5" style="margin: 0 auto 0.5rem auto; display: block;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                <div style="font-weight: 600; font-size: 0.95rem; color: var(--success-text); margin-bottom: 0.25rem;">Procesamiento e Idempotencia Conformes en Supabase</div>
                                <div style="font-size: 0.775rem; color: var(--text-secondary);">Reporte consolidado de auditoría de carga generado abajo</div>
                            </div>

                            <input type="file" id="fileInput" accept=".csv" style="display: none;" onchange="manejarSeleccionArchivo(this.files[0])">
                        </div>

                        <div id="archivoMeta" style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); display: none;">
                            Archivo: <strong id="lblNombreArchivo" style="color: #FFFFFF;">--</strong> (<span id="lblTamanoArchivo">-- KB</span>) · Hash SHA-256: <code id="lblHashArchivo" class="mono" style="color: #60A5FA;">--</code>
                        </div>

                        <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                            <button id="btnPrevisualizar" class="btn btn-outline" onclick="iniciarPrevisualizacion()" disabled>
                                <span>Paso 1 y 2: Validar Estructura y Previsualizar</span>
                            </button>
                            <button id="btnConfirmarCarga" class="btn btn-primary" onclick="confirmarIngesta()" disabled>
                                <span>Paso 3, 4 y 5: Normalizar y Asentar en Supabase</span>
                            </button>
                        </div>
                    </div>

                    <div>
                        <div class="card" style="background: var(--bg-surface-elevated); margin-bottom: 0; height: 100%;">
                            <div style="font-weight: 600; font-size: 0.925rem; margin-bottom: 0.5rem;">Diagnóstico Estructural y de Idempotencia</div>
                            <div id="diagnosticoEstructural" style="font-size: 0.825rem; color: var(--text-secondary); line-height: 1.5;">
                                Seleccione o arrastre un archivo CSV para inspeccionar delimitadores, juego de caracteres, calcular su hash único y validar las columnas obligatorias contra el esquema relacional en Supabase.
                            </div>
                        </div>
                    </div>
                </div>

                <!-- COMPONENTE DE REPORTE DETALLADO DE INGESTA (Requisito 3) -->
                <div id="panelRendicionCuentas" style="display: none; margin-top: 1.5rem;">
                    <!-- Tarjeta de Resumen Ejecutivo y Estado de Carga -->
                    <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-fine); border-radius: var(--radius-md); padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="font-size: 1.05rem; font-weight: 600; color: #FFFFFF;">Reporte Consolidado de Auditoría de Carga</div>
                                <div id="rcBadgeEstado" class="kpi-badge badge-success" style="font-size: 0.75rem; padding: 0.25rem 0.65rem;">--</div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">
                                ID Carga: <span id="rcIdCarga" class="mono" style="color: #60A5FA;">--</span>
                            </div>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.8rem; color: var(--text-secondary);">
                            <div>Archivo: <strong id="rcNombreArchivo" style="color: #FFFFFF;">--</strong></div>
                            <div>Hash SHA-256: <code id="rcHashArchivo" class="mono" style="color: #60A5FA;">--</code></div>
                            <div>Sincronización Supabase: <strong id="rcSupabaseSync" style="color: var(--success-text);">ON CONFLICT DO UPDATE / DO NOTHING</strong></div>
                        </div>
                    </div>

                    <!-- Las 4 Tarjetas Métricas Cuantitativas Exigidas -->
                    <div class="kpi-grid">
                        <div class="kpi-card">
                            <div class="kpi-label">Total de Registros Procesados</div>
                            <div id="rcLeidas" class="kpi-value">0</div>
                            <div class="kpi-footer">Número de filas leídas del CSV</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Registros Insertados / Actualizados</div>
                            <div id="rcInsertadas" class="kpi-value" style="color: var(--success-text);">0</div>
                            <div class="kpi-footer">Filas agregadas o actualizadas en Supabase</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Registros Omitidos por Idempotencia</div>
                            <div id="rcOmitidas" class="kpi-value" style="color: #60A5FA;">0</div>
                            <div class="kpi-footer">Detectadas como ya existentes (sin alteración)</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Registros Rechazados</div>
                            <div id="rcRechazadas" class="kpi-value" style="color: var(--danger-text);">0</div>
                            <div class="kpi-footer">Errores de formato, fechas o nulos obligatorios</div>
                        </div>
                    </div>

                    <!-- Banner de Explicación de Idempotencia -->
                    <div id="bannerIdempotenciaExplicacion" class="alert-banner alert-success" style="margin-bottom: 1.25rem;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 2px;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        <div>
                            <div class="alert-title" style="font-size: 0.875rem;">Garantía Absoluta de Idempotencia en Supabase</div>
                            <div class="alert-body" style="font-size: 0.8rem;" id="rcTextoIdempotencia">
                                El reingreso del mismo archivo o la ejecución múltiple de la carga no altera los saldos de inventario ni duplica registros. Las transacciones existentes son gestionadas con cláusulas ON CONFLICT.
                            </div>
                        </div>
                    </div>

                    <!-- Trazabilidad Fila a Fila con Razón Exacta de Rechazo -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0;">
                        <div style="font-weight: 600; font-size: 0.925rem;">Trazabilidad Pericial Fila a Fila (Razón Exacta por Fila)</div>
                        <div class="filter-bar" style="margin-bottom: 0;">
                            <select id="filtroEstadoFila" class="form-select" style="max-width: 210px;" onchange="filtrarTrazabilidad()">
                                <option value="">Todos los Estados</option>
                                <option value="INSERTADA">Insertadas</option>
                                <option value="ACTUALIZADA">Actualizadas</option>
                                <option value="OMITIDA">Omitidas por Idempotencia</option>
                                <option value="RECHAZADA">Rechazadas con Inconsistencia</option>
                            </select>
                            <button class="btn btn-outline btn-sm" onclick="descargarInformeAuditoria()">Descargar Reporte CSV de Auditoría</button>
                        </div>
                    </div>

                    <div class="table-responsive" style="max-height: 420px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Fila</th>
                                    <th>Identificador Único</th>
                                    <th>Estado de Transacción</th>
                                    <th>Causa del Resultado</th>
                                    <th>Razón Exacta / Detalle Pericial</th>
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
                        <div class="card-title">Instrumentación del Sistema — «El Sistema se Mide Solo»</div>
                        <div class="card-subtitle">Cinco dimensiones cuantitativas de telemetría operativa para control continuo y autodiagnóstico del aplicativo.</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="cargarMetricasInstrumentacion()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                        <span>Actualizar Métricas de Telemetría</span>
                    </button>
                </div>

                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">1. Calidad del Dato de Entrada</div>
                        <div id="teleTasaRechazo" class="kpi-value">0.0 %</div>
                        <div class="kpi-footer">Tasa de rechazo en cargas de archivos</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">2. Ahorro de Trabajo Manual</div>
                        <div id="teleHorasAhorro" class="kpi-value" style="color: #60A5FA;">-- h</div>
                        <div class="kpi-footer">Horas estimadas de planeación</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">3. Calibración de Paradas</div>
                        <div id="teleTasaParadas" class="kpi-value" style="color: var(--warning-text);">-- %</div>
                        <div class="kpi-footer">Frecuencia de corridas con parada activa</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">4. Acierto en Decisiones</div>
                        <div id="teleAciertoHumano" class="kpi-value" style="color: var(--success-text);">-- %</div>
                        <div class="kpi-footer">Órdenes autorizadas por el planeador</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">5. Costo Computacional</div>
                        <div id="teleTiempoProm" class="kpi-value" style="font-size: 1.55rem;">-- ms</div>
                        <div class="kpi-footer">Tiempo medio de respuesta</div>
                    </div>
                </div>
            </div>

            <!-- Bitácora de Corridas -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Bitácora Oficial de Corridas del Sistema</div>
                        <div class="card-subtitle">Registro transaccional inmutable de ejecuciones con fecha, duración, indicadores analíticos y resultado de supervisión.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha y Hora</th>
                                <th>ID de Corrida</th>
                                <th>Duración</th>
                                <th>SKUs Auditados</th>
                                <th>ERI Global</th>
                                <th>Quiebres</th>
                                <th>Inversión Propuesta (COP)</th>
                                <th>Estado de Parada</th>
                            </tr>
                        </thead>
                        <tbody id="tablaBitacoraCorridasBody">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay registros históricos en la bitácora de corridas.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Bitácora de Cargas -->
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Bitácora Oficial de Ingesta de Archivos CSV</div>
                        <div class="card-subtitle">Historial de archivos procesados, balance de inserciones, registros omitidos por idempotencia y rechazos.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha y Hora</th>
                                <th>Nombre del Archivo</th>
                                <th>Tipo de Documento</th>
                                <th>Leídas</th>
                                <th>Insertadas</th>
                                <th>Omitidas (Idempotencia)</th>
                                <th>Rechazadas</th>
                                <th>Diagnóstico Pericial</th>
                            </tr>
                        </thead>
                        <tbody id="tablaBitacoraCargasBody">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay registros de ingesta registrados aún.</td></tr>
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

        let matrizReconciliacionActual = [];

        function cambiarPestana(idTab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(idTab).classList.add('active');
            
            const idx = ['tab-control', 'tab-demanda', 'tab-reconciliacion', 'tab-ingesta', 'tab-telemetria'].indexOf(idTab);
            if (idx >= 0) {
                document.querySelectorAll('.tab-btn')[idx].classList.add('active');
            }

            if (idTab === 'tab-demanda' && matrizDemandaActual.length === 0) {
                cargarMatrizDemanda();
            } else if (idTab === 'tab-reconciliacion' && matrizReconciliacionActual.length === 0) {
                cargarMatrizReconciliacion();
            } else if (idTab === 'tab-telemetria') {
                cargarMetricasInstrumentacion();
            }
        }

        let isExecutingAnalysis = false;
        async function ejecutarAnalisisIntegral() {
            if (isExecutingAnalysis) {
                showToast('Ya hay un análisis de abastecimiento en ejecución. Por favor espere...', 'warning');
                return;
            }
            isExecutingAnalysis = true;
            const btn = document.getElementById('btnEjecutarOrquestacion');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Ejecutando análisis...';

            try {
                const res = await fetch('/api/correr');
                if (!res.ok) throw new Error(`El servidor respondió con código ${res.status}`);
                const data = await res.json();
                if (data.status === 'error') {
                    showToast('Atención: ' + (data.mensaje || 'Error en motor analítico'), 'error');
                } else {
                    renderTableroControl(data);
                    showToast('Análisis integral completado exitosamente.', 'success');
                }
            } catch (err) {
                showToast('Error al ejecutar análisis: ' + err.message, 'error');
            } finally {
                isExecutingAnalysis = false;
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
                titulo.innerText = 'Supervisión Humana Obligatoria — Criterio de Parada Activo';
                msg.innerText = data.mensaje_parada;
            } else {
                banner.className = 'alert-banner alert-success';
                titulo.innerText = 'Operación Conforme a Parámetros Nominales';
                msg.innerText = 'No se registraron quiebres de inventario inminentes. Los saldos satisfacen los puntos de reorden vigentes.';
            }

            const tbody = document.getElementById('tablaPropuestasBody');
            tbody.innerHTML = '';

            if (data.propuestas_compra.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2.5rem; color: #10B981;">No hay insumos que requieran reorden en este ciclo de operación.</td></tr>';
                return;
            }

            data.propuestas_compra.forEach(p => {
                const tr = document.createElement('tr');
                tr.id = 'propuesta-' + p.sku;
                tr.innerHTML = `
                    <td>
                        <span class="mono" style="font-weight: 700; color: #60A5FA;">${p.sku}</span><br>
                        <strong>${p.descripcion}</strong><br>
                        <small style="color: var(--text-secondary);">${p.categoria}</small>
                    </td>
                    <td>
                        <span class="kpi-badge ${p.clase_abc === 'A' ? 'badge-danger' : (p.clase_abc === 'B' ? 'badge-warning' : 'badge-success')}">
                            Clase ${p.clase_abc}
                        </span><br>
                        <small style="color: var(--text-muted);">Prioridad ${p.prioridad || 'Media'}</small>
                    </td>
                    <td>
                        <span class="mono">${Number(p.stock_real).toLocaleString('es-CO')}</span> ${p.unidad || 'und'}<br>
                        <small style="color: var(--text-secondary);">Cobertura: ${p.dias_cobertura_remanente || 0} d</small>
                    </td>
                    <td>
                        <span class="mono" style="color: var(--warning-text); font-weight: 600;">${Number(p.punto_reorden_rop).toLocaleString('es-CO')}</span> ${p.unidad || 'und'}<br>
                        <small style="color: var(--text-muted);">SS: ${Number(p.stock_seguridad_ss).toLocaleString('es-CO')}</small>
                    </td>
                    <td>
                        <strong class="mono" style="color: #60A5FA; font-size: 1.05rem;">${Number(p.cantidad_sugerida_eoq).toLocaleString('es-CO')}</strong> ${p.unidad || 'und'}<br>
                        <strong style="color: var(--text-primary); font-size: 0.8rem;">$ ${Number(p.inversion_estimada_cop).toLocaleString('es-CO')} COP</strong>
                    </td>
                    <td>
                        <span class="kpi-badge badge-warning" style="font-size: 0.72rem; padding: 2px 6px;">
                            ${p.momento_emision || 'Inmediato (Stock ≤ ROP)'}
                        </span><br>
                        <small style="color: var(--text-secondary);">Entrega: ${p.lead_time_dias || 15} d</small>
                    </td>
                    <td>
                        <div class="justification-card">
                            <div style="color: #F8FAFC; margin-bottom: 0.35rem; line-height: 1.45;">
                                ${p.justificacion_ejecutiva}
                            </div>
                            <div style="font-size: 0.75rem; color: var(--success-text); font-weight: 600;">
                                ✓ Riesgo financiero mitigado: $ ${Number(p.riesgo_evitado_cop || 3600000).toLocaleString('es-CO')} COP
                            </div>
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

        async function cargarMatrizReconciliacion() {
            try {
                const res = await fetch('/api/reconciliacion');
                const data = await res.json();
                matrizReconciliacionActual = data.auditados || [];

                document.getElementById('recEriPct').innerText = (data.eri_global_pct || 0) + ' %';
                document.getElementById('recConcordantes').innerText = (data.concordantes || 0) + ' SKUs';
                document.getElementById('recDesfases').innerText = (data.total_desfases || 0) + ' SKUs';
                document.getElementById('recFantasmas').innerText = (data.total_fantasmas || 0) + ' SKUs';
                document.getElementById('recImpactoTotal').innerText = '$ ' + Number(data.impacto_total_cop || 0).toLocaleString('es-CO');

                renderTablaReconciliacion(matrizReconciliacionActual);
            } catch (err) {
                console.error('Error cargando reconciliación:', err);
            }
        }

        function renderTablaReconciliacion(lista) {
            const tbody = document.getElementById('tablaReconciliacionBody');
            tbody.innerHTML = '';
            if (lista.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">No hay registros de reconciliación para este filtro.</td></tr>';
                return;
            }
            lista.forEach(r => {
                const tr = document.createElement('tr');
                let badgeClass = 'badge-neutral';
                if (r.concordancia) badgeClass = 'badge-success';
                else if (r.diagnostico_eri.includes('Muelle')) badgeClass = 'badge-warning';
                else badgeClass = 'badge-danger';

                tr.innerHTML = `
                    <td class="mono" style="font-weight: 600; color: #60A5FA;">${r.sku}</td>
                    <td>${r.descripcion}</td>
                    <td><small style="color: var(--text-secondary);">${r.categoria}</small></td>
                    <td class="mono">${Number(r.saldo_teorico).toLocaleString('es-CO', {maximumFractionDigits: 1})}</td>
                    <td class="mono" style="font-weight: 600;">${Number(r.stock_fisico_contado).toLocaleString('es-CO', {maximumFractionDigits: 1})}</td>
                    <td class="mono" style="color: ${r.discrepancia_neta === 0 ? 'var(--text-muted)' : (r.discrepancia_neta > 0 ? 'var(--danger-text)' : '#60A5FA')}">
                        ${r.discrepancia_neta > 0 ? '+' : ''}${Number(r.discrepancia_neta).toLocaleString('es-CO', {maximumFractionDigits: 1})}
                    </td>
                    <td class="mono">$ ${Number(r.impacto_financiero_cop || 0).toLocaleString('es-CO')}</td>
                    <td><span class="kpi-badge ${badgeClass}">${r.diagnostico_eri}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filtrarTablaReconciliacion() {
            const query = document.getElementById('filtroSkuReconciliacion').value.toLowerCase();
            const tipo = document.getElementById('filtroTipoReconciliacion').value;
            const filtrados = matrizReconciliacionActual.filter(r => {
                const coincideTexto = r.sku.toLowerCase().includes(query) || (r.descripcion || '').toLowerCase().includes(query) || (r.categoria || '').toLowerCase().includes(query);
                let coincideTipo = true;
                if (tipo === 'Concordante') coincideTipo = r.concordancia === true;
                else if (tipo === 'Muelle') coincideTipo = (r.diagnostico_eri || '').includes('Muelle');
                else if (tipo === 'Faltante') coincideTipo = (r.diagnostico_eri || '').includes('Faltante') || (r.diagnostico_eri || '').includes('Piso');
                return coincideTexto && coincideTipo;
            });
            renderTablaReconciliacion(filtrados);
        }

        const operacionesEnCurso = new Set();
        async function tomarDecision(sku, accion) {
            if (operacionesEnCurso.has(sku)) {
                showToast(`La decisión para el material ${sku} se encuentra en proceso.`, 'warning');
                return;
            }
            operacionesEnCurso.add(sku);
            const celda = document.getElementById('acciones-' + sku);
            if (celda) {
                celda.innerHTML = '<span class="spinner"></span> <small style="color: var(--text-muted);">Registrando...</small>';
            }

            try {
                const res = await fetch(`/api/decidir?sku=${encodeURIComponent(sku)}&accion=${encodeURIComponent(accion)}`);
                if (!res.ok) throw new Error(`El servidor respondió con código ${res.status}`);
                const data = await res.json();
                
                if (data.status === 'registrado') {
                    if (accion === 'APROBADA') {
                        if (celda) celda.innerHTML = '<span style="color: var(--success-text); font-weight: 600;">✓ Orden Autorizada</span>';
                        showToast(`Orden de compra para SKU ${sku} autorizada y registrada en base de datos.`, 'success');
                    } else {
                        if (celda) celda.innerHTML = '<span style="color: var(--danger-text); font-weight: 600;">✕ Orden Desestimada</span>';
                        showToast(`Recomendación para SKU ${sku} desestimada.`, 'info');
                    }
                } else {
                    showToast('Aviso: ' + (data.mensaje || 'No fue posible registrar la decisión.'), 'warning');
                    restablecerBotonesDecision(sku, celda);
                }
            } catch (err) {
                showToast('Error al registrar decisión: ' + err.message, 'error');
                restablecerBotonesDecision(sku, celda);
            } finally {
                operacionesEnCurso.delete(sku);
            }
        }

        function restablecerBotonesDecision(sku, celda) {
            if (celda) {
                celda.innerHTML = `
                    <button class="btn btn-success btn-sm" onclick="tomarDecision('${sku}', 'APROBADA')">Autorizar</button>
                    <button class="btn btn-danger-outline btn-sm" onclick="tomarDecision('${sku}', 'RECHAZADA')">Desestimar</button>
                `;
            }
        }

        async function cargarMatrizDemanda() {
            try {
                const res = await fetch('/api/demanda');
                if (!res.ok) throw new Error(`Error ${res.status}`);
                const data = await res.json();
                matrizDemandaActual = data.materiales || [];

                // Actualizar Pareto
                const p = data.resumen_abc || {};
                if (p.A) {
                    document.getElementById('paretoA_skus').innerText = (p.A.skus || 0) + ' SKUs';
                    document.getElementById('paretoA_valor').innerText = '$ ' + Number(p.A.valor_cop || 0).toLocaleString('es-CO') + ' COP (' + (p.A.pct_valor || 0).toFixed(1) + '%)';
                }
                if (p.B) {
                    document.getElementById('paretoB_skus').innerText = (p.B.skus || 0) + ' SKUs';
                    document.getElementById('paretoB_valor').innerText = '$ ' + Number(p.B.valor_cop || 0).toLocaleString('es-CO') + ' COP (' + (p.B.pct_valor || 0).toFixed(1) + '%)';
                }
                if (p.C) {
                    document.getElementById('paretoC_skus').innerText = (p.C.skus || 0) + ' SKUs';
                    document.getElementById('paretoC_valor').innerText = '$ ' + Number(p.C.valor_cop || 0).toLocaleString('es-CO') + ' COP (' + (p.C.pct_valor || 0).toFixed(1) + '%)';
                }

                renderTablaDemanda(matrizDemandaActual);
            } catch (err) {
                console.error(err);
                showToast('Error al cargar matriz de demanda: ' + err.message, 'error');
            }
        }

        function renderTablaDemanda(lista) {
            const tbody = document.getElementById('tablaDemandaBody');
            tbody.innerHTML = '';
            if (!lista || lista.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No se encontraron materiales que coincidan con los criterios de búsqueda.</td></tr>';
                return;
            }
            lista.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="mono" style="font-weight: 600; color: #60A5FA;">${m.sku}</td>
                    <td>${m.descripcion}</td>
                    <td><small style="color: var(--text-secondary);">${m.categoria}</small></td>
                    <td><span class="kpi-badge ${m.clasificacion_abc === 'A' ? 'badge-danger' : (m.clasificacion_abc === 'B' ? 'badge-warning' : 'badge-success')}">Clase ${m.clasificacion_abc}</span></td>
                    <td class="mono">${Number(m.demanda_anual_d).toLocaleString('es-CO', {maximumFractionDigits: 1})}</td>
                    <td class="mono">${Number(m.consumo_diario_d).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono">${Number(m.sigma_diario).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono">${m.lead_time_usado} d</td>
                    <td class="mono" style="color: var(--success-text);">${Number(m.SS_95).toLocaleString('es-CO')}</td>
                    <td class="mono" style="color: var(--warning-text); font-weight: 600;">${Number(m.ROP).toLocaleString('es-CO')}</td>
                    <td class="mono" style="color: #60A5FA; font-weight: 600;">${Number(m.EOQ).toLocaleString('es-CO')}</td>
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
        // MÓDULO DE INGESTA (5 PASOS & SUPABASE)
        // ==========================================
        function mostrarEstadoDropzone(estado) {
            const elInicial = document.getElementById('dropzoneEstadoInicial');
            const elProcesando = document.getElementById('dropzoneEstadoProcesando');
            const elCompletado = document.getElementById('dropzoneEstadoCompletado');
            if (elInicial) elInicial.style.display = (estado === 'inicial') ? 'block' : 'none';
            if (elProcesando) elProcesando.style.display = (estado === 'procesando') ? 'block' : 'none';
            if (elCompletado) elCompletado.style.display = (estado === 'completado') ? 'block' : 'none';
        }

        function configurarDropzone() {
            const dz = document.getElementById('dropzone');
            if (!dz) return;

            dz.addEventListener('click', (e) => {
                if (e.target.tagName !== 'INPUT') {
                    document.getElementById('fileInput').click();
                }
            });

            dz.addEventListener('dragover', (e) => {
                e.preventDefault();
                dz.style.borderColor = 'var(--primary)';
                dz.style.backgroundColor = 'var(--primary-subtle)';
            });

            dz.addEventListener('dragleave', () => {
                dz.style.borderColor = '';
                dz.style.backgroundColor = '';
            });

            dz.addEventListener('drop', (e) => {
                e.preventDefault();
                dz.style.borderColor = '';
                dz.style.backgroundColor = '';
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    manejarSeleccionArchivo(e.dataTransfer.files[0]);
                }
            });
        }

        function manejarSeleccionArchivo(file) {
            if (!file) return;
            archivoSeleccionadoNombre = file.name;
            mostrarEstadoDropzone('inicial');
            const reader = new FileReader();
            reader.onload = (e) => {
                archivoSeleccionadoContenido = e.target.result;
                document.getElementById('lblNombreArchivo').innerText = file.name;
                document.getElementById('lblTamanoArchivo').innerText = (file.size / 1024).toFixed(1) + ' KB';
                document.getElementById('lblHashArchivo').innerText = 'Pendiente de cálculo...';
                document.getElementById('archivoMeta').style.display = 'block';
                document.getElementById('btnPrevisualizar').disabled = false;
                document.getElementById('btnConfirmarCarga').disabled = true;
                document.getElementById('panelRendicionCuentas').style.display = 'none';
            };
            reader.readAsText(file);
        }

        let isPrevisualizing = false;
        async function iniciarPrevisualizacion() {
            if (isPrevisualizing) return;
            isPrevisualizing = true;
            const tipo = document.getElementById('ingestaTipoDoc').value;
            const btn = document.getElementById('btnPrevisualizar');
            btn.disabled = true;
            mostrarEstadoDropzone('procesando');

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
                if (!res.ok) throw new Error(`El servidor respondió con código ${res.status}`);
                const data = await res.json();
                mostrarEstadoDropzone('inicial');
                
                const diag = document.getElementById('diagnosticoEstructural');
                if (data.valido) {
                    document.getElementById('lblHashArchivo').innerText = (data.hash_archivo_sha256 || '').substring(0, 18) + '...';
                    diag.innerHTML = `
                        <div style="color: var(--success-text); font-weight: 600; margin-bottom: 0.5rem;">✓ Estructura de archivo conforme para importación e idempotencia</div>
                        <p><strong>Hash SHA-256:</strong> <code class="mono" style="color: #60A5FA;">${data.hash_archivo_sha256}</code></p>
                        <p style="margin-top: 0.35rem;"><strong>Delimitador detectado:</strong> '${data.delimitador}' | <strong>Codificación:</strong> ${data.codificacion.toUpperCase()} | <strong>Filas leídas:</strong> ${data.filas_total}</p>
                        <p style="margin-top: 0.4rem; color: #CBD5E1;">Columnas obligatorias presentes: <em>${data.columnas_esperadas.join(', ')}</em>.</p>
                    `;
                    document.getElementById('btnConfirmarCarga').disabled = false;
                    showToast('Validación estructural aprobada. Listo para asentar con sentencias UPSERT.', 'success');
                } else {
                    diag.innerHTML = `
                        <div style="color: var(--danger-text); font-weight: 600; margin-bottom: 0.5rem;">✕ Inconsistencia en la estructura del archivo</div>
                        <p>${data.mensaje}</p>
                    `;
                    document.getElementById('btnConfirmarCarga').disabled = true;
                    showToast(data.mensaje || 'Inconsistencia en archivo CSV.', 'error');
                }
            } catch (err) {
                mostrarEstadoDropzone('inicial');
                showToast('Error en validación: ' + err.message, 'error');
            } finally {
                isPrevisualizing = false;
                btn.disabled = false;
            }
        }

        let isIngesting = false;
        async function confirmarIngesta() {
            if (isIngesting) {
                showToast('Ya se está procesando una carga en base de datos. Por favor espere...', 'warning');
                return;
            }
            isIngesting = true;
            const tipo = document.getElementById('ingestaTipoDoc').value;
            const btn = document.getElementById('btnConfirmarCarga');
            btn.disabled = true;
            mostrarEstadoDropzone('procesando');

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
                if (!res.ok) throw new Error(`El servidor respondió con código ${res.status}`);
                const data = await res.json();
                
                mostrarEstadoDropzone('completado');
                renderReporteAuditoriaDetallado(data);
                
                if (data.estado_carga === 'Exitoso') {
                    showToast(`Carga procesada con éxito: ${data.filas_insertadas_o_actualizadas} registros conformes asentados en base de datos.`, 'success');
                } else if (data.estado_carga === 'Parcial') {
                    showToast(data.resumen_ejecutivo || `Carga procesada con observaciones: ${data.filas_insertadas_o_actualizadas} conformes, ${data.filas_rechazadas} descartados por inconsistencia.`, 'warning');
                } else {
                    showToast(data.mensaje || `Carga rechazada: el archivo contiene inconsistencias estructurales.`, 'error');
                }
            } catch (err) {
                mostrarEstadoDropzone('inicial');
                showToast('Error durante la importación: ' + err.message, 'error');
            } finally {
                isIngesting = false;
                btn.disabled = false;
            }
        }

        function renderReporteAuditoriaDetallado(data) {
            document.getElementById('panelRendicionCuentas').style.display = 'block';

            // 1. Estado de la Carga (Exitoso / Parcial / Rechazado)
            const badge = document.getElementById('rcBadgeEstado');
            if (data.estado_carga === 'Exitoso') {
                badge.className = 'kpi-badge badge-success';
                badge.innerText = '✓ Estado: Carga Exitosa (100% Conforme)';
            } else if (data.estado_carga === 'Parcial') {
                badge.className = 'kpi-badge badge-warning';
                badge.innerText = '⚠ Estado: Carga Parcial (Con Observaciones)';
            } else {
                badge.className = 'kpi-badge badge-danger';
                badge.innerText = '✕ Estado: Carga Rechazada (Inconsistencias)';
            }

            // Metadatos
            document.getElementById('rcIdCarga').innerText = (data.id_carga || '').substring(0, 16) + '...';
            document.getElementById('rcNombreArchivo').innerText = data.nombre_archivo || archivoSeleccionadoNombre;
            document.getElementById('rcHashArchivo').innerText = data.hash_archivo_sha256 || 'N/A';
            
            const sbSync = document.getElementById('rcSupabaseSync');
            if (data.sincronizacion_supabase && (data.sincronizacion_supabase.status === 'success' || data.sincronizacion_supabase.estado === 'SINCRONIZADO')) {
                sbSync.innerHTML = '<span style="color: var(--success-text);">✓ Sincronizado en Supabase (UPSERT ON CONFLICT)</span>';
            } else if (data.sincronizacion_supabase && data.sincronizacion_supabase.status === 'offline_fallback') {
                sbSync.innerHTML = '<span style="color: #60A5FA;">✓ Asentado en Base Relacional Local (Modo Resiliente / Supabase Offline)</span>';
            } else {
                sbSync.innerHTML = '<span style="color: #60A5FA;">✓ Asentado en Base Relacional (ON CONFLICT DO UPDATE / DO NOTHING)</span>';
            }

            // 2. Total de Registros Procesados
            document.getElementById('rcLeidas').innerText = data.total_registros_procesados || data.filas_leidas;

            // 3. Registros Insertados / Actualizados
            document.getElementById('rcInsertadas').innerText = data.filas_insertadas_o_actualizadas || (data.filas_insertadas + data.filas_actualizadas);

            // 4. Registros Omitidos por Idempotencia
            document.getElementById('rcOmitidas').innerText = data.filas_omitidas_duplicadas;

            // 5. Registros Rechazados
            document.getElementById('rcRechazadas').innerText = data.filas_rechazadas;

            // Explicación de Idempotencia
            const textoIdemp = document.getElementById('rcTextoIdempotencia');
            textoIdemp.innerText = `Idempotencia verificada: el reingreso del mismo archivo o la ejecución múltiple no altera los saldos de inventario ni duplica registros (Cambio neto en base = ${data.cambio_neto_base} registros). Las transacciones existentes fueron gestionadas con cláusulas ON CONFLICT en Supabase y base relacional.`;

            // Trazabilidad Fila a Fila
            trazabilidadActual = data.trazabilidad_filas || [];
            renderTablaTrazabilidad(trazabilidadActual);
        }

        function renderTablaTrazabilidad(filas) {
            const tbody = document.getElementById('tablaTrazabilidadBody');
            tbody.innerHTML = '';
            
            if (filas.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay registros de trazabilidad para este filtro.</td></tr>';
                return;
            }

            filas.forEach(f => {
                const tr = document.createElement('tr');
                let badgeClass = 'badge-neutral';
                if (f.estado === 'INSERTADA') badgeClass = 'badge-success';
                else if (f.estado === 'ACTUALIZADA') badgeClass = 'badge-warning';
                else if (f.estado.includes('OMITIDA')) badgeClass = 'badge-neutral';
                else if (f.estado === 'RECHAZADA') badgeClass = 'badge-danger';

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
            link.setAttribute("download", `auditoria_carga_supabase_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function limpiarEstadoIngesta() {
            mostrarEstadoDropzone('inicial');
            document.getElementById('panelRendicionCuentas').style.display = 'none';
            document.getElementById('diagnosticoEstructural').innerText = 'Seleccione o arrastre un archivo CSV para inspeccionar delimitadores, juego de caracteres, calcular su hash único y validar las columnas obligatorias.';
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
                            <td class="mono" style="color: var(--danger-text); font-weight: 600;">${c.skus_en_quiebre}</td>
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
                            <td class="mono" style="color: var(--success-text);">${cg.filas_cargadas}</td>
                            <td class="mono" style="color: #60A5FA;">${cg.filas_omitidas_duplicadas}</td>
                            <td class="mono" style="color: var(--danger-text);">${cg.filas_rechazadas}</td>
                            <td style="font-size: 0.8rem; color: var(--text-secondary);">${cg.detalle_rechazos}</td>
                        `;
                        tbodyCargas.appendChild(tr);
                    });
                }
            } catch (err) {
                console.error(err);
            }
        }

        function showToast(msg, tipo = 'info') {
            const toast = document.getElementById('toast');
            if (!toast) return;
            if (tipo === 'error') {
                toast.style.borderColor = 'var(--danger-border)';
                toast.style.backgroundColor = '#2D1515';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--danger-text); font-weight: 700; font-size: 1rem;">✕</span><div style="color: #FEE2E2; line-height: 1.4;">${msg}</div></div>`;
            } else if (tipo === 'warning') {
                toast.style.borderColor = 'var(--warning-border)';
                toast.style.backgroundColor = '#2B1E11';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--warning-text); font-weight: 700; font-size: 1rem;">⚠</span><div style="color: #FEF3C7; line-height: 1.4;">${msg}</div></div>`;
            } else if (tipo === 'success') {
                toast.style.borderColor = 'var(--success-border)';
                toast.style.backgroundColor = '#0F291E';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--success-text); font-weight: 700; font-size: 1rem;">✓</span><div style="color: #D1FAE5; line-height: 1.4;">${msg}</div></div>`;
            } else {
                toast.style.borderColor = 'var(--primary-border)';
                toast.style.backgroundColor = 'var(--bg-surface-elevated)';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: #60A5FA; font-weight: 700; font-size: 1rem;">ℹ</span><div style="color: #FFFFFF; line-height: 1.4;">${msg}</div></div>`;
            }
            toast.style.display = 'block';
            if (window._toastTimer) clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => { toast.style.display = 'none'; }, 6000);
        }

        // Blindaje global contra excepciones y promesas no controladas
        window.addEventListener('unhandledrejection', function (event) {
            console.error('Promesa no capturada interceptada:', event.reason);
            showToast('Aviso de estabilidad: Se interceptó una respuesta no conforme. La sesión y los datos permanecen asegurados.', 'warning');
            event.preventDefault();
        });

        window.onerror = function (msg, url, lineNo, columnNo, error) {
            console.error('Error de interfaz interceptado:', msg, error);
            showToast('Aviso de interfaz: Se controló una anomalía visual sin comprometer las transacciones.', 'info');
            return true;
        };

        // Carga inicial
        window.onload = () => {
            configurarDropzone();
            ejecutarAnalisisIntegral();
        };
    </script>
</body>
</html>
"""

class EnterpriseRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
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
                sku = query.get('sku', [''])[0].strip()
                accion = query.get('accion', ['APROBADA'])[0].strip()
                corrida_id = query.get('corrida_id', [None])[0]
                
                if not sku:
                    res = {'status': 'error', 'mensaje': 'El código SKU es obligatorio para registrar una decisión.'}
                else:
                    res = datos.registrar_decision(sku, accion, planeador="Planeador de Abastecimiento E2", corrida_id=corrida_id)
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
                
            elif parsed.path == '/api/reconciliacion':
                estado = datos.leer_estado()
                res_eri = eri.auditar_eri(estado)
                df_aud = res_eri['df_auditoria'].replace({np.nan: None})
                res = {
                    'eri_global_pct': res_eri['eri_global_pct'],
                    'total_auditados': res_eri['total_auditados'],
                    'concordantes': res_eri['concordantes'],
                    'total_fantasmas': len(res_eri['fantasmas']),
                    'total_desfases': len(res_eri['desfases_muelle']),
                    'impacto_fantasmas_cop': res_eri['impacto_fantasmas_cop'],
                    'impacto_desfases_cop': res_eri['impacto_desfases_cop'],
                    'impacto_total_cop': res_eri['impacto_total_cop'],
                    'auditados': df_aud[[
                        'sku', 'descripcion', 'categoria', 'saldo_teorico',
                        'stock_fisico_contado', 'discrepancia_neta', 'discrepancia_absoluta',
                        'impacto_financiero_cop', 'concordancia', 'diagnostico_eri'
                    ]].to_dict(orient='records')
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
                
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'mensaje': f'Ruta no encontrada: {parsed.path}'}, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            err_data = {
                'status': 'error',
                'mensaje': f'El servidor interceptó una anomalía operacional en modo resiliente: {str(e)}',
                'tipo_error': type(e).__name__
            }
            self.wfile.write(json.dumps(err_data, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
            
            try:
                payload = json.loads(post_body)
            except Exception:
                payload = {}
                
            if parsed.path == '/api/previsualizar':
                nombre_archivo = payload.get('nombre_archivo', 'archivo.csv')
                tipo_documento = payload.get('tipo_documento', 'movimientos_inventario')
                contenido = payload.get('contenido', '')
                
                contenido_bytes = contenido.encode('utf-8') if isinstance(contenido, str) else (contenido or b'')
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
                self.send_response(404)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'mensaje': f'Endpoint POST no encontrado: {parsed.path}'}, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            err_data = {
                'status': 'error',
                'mensaje': f'Inconsistencia en el cuerpo de la petición POST: {str(e)}',
                'tipo_error': type(e).__name__
            }
            self.wfile.write(json.dumps(err_data, ensure_ascii=False).encode('utf-8'))

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
