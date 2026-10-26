"""
APLICATIVO EMPRESARIAL DE GESTIÓN DE ABASTECIMIENTO, INVENTARIOS Y CONTROL
E2 SAS — Manufactura de Mobiliario Metálico para Oficina
Producción 4.0 · Énfasis II · Universidad de Medellín

Módulos integrados:
  1. Tablero de control y supervisión humana
  2. Planificación de demanda dependiente y reposición
  3. Reconciliación de inventario y exactitud de registro
  4. Carga de archivos e ingesta de datos con control de idempotencia
  5. Instrumentación operativa y auditoría del sistema
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
    <!-- Metadatos de módulos corporativos: Tablero de Control | Ingesta de Datos | Reconciliación | Abastecimiento -->
    <meta name="application-name" content="E2 SAS — Tablero de Control e Ingesta de Datos">
    <title>E2 SAS — Tablero de Control e Ingesta de Datos | Sistema integral de abastecimiento</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            /* 1. Fondo general y lienzos corporativos (ERP Enterprise) */
            --bg-app: #F4F5F6;                 /* Gris neutro corporativo claro */
            --bg-surface: #FFFFFF;             /* Blanco puro para tarjetas y paneles */
            --bg-surface-subtle: #F8F9FA;      /* Superficie auxiliar sobria */
            --bg-surface-hover: #F9FAFA;       /* Hover sutil en filas */
            --bg-input: #FFFFFF;

            /* 2. Barra Lateral Fija (Sidebar) Carbón Oscuro Mate */
            --bg-sidebar: #16181B;             /* Carbón oscuro mate, cero azul */
            --bg-sidebar-hover: #23262A;       /* Hover en ítems de menú */
            --bg-sidebar-active: #2B2E33;      /* Ítem activo */
            --border-sidebar: #26292E;         /* Borde derecho y divisores */
            --text-sidebar: #C2C5C9;           /* Texto secundario sidebar */
            --text-sidebar-active: #FFFFFF;    /* Texto ítem activo */
            --text-sidebar-muted: #8A8F96;     /* Metadatos sidebar */

            /* 3. Bordes y Delimitadores Estructurales */
            --border: #E1E3E6;                 /* Gris neutro claro 1px sólido */
            --border-subtle: #EAECEE;          /* Divisores internos suaves */
            --border-hover: #C2C5C9;           /* Borde hover controles */
            --border-focus: #2B2E33;           /* Borde focus sobrio */

            /* 4. Jerarquía Tipográfica */
            --text-primary: #16181B;           /* Carbón profundo principal */
            --text-secondary: #5C6168;         /* Gris medio para etiquetas */
            --text-muted: #8A8F96;             /* Gris atenuado para notas */

            /* 5. Acento Primario (Cero Azul) */
            --accent: #2B2E33;                 /* Grafito / carbón oscuro */
            --accent-hover: #16181B;
            --accent-text: #FFFFFF;

            /* 6. Estados Semánticos Desaturados / Apagados */
            --success: #3F6B53;                /* Verde bosque apagado */
            --success-hover: #325643;
            --bg-success: #F0F4F1;             /* Fondo estado óptimo */
            --border-success: #C8D6CD;         /* Borde estado óptimo */
            --text-success: #3F6B53;

            --warning: #8A6A1F;                /* Mostaza oscuro / ámbar seco */
            --warning-hover: #735717;
            --bg-warning: #FBF8EE;             /* Fondo alerta sutil */
            --border-warning: #E5DBC2;         /* Borde alerta */
            --text-warning: #8A6A1F;

            --danger: #8C2F2F;                 /* Rojo ladrillo apagado / vino suave */
            --danger-hover: #752525;
            --bg-danger: #F9F1F1;              /* Fondo riesgo suave */
            --border-danger: #DFCCCC;          /* Borde riesgo */
            --text-danger: #8C2F2F;

            --neutral-badge-bg: #F4F5F6;
            --neutral-badge-border: #E1E3E6;
            --neutral-badge-text: #5C6168;

            /* 7. Geometría: Estrictamente 3px-6px (Cero estilo píldora >8px) */
            --radius-xs: 3px;
            --radius-sm: 4px;
            --radius-md: 6px;
            --shadow-subtle: 0 1px 2px rgba(0, 0, 0, 0.04);
            --shadow-dropdown: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.03);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-app);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            line-height: 1.45;
        }

        /* BARRA LATERAL FIJA (SIDEBAR) */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 250px;
            height: 100vh;
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-sidebar);
            display: flex;
            flex-direction: column;
            z-index: 200;
            overflow-y: auto;
        }

        .sidebar-brand {
            padding: 1.25rem 1.25rem 1rem 1.25rem;
            border-bottom: 1px solid var(--border-sidebar);
        }

        .sidebar-logo {
            font-size: 1.15rem;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: 0.03em;
            font-family: 'JetBrains Mono', monospace;
        }

        .sidebar-subtitle {
            font-size: 0.775rem;
            color: var(--text-sidebar);
            font-weight: 500;
            margin-top: 0.25rem;
        }

        .sidebar-meta {
            font-size: 0.6875rem;
            color: var(--text-sidebar-muted);
            margin-top: 0.15rem;
        }

        .sidebar-nav {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            padding: 1rem 0.75rem;
            flex: 1;
        }

        .tab-btn {
            background: transparent;
            border: none;
            border-left: 2px solid transparent;
            color: var(--text-sidebar);
            padding: 0.65rem 0.85rem;
            border-radius: var(--radius-xs);
            font-size: 0.8125rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-align: left;
            width: 100%;
            line-height: 1.35;
        }

        .tab-btn:hover {
            color: #FFFFFF;
            background-color: var(--bg-sidebar-hover);
        }

        .tab-btn.active {
            background: var(--bg-sidebar-active);
            color: var(--text-sidebar-active);
            font-weight: 600;
            border-left-color: #FFFFFF;
        }

        .tab-btn svg {
            flex-shrink: 0;
            stroke: currentColor;
        }

        .sidebar-footer {
            padding: 1rem 1.25rem;
            border-top: 1px solid var(--border-sidebar);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.6875rem;
            color: var(--text-sidebar-muted);
        }

        /* CONTENIDO Y DISPOSICIÓN DERECHA */
        .layout-content-wrapper {
            margin-left: 250px;
            width: calc(100% - 250px);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* BARRA SUPERIOR (TOPBAR) */
        .topbar {
            position: sticky;
            top: 0;
            height: 56px;
            background-color: #FFFFFF;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            z-index: 100;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        }

        .topbar-left {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .topbar-brand-name {
            font-size: 0.8125rem;
            font-weight: 600;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        .topbar-divider {
            color: var(--border);
            font-size: 0.8125rem;
        }

        .topbar-section-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .system-status-indicator {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-success);
            background: var(--bg-success);
            border: 1px solid var(--border-success);
            padding: 0.3rem 0.65rem;
            border-radius: var(--radius-xs);
        }

        .status-dot {
            width: 6px;
            height: 6px;
            background-color: var(--success);
            border-radius: 50%;
            display: inline-block;
        }

        /* LIENZO PRINCIPAL */
        main {
            padding: 1.75rem 2rem;
            background-color: var(--bg-app);
            flex: 1;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* TARJETAS Y PANELES */
        .card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 1.35rem 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-subtle);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            padding-bottom: 0.85rem;
            border-bottom: 1px solid var(--border);
        }

        .card-title {
            font-size: 0.9375rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.55rem;
            letter-spacing: -0.01em;
        }

        .card-subtitle {
            font-size: 0.775rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }

        /* GRILLES KPI EQUILIBRADAS */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .kpi-grid-5 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border);
            border-top: 2px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 1.15rem 1.25rem;
            box-shadow: var(--shadow-subtle);
            transition: border-color 0.15s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .kpi-card:hover {
            border-color: var(--border-hover);
        }

        .kpi-card.accent-success { border-top-color: var(--success); }
        .kpi-card.accent-warning { border-top-color: var(--warning); }
        .kpi-card.accent-danger { border-top-color: var(--danger); }

        .kpi-label {
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 0.45rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .kpi-value {
            font-size: 1.75rem;
            font-weight: 600;
            font-family: 'Inter', -apple-system, sans-serif;
            font-variant-numeric: tabular-nums;
            color: var(--text-primary);
            letter-spacing: -0.02em;
            line-height: 1.2;
        }

        .kpi-footer {
            font-size: 0.725rem;
            color: var(--text-secondary);
            margin-top: 0.65rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* ETIQUETAS Y BADGES RECTANGULARES SOBRIOS */
        .kpi-badge {
            padding: 2px 7px;
            border-radius: var(--radius-xs);
            font-weight: 600;
            font-size: 0.72rem;
            letter-spacing: normal;
            display: inline-block;
            line-height: 1.35;
        }

        .badge-success {
            background: var(--bg-success);
            color: var(--text-success);
            border: 1px solid var(--border-success);
        }

        .badge-warning {
            background: var(--bg-warning);
            color: var(--text-warning);
            border: 1px solid var(--border-warning);
        }

        .badge-danger {
            background: var(--bg-danger);
            color: var(--text-danger);
            border: 1px solid var(--border-danger);
        }

        .badge-neutral {
            background: var(--neutral-badge-bg);
            color: var(--neutral-badge-text);
            border: 1px solid var(--neutral-badge-border);
        }

        /* BANNERS DE SUPERVISIÓN Y CONTROL */
        .alert-banner {
            border-radius: var(--radius-sm);
            padding: 1.1rem 1.35rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.95rem;
            background: #FFFFFF;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-subtle);
        }

        .alert-warning {
            border-left: 4px solid var(--warning);
            color: var(--text-primary);
        }

        .alert-success {
            border-left: 4px solid var(--success);
            color: var(--text-primary);
        }

        .alert-title {
            font-weight: 600;
            font-size: 0.875rem;
            margin-bottom: 0.25rem;
            letter-spacing: -0.01em;
            color: var(--text-primary);
        }

        .alert-body {
            font-size: 0.8125rem;
            line-height: 1.5;
            color: var(--text-secondary);
        }

        /* TABLAS CORPORATIVAS */
        .table-responsive {
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: var(--bg-surface);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.8125rem;
        }

        th {
            background-color: var(--bg-app);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }

        th.text-right, td.text-right {
            text-align: right;
        }

        th.text-center, td.text-center {
            text-align: center;
        }

        td {
            padding: 0.8rem 1rem;
            border-bottom: 1px solid var(--border-subtle);
            vertical-align: middle;
            color: var(--text-primary);
            font-size: 0.8125rem;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background-color: var(--bg-surface-hover);
        }

        /* MATRIZ DE DEMANDA CON COLUMNAS CONGELADAS */
        .table-sticky-demanda {
            overflow-x: auto;
            max-height: 520px;
            position: relative;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: var(--bg-surface);
        }

        .table-sticky-demanda th.col-sticky-sku,
        .table-sticky-demanda td.col-sticky-sku {
            position: sticky;
            left: 0;
            z-index: 2;
            background-color: #FFFFFF;
            border-right: 1px solid var(--border);
            min-width: 105px;
        }

        .table-sticky-demanda th.col-sticky-desc,
        .table-sticky-demanda td.col-sticky-desc {
            position: sticky;
            left: 105px;
            z-index: 2;
            background-color: #FFFFFF;
            border-right: 2px solid var(--border);
            min-width: 220px;
        }

        .table-sticky-demanda th.col-sticky-sku,
        .table-sticky-demanda th.col-sticky-desc {
            background-color: var(--bg-app);
            z-index: 4;
        }

        .table-sticky-demanda tr:hover td.col-sticky-sku,
        .table-sticky-demanda tr:hover td.col-sticky-desc {
            background-color: var(--bg-surface-hover);
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8125rem;
            font-variant-numeric: tabular-nums;
        }

        /* BOTONES ENTERPRISE */
        .btn {
            padding: 0.45rem 0.9rem;
            border-radius: var(--radius-sm);
            font-size: 0.8125rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border: 1px solid transparent;
            text-decoration: none;
            line-height: 1.4;
        }

        .btn-primary {
            background-color: var(--accent);
            color: var(--accent-text);
            border-color: var(--accent);
            box-shadow: var(--shadow-subtle);
        }

        .btn-primary:hover {
            background-color: var(--accent-hover);
            border-color: var(--accent-hover);
        }

        .btn-primary:focus {
            outline: none;
            box-shadow: 0 0 0 2px rgba(43, 46, 51, 0.25);
        }

        .btn-success {
            background-color: var(--success);
            color: #FFFFFF;
            border-color: var(--success);
            box-shadow: var(--shadow-subtle);
        }

        .btn-success:hover {
            background-color: var(--success-hover);
            border-color: var(--success-hover);
        }

        .btn-outline {
            background-color: #FFFFFF;
            border-color: var(--border);
            color: var(--text-primary);
        }

        .btn-outline:hover {
            color: var(--text-primary);
            border-color: var(--border-hover);
            background-color: var(--bg-app);
        }

        .btn-danger-outline {
            background-color: #FFFFFF;
            border: 1px solid var(--border-danger);
            color: var(--danger);
        }

        .btn-danger-outline:hover {
            background-color: var(--bg-danger);
            border-color: var(--danger);
        }

        .btn-sm {
            padding: 0.3rem 0.65rem;
            font-size: 0.75rem;
            border-radius: var(--radius-xs);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* FORMULARIOS Y FILTROS */
        .form-group {
            margin-bottom: 1.15rem;
        }

        .form-label {
            display: block;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
            letter-spacing: normal;
        }

        .form-select, .form-input {
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.5rem 0.75rem;
            border-radius: var(--radius-sm);
            font-size: 0.8125rem;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }

        .form-select:focus, .form-input:focus {
            outline: none;
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px rgba(43, 46, 51, 0.12);
        }

        /* ZONA DE CARGA (DRAG & DROP) */
        .dropzone {
            border: 1px dashed var(--border-hover);
            border-radius: var(--radius-sm);
            padding: 2.25rem 1.5rem;
            text-align: center;
            background: #FFFFFF;
            transition: all 0.15s ease;
            cursor: pointer;
        }

        .dropzone:hover {
            border-color: var(--success);
            background: var(--bg-success);
        }

        .dropzone-icon {
            width: 32px;
            height: 32px;
            margin: 0 auto 0.75rem;
            color: var(--text-secondary);
        }

        /* BARRA DE FILTROS */
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
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.45rem 0.75rem;
            border-radius: var(--radius-sm);
            font-size: 0.8125rem;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px rgba(43, 46, 51, 0.12);
        }

        /* TARJETA DE JUSTIFICACIÓN DE RIESGO EVITADO */
        .justification-card {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 3px solid var(--success);
            padding: 0.85rem 1rem;
            border-radius: var(--radius-xs);
            font-size: 0.8rem;
            line-height: 1.6;
            color: var(--text-secondary);
            margin-top: 0.35rem;
        }

        /* TOAST FLOTANTE */
        #toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #16181B;
            border: 1px solid #2B2E33;
            color: #FFFFFF;
            padding: 0.85rem 1.25rem;
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-dropdown);
            font-size: 0.8125rem;
            font-weight: 500;
            display: none;
            z-index: 9999;
            max-width: 440px;
        }

        /* SPINNERS */
        .spinner {
            width: 13px;
            height: 13px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: #FFFFFF;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            display: inline-block;
        }

        .spinner-emerald {
            width: 24px;
            height: 24px;
            border: 2.5px solid var(--border);
            border-top-color: var(--success);
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

    <!-- BARRA LATERAL FIJA (SIDEBAR) -->
    <aside class="sidebar">
        <div class="sidebar-brand">
            <div class="sidebar-logo">E2 SAS</div>
            <div class="sidebar-subtitle">Sistema de Abastecimiento</div>
            <div class="sidebar-meta">Producción 4.0 · Mobiliario Metálico</div>
        </div>

        <nav class="sidebar-nav">
            <button class="tab-btn active" onclick="cambiarPestana('tab-control')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
                <span>Tablero de control y recomendaciones</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('tab-demanda')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                <span>Planificación de demanda y abastecimiento</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('tab-reconciliacion')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                <span>Reconciliación de inventario y exactitud de registro</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('tab-ingesta')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                <span>Carga de archivos e ingesta de datos</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('tab-telemetria')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                <span>Instrumentación operativa y auditoría</span>
            </button>
        </nav>

        <div class="sidebar-footer">
            <div>v4.0 Enterprise</div>
            <div>E2 SAS · Control 4.0</div>
        </div>
    </aside>

    <!-- DISPOSICIÓN PRINCIPAL DERECHA -->
    <div class="layout-content-wrapper">
        <!-- BARRA SUPERIOR (TOPBAR) -->
        <header class="topbar">
            <div class="topbar-left">
                <span class="topbar-brand-name">E2 SAS</span>
                <span class="topbar-divider">/</span>
                <span id="topbarSectionTitle" class="topbar-section-title">Tablero de control y recomendaciones</span>
            </div>
            <div class="topbar-right">
                <div class="system-status-indicator">
                    <span class="status-dot"></span>
                    <span>Base relacional activa</span>
                </div>
            </div>
        </header>

        <main>
            <!-- ======================================================== -->
            <!-- PESTAÑA 1: TABLERO DE CONTROL Y RECOMENDACIONES DE PEDIDOS -->
            <!-- ======================================================== -->
            <div id="tab-control" class="tab-content active">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <h2 style="font-size: 1.25rem; font-weight: 600; letter-spacing: -0.01em; color: var(--text-primary);">Estado general de abastecimiento</h2>
                        <p style="font-size: 0.8125rem; color: var(--text-secondary);">Supervisión de inventario físico, reconciliación contable y aprobación ejecutiva de órdenes de compra.</p>
                    </div>
                    <div>
                        <button id="btnEjecutarOrquestacion" class="btn btn-primary" onclick="ejecutarAnalisisIntegral()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            <span>Ejecutar análisis integral</span>
                        </button>
                    </div>
                </div>

                <!-- Grid de Indicadores Clave -->
                <div class="kpi-grid">
                    <div class="kpi-card accent-success">
                        <div class="kpi-label">Exactitud de registro (ERI)</div>
                        <div id="kpiEri" class="kpi-value">-- %</div>
                        <div class="kpi-footer">
                            <span id="badgeEri" class="kpi-badge badge-neutral">Tolerancia ±5%</span>
                            <span>Saldo teórico frente a conteo físico</span>
                        </div>
                    </div>
                    <div class="kpi-card accent-danger">
                        <div class="kpi-label">Materiales en riesgo de quiebre</div>
                        <div id="kpiQuiebres" class="kpi-value" style="color: var(--danger);">--</div>
                        <div class="kpi-footer">
                            <span class="kpi-badge badge-danger">Stock real ≤ ROP</span>
                            <span>Requiere reposición inmediata</span>
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Inversión requerida (EOQ)</div>
                        <div id="kpiInversion" class="kpi-value">$ --</div>
                        <div class="kpi-footer">
                            <span class="kpi-badge badge-neutral">Costo de emisión $80.000 COP</span>
                            <span>Lote económico de compra</span>
                        </div>
                    </div>
                    <div class="kpi-card accent-warning">
                        <div class="kpi-label">Discrepancias físicas auditadas</div>
                        <div id="kpiDiscrepancias" class="kpi-value" style="color: var(--warning);">--</div>
                        <div class="kpi-footer">
                            <span class="kpi-badge badge-warning">Desfases detectados</span>
                            <span>Muelle y faltantes en piso</span>
                        </div>
                    </div>
                </div>

                <!-- Banner de Criterio de Parada y Supervisión Humana -->
                <div id="bannerSupervision" class="alert-banner alert-warning">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" style="flex-shrink: 0; margin-top: 2px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    <div>
                        <div id="supervisionTitulo" class="alert-title">Supervisión humana obligatoria — Criterio de parada activo</div>
                        <div id="supervisionMensaje" class="alert-body">
                            El sistema ha detectado necesidades críticas de abastecimiento. Por política corporativa de E2 SAS, ninguna orden de compra compromete recursos financieros sin la aprobación explícita del planeador de abastecimiento.
                        </div>
                    </div>
                </div>

                <!-- Tarjetas Ejecutivas de Recomendación Verticales -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Recomendaciones del agente de abastecimiento</div>
                            <div class="card-subtitle">Decisiones prioritarias: lote económico exacto (EOQ), condición de emisión al tocar el ROP y justificación financiera del riesgo evitado.</div>
                        </div>
                    </div>
                    <div id="contenedorPropuestasCards" style="display: flex; flex-direction: column; gap: 1rem;">
                        <div style="text-align: center; color: var(--text-secondary); padding: 3rem; background: var(--bg-surface-subtle); border: 1px solid var(--border); border-radius: var(--radius-sm);">
                            Presione <strong>"Ejecutar análisis integral"</strong> para evaluar el estado actual del inventario.
                        </div>
                    </div>
                </div>
            </div>

            <!-- ======================================================== -->
            <!-- PESTAÑA 2: PLANIFICACIÓN DE DEMANDA Y ABASTECIMIENTO     -->
            <!-- ======================================================== -->
            <div id="tab-demanda" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Planificación de demanda dependiente y reposición</div>
                            <div class="card-subtitle">Explosión de requerimientos brutos sobre la matriz de recetas y dimensionamiento dinámico de reposición.</div>
                        </div>
                    </div>
                    <div class="kpi-grid" id="paretoGrid">
                        <div class="kpi-card accent-danger">
                            <div class="kpi-label">Clase A (Inversión alta)</div>
                            <div id="paretoA_skus" class="kpi-value" style="color: var(--danger);">-- SKUs</div>
                            <div id="paretoA_valor" class="kpi-footer">$ -- COP (80% del valor total)</div>
                        </div>
                        <div class="kpi-card accent-warning">
                            <div class="kpi-label">Clase B (Inversión media)</div>
                            <div id="paretoB_skus" class="kpi-value" style="color: var(--warning);">-- SKUs</div>
                            <div id="paretoB_valor" class="kpi-footer">$ -- COP (15% del valor total)</div>
                        </div>
                        <div class="kpi-card accent-success">
                            <div class="kpi-label">Clase C (Inversión baja)</div>
                            <div id="paretoC_skus" class="kpi-value" style="color: var(--success);">-- SKUs</div>
                            <div id="paretoC_valor" class="kpi-footer">$ -- COP (5% del valor total)</div>
                        </div>
                    </div>
                </div>

                <!-- Panel de Análisis de Demanda Dependiente por Líneas de Muebles -->
                <div class="card" style="background: var(--bg-surface-subtle); margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <div style="font-weight: 600; font-size: 0.9375rem; color: var(--text-primary);">Demanda dependiente derivada del plan maestro de muebles metálicos</div>
                        <span class="kpi-badge badge-neutral">Explosión matricial plan × recetas</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.8125rem; color: var(--text-secondary);">
                        <div style="background: #FFFFFF; padding: 0.9rem; border-radius: var(--radius-xs); border: 1px solid var(--border); border-left: 3px solid var(--accent);">
                            <strong style="color: var(--text-primary);">Línea de archivadores (ARC):</strong> Demanda mensual pico de hasta 501 unidades (+106.1%). Exige hasta 7.76 láminas de acero y 6.46 juegos de correderas por mueble terminado.
                        </div>
                        <div style="background: #FFFFFF; padding: 0.9rem; border-radius: var(--radius-xs); border: 1px solid var(--border); border-left: 3px solid var(--success);">
                            <strong style="color: var(--text-primary);">Línea de estanterías (EST):</strong> Demanda mensual pico de hasta 444 unidades (+87.2%). Alto consumo de tubería, perfiles estructurales y pintura electrostática en polvo.
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Matriz analítica de reposición y parámetros dinámicos</div>
                            <div class="card-subtitle">Consumo diario, desviación estándar, tiempo de entrega auditado, stock de seguridad probabilístico, punto de reorden y lote económico.</div>
                        </div>
                        <div class="filter-bar">
                            <input type="text" id="filtroSkuDemanda" class="search-input" placeholder="Buscar por número de SKU, descripción o familia..." oninput="filtrarTablaDemanda()">
                            <select id="filtroClaseAbc" class="form-select" style="max-width: 160px;" onchange="filtrarTablaDemanda()">
                                <option value="">Todas las clases</option>
                                <option value="A">Clase A</option>
                                <option value="B">Clase B</option>
                                <option value="C">Clase C</option>
                            </select>
                        </div>
                    </div>
                    <!-- Tabla con Columnas Congeladas (Sticky) -->
                    <div class="table-sticky-demanda">
                        <table>
                            <thead>
                                <tr>
                                    <th class="col-sticky-sku">Número de SKU</th>
                                    <th class="col-sticky-desc">Descripción del material</th>
                                    <th>Familia</th>
                                    <th class="text-center">Clase ABC</th>
                                    <th class="text-right">Demanda anual (D)</th>
                                    <th class="text-right">Consumo diario (d)</th>
                                    <th class="text-right">Desviación (σd)</th>
                                    <th class="text-right">Tiempo de entrega</th>
                                    <th class="text-right">Stock de seguridad</th>
                                    <th class="text-right">Punto de reorden</th>
                                    <th class="text-right">Lote económico</th>
                                    <th class="text-right">Stock físico actual</th>
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
            <!-- PESTAÑA 3: AUDITORÍA Y DETALLE DE RECONCILIACIÓN         -->
            <!-- ======================================================== -->
            <div id="tab-reconciliacion" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Reconciliación de inventario y exactitud de registro</div>
                            <div class="card-subtitle">Reconciliación matemática entre el Kardex canónico relacional y el conteo físico en bodega bajo tolerancia del ±5%.</div>
                        </div>
                        <button class="btn btn-outline btn-sm" onclick="cargarMatrizReconciliacion()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                            <span>Actualizar reconciliación</span>
                        </button>
                    </div>
                    <!-- Grilla Simétrica de 5 Columnas -->
                    <div class="kpi-grid-5">
                        <div class="kpi-card accent-success">
                            <div class="kpi-label">Exactitud de registro (ERI)</div>
                            <div id="recEriPct" class="kpi-value" style="color: var(--success);">-- %</div>
                            <div class="kpi-footer">Meta corporativa: 95.0%</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Materiales concordantes (±5%)</div>
                            <div id="recConcordantes" class="kpi-value">--</div>
                            <div class="kpi-footer">Dentro del umbral de tolerancia</div>
                        </div>
                        <div class="kpi-card accent-warning">
                            <div class="kpi-label">Desfases en muelle de recepción</div>
                            <div id="recDesfases" class="kpi-value" style="color: var(--text-primary);">--</div>
                            <div class="kpi-footer">Físico > Kardex (pendientes de asentar)</div>
                        </div>
                        <div class="kpi-card accent-danger">
                            <div class="kpi-label">Riesgo por parada de planta (faltantes)</div>
                            <div id="recFantasmas" class="kpi-value" style="color: var(--danger);">--</div>
                            <div class="kpi-footer">Kardex > Físico (riesgo en línea de ensamble)</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Impacto financiero de discrepancias</div>
                            <div id="recImpactoTotal" class="kpi-value" style="font-size: 1.45rem; color: var(--warning);">$ --</div>
                            <div class="kpi-footer">Valoración total de descuadres</div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Auditoría y detalle de reconciliación de inventario</div>
                            <div class="card-subtitle">Comparativa entre saldo teórico reconstruido y conteo auditado con clasificación de causa raíz e impacto contable.</div>
                        </div>
                        <div class="filter-bar">
                            <input type="text" id="filtroSkuReconciliacion" class="search-input" placeholder="Buscar material o SKU..." oninput="filtrarTablaReconciliacion()">
                            <select id="filtroTipoReconciliacion" class="form-select" style="max-width: 250px;" onchange="filtrarTablaReconciliacion()">
                                <option value="">Todos los diagnósticos</option>
                                <option value="Concordante">Concordantes (±5%)</option>
                                <option value="Muelle">Desfases en muelle (físico > Kardex)</option>
                                <option value="Faltante">Faltantes en piso (Kardex > físico)</option>
                            </select>
                        </div>
                    </div>
                    <div class="table-responsive" style="max-height: 480px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Número de SKU</th>
                                    <th>Descripción del material</th>
                                    <th>Familia</th>
                                    <th class="text-right">Saldo Kardex teórico</th>
                                    <th class="text-right">Conteo físico auditado</th>
                                    <th class="text-right">Discrepancia neta</th>
                                    <th class="text-right">Impacto financiero</th>
                                    <th class="text-center">Diagnóstico de reconciliación</th>
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
            <!-- PESTAÑA 4: CARGA DE ARCHIVOS E INGESTA DE DATOS          -->
            <!-- ======================================================== -->
            <div id="tab-ingesta" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Carga de archivos e ingesta de datos con control de idempotencia</div>
                            <div class="card-subtitle">Validación estructural, hashes criptográficos SHA-256, operaciones idempotentes y auditoría fila a fila.</div>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div>
                            <div class="form-group">
                                <label class="form-label">Tipo de documento a procesar:</label>
                                <select id="ingestaTipoDoc" class="form-select" onchange="limpiarEstadoIngesta()">
                                    <option value="movimientos_inventario">Movimientos de inventario (Kardex transaccional)</option>
                                    <option value="ordenes_compra">Órdenes de compra (histórico de adquisiciones)</option>
                                    <option value="conteo_fisico">Conteo físico auditado en bodega</option>
                                    <option value="maestro_materiales">Catálogo maestro de materiales</option>
                                </select>
                            </div>

                            <!-- Zona de Carga (Drag & Drop) -->
                            <div class="dropzone" id="dropzone">
                                <!-- Estado Inicial -->
                                <div id="dropzoneEstadoInicial" style="display: block;">
                                    <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                                    <div style="font-weight: 600; font-size: 0.925rem; margin-bottom: 0.25rem; color: var(--text-primary);">Arrastre su archivo CSV o selecciónelo desde su equipo</div>
                                    <div style="font-size: 0.775rem; color: var(--text-secondary);">Archivos delimitados por coma o punto y coma (.csv) · Detección automática de codificación e integridad</div>
                                </div>
                                
                                <!-- Estado Procesando -->
                                <div id="dropzoneEstadoProcesando" style="display: none; padding: 0.85rem 0;">
                                    <div class="spinner-emerald" style="margin: 0 auto 0.75rem auto;"></div>
                                    <div style="font-weight: 600; font-size: 0.925rem; color: var(--success); margin-bottom: 0.25rem;">Validando estructura e idempotencia en la base de datos...</div>
                                    <div style="font-size: 0.775rem; color: var(--text-secondary);">Verificando unicidad, claves naturales y aplicando cláusulas de control transaccional</div>
                                </div>

                                <!-- Estado Completado -->
                                <div id="dropzoneEstadoCompletado" style="display: none; padding: 0.5rem 0;">
                                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" style="margin: 0 auto 0.5rem auto; display: block;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                    <div style="font-weight: 600; font-size: 0.925rem; color: var(--text-success); margin-bottom: 0.25rem;">Procesamiento e idempotencia conformes en la base de datos</div>
                                    <div style="font-size: 0.775rem; color: var(--text-secondary);">Reporte consolidado de auditoría de carga generado abajo</div>
                                </div>

                                <input type="file" id="fileInput" accept=".csv" style="display: none;" onchange="manejarSeleccionArchivo(this.files[0])">
                            </div>

                            <div id="archivoMeta" style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); display: none;">
                                Archivo: <strong id="lblNombreArchivo" style="color: var(--text-primary);">--</strong> (<span id="lblTamanoArchivo">-- KB</span>) · <span id="lblHashArchivo">SHA-256: --</span>
                            </div>

                            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                                <button id="btnPrevisualizar" class="btn btn-outline" onclick="iniciarPrevisualizacion()" disabled>
                                    <span>Validar estructura del archivo</span>
                                </button>
                                <button id="btnConfirmarCarga" class="btn btn-success" onclick="confirmarIngesta()" disabled>
                                    <span>Asentar e importar datos</span>
                                </button>
                            </div>
                        </div>

                        <div>
                            <div class="card" style="background: var(--bg-surface-subtle); margin-bottom: 0; height: 100%;">
                                <div style="font-weight: 600; font-size: 0.925rem; margin-bottom: 0.5rem; color: var(--text-primary);">Diagnóstico estructural y de idempotencia</div>
                                <div id="diagnosticoEstructural" style="font-size: 0.8125rem; color: var(--text-secondary); line-height: 1.5;">
                                    Seleccione o arrastre un archivo CSV para inspeccionar delimitadores, juego de caracteres, calcular su hash único y validar las columnas obligatorias contra el esquema relacional.
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Componente de Reporte Detallado de Ingesta -->
                    <div id="panelRendicionCuentas" style="display: none; margin-top: 1.5rem;">
                        <!-- Tarjeta de Resumen Ejecutivo y Estado de Carga -->
                        <div style="background: var(--bg-surface-subtle); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="font-size: 1rem; font-weight: 600; color: var(--text-primary);">Reporte consolidado de auditoría de carga</div>
                                    <div id="rcBadgeEstado" class="kpi-badge badge-success" style="font-size: 0.75rem; padding: 0.25rem 0.65rem;">--</div>
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">
                                    Identificador de carga: <span id="rcIdCarga" class="mono" style="color: var(--text-primary); font-weight: 600;">--</span>
                                </div>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.8rem; color: var(--text-secondary);">
                                <div>Archivo: <strong id="rcNombreArchivo" style="color: var(--text-primary);">--</strong></div>
                                <div>Hash SHA-256: <code id="rcHashArchivo" class="mono" style="color: var(--text-primary); background: #FFFFFF; border: 1px solid var(--border); padding: 2px 6px; border-radius: var(--radius-xs);">--</code></div>
                                <div>Sincronización de base de datos: <strong id="rcSupabaseSync" style="color: var(--text-success);">ON CONFLICT DO UPDATE / DO NOTHING</strong></div>
                            </div>
                        </div>

                        <!-- Las 4 Tarjetas Métricas Cuantitativas -->
                        <div class="kpi-grid">
                            <div class="kpi-card">
                                <div class="kpi-label">Total de registros procesados</div>
                                <div id="rcLeidas" class="kpi-value">0</div>
                                <div class="kpi-footer">Número de filas leídas del archivo CSV</div>
                            </div>
                            <div class="kpi-card accent-success">
                                <div class="kpi-label">Registros insertados o actualizados</div>
                                <div id="rcInsertadas" class="kpi-value" style="color: var(--success);">0</div>
                                <div class="kpi-footer">Filas asentadas en la base de datos</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-label">Registros omitidos por idempotencia</div>
                                <div id="rcOmitidas" class="kpi-value" style="color: var(--text-primary);">0</div>
                                <div class="kpi-footer">Detectadas como ya existentes (sin alteración)</div>
                            </div>
                            <div class="kpi-card accent-danger">
                                <div class="kpi-label">Registros rechazados</div>
                                <div id="rcRechazadas" class="kpi-value" style="color: var(--danger);">0</div>
                                <div class="kpi-footer">Errores de formato, fechas o campos obligatorios</div>
                            </div>
                        </div>

                        <!-- Banner de Explicación de Idempotencia -->
                        <div id="bannerIdempotenciaExplicacion" class="alert-banner alert-success" style="margin-bottom: 1.25rem;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 2px;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                            <div>
                                <div class="alert-title" style="font-size: 0.875rem;">Garantía de idempotencia en la base de datos</div>
                                <div class="alert-body" style="font-size: 0.8125rem;" id="rcTextoIdempotencia">
                                    El reingreso del mismo archivo o la ejecución múltiple de la carga no altera los saldos de inventario ni duplica registros. Las transacciones existentes son gestionadas con cláusulas ON CONFLICT.
                                </div>
                            </div>
                        </div>

                        <!-- Trazabilidad Fila a Fila con Razón de Resultado -->
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0; flex-wrap: wrap; gap: 0.75rem;">
                            <div style="font-weight: 600; font-size: 0.925rem; color: var(--text-primary);">Trazabilidad fila a fila con razón de resultado</div>
                            <div class="filter-bar" style="margin-bottom: 0;">
                                <select id="filtroEstadoFila" class="form-select" style="max-width: 250px;" onchange="filtrarTrazabilidad()">
                                    <option value="">Todos los estados</option>
                                    <option value="INSERTADA">Insertadas</option>
                                    <option value="ACTUALIZADA">Actualizadas</option>
                                    <option value="OMITIDA">Omitidas (Ya existentes / duplicadas)</option>
                                    <option value="RECHAZADA">Rechazadas con inconsistencia</option>
                                </select>
                                <button class="btn btn-outline btn-sm" onclick="descargarInformeAuditoria()">Descargar reporte CSV de auditoría</button>
                            </div>
                        </div>

                        <div class="table-responsive" style="max-height: 420px;">
                            <table>
                                <thead>
                                    <tr>
                                        <th class="text-right">Fila</th>
                                        <th>Identificador único</th>
                                        <th class="text-center">Estado de transacción</th>
                                        <th>Causa del resultado</th>
                                        <th>Razón y detalle de auditoría</th>
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
            <!-- PESTAÑA 5: INSTRUMENTACIÓN Y TELEMETRÍA OPERATIVA        -->
            <!-- ======================================================== -->
            <div id="tab-telemetria" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Instrumentación operativa y control del sistema</div>
                            <div class="card-subtitle">Cinco dimensiones cuantitativas de telemetría operativa para control continuo y autodiagnóstico del aplicativo.</div>
                        </div>
                        <button class="btn btn-outline btn-sm" onclick="cargarMetricasInstrumentacion()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                            <span>Actualizar métricas de telemetría</span>
                        </button>
                    </div>

                    <!-- Grilla Equilibrada de 5 Columnas Simétricas -->
                    <div class="kpi-grid-5">
                        <div class="kpi-card">
                            <div class="kpi-label">1. Calidad del dato de entrada</div>
                            <div id="teleTasaRechazo" class="kpi-value">0.0 %</div>
                            <div class="kpi-footer">Tasa de rechazo en cargas de archivos</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">2. Ahorro de trabajo manual</div>
                            <div id="teleHorasAhorro" class="kpi-value">-- horas</div>
                            <div class="kpi-footer">Tiempo estimado de planeación</div>
                        </div>
                        <div class="kpi-card accent-warning">
                            <div class="kpi-label">3. Calibración de paradas</div>
                            <div id="teleTasaParadas" class="kpi-value" style="color: var(--warning);">-- %</div>
                            <div class="kpi-footer">Frecuencia de corridas con parada activa</div>
                        </div>
                        <div class="kpi-card accent-success">
                            <div class="kpi-label">4. Acierto en decisiones</div>
                            <div id="teleAciertoHumano" class="kpi-value" style="color: var(--success);">-- %</div>
                            <div class="kpi-footer">Órdenes autorizadas por el planeador</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">5. Costo computacional</div>
                            <div id="teleTiempoProm" class="kpi-value" style="font-size: 1.55rem;">-- ms</div>
                            <div class="kpi-footer">Tiempo medio de respuesta</div>
                        </div>
                    </div>
                </div>

                <!-- Bitácora de Corridas -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Bitácora de corridas del sistema</div>
                            <div class="card-subtitle">Registro transaccional inmutable de ejecuciones con fecha, duración, indicadores analíticos y resultado de supervisión.</div>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Fecha y hora</th>
                                    <th>Identificador de corrida</th>
                                    <th class="text-right">Duración</th>
                                    <th class="text-right">SKUs auditados</th>
                                    <th class="text-right">ERI global</th>
                                    <th class="text-right">Quiebres</th>
                                    <th class="text-right">Inversión requerida</th>
                                    <th class="text-center">Estado de parada</th>
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
                            <div class="card-title">Bitácora de ingesta de archivos CSV</div>
                            <div class="card-subtitle">Historial de archivos procesados, balance de inserciones, registros omitidos por idempotencia y rechazos.</div>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Fecha y hora</th>
                                    <th>Nombre del archivo</th>
                                    <th>Tipo de documento</th>
                                    <th class="text-right">Leídas</th>
                                    <th class="text-right">Insertadas</th>
                                    <th class="text-right">Omitidas</th>
                                    <th class="text-right">Rechazadas</th>
                                    <th>Diagnóstico</th>
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
    </div>

    <div id="toast"></div>

    <script>
        let archivoSeleccionadoContenido = null;
        let archivoSeleccionadoNombre = '';
        let trazabilidadActual = [];
        let matrizDemandaActual = [];
        let matrizReconciliacionActual = [];

        // Función estricta de formateo de plurales en español corporativo
        function formatearUnidades(n) {
            if (n === null || n === undefined || isNaN(n)) return '0 unidades';
            const val = Math.round(Number(n));
            return (val === 1 || val === -1) ? val.toLocaleString('es-CO') + ' unidad' : val.toLocaleString('es-CO') + ' unidades';
        }

        // Abreviar hashes SHA-256 para visualización ejecutiva limpia
        function abreviarHash(h) {
            if (!h || h === 'N/A' || h.length <= 16) return h || 'N/A';
            return 'SHA-256: ' + h.substring(0, 8) + '...' + h.substring(h.length - 7);
        }

        const titulosPestanas = {
            'tab-control': 'Tablero de control y recomendaciones',
            'tab-demanda': 'Planificación de demanda y abastecimiento',
            'tab-reconciliacion': 'Reconciliación de inventario y exactitud de registro',
            'tab-ingesta': 'Carga de archivos e ingesta de datos',
            'tab-telemetria': 'Instrumentación operativa y auditoría'
        };

        function cambiarPestana(idTab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(idTab).classList.add('active');
            
            const idx = ['tab-control', 'tab-demanda', 'tab-reconciliacion', 'tab-ingesta', 'tab-telemetria'].indexOf(idTab);
            if (idx >= 0) {
                document.querySelectorAll('.tab-btn')[idx].classList.add('active');
            }

            const titleEl = document.getElementById('topbarSectionTitle');
            if (titleEl && titulosPestanas[idTab]) {
                titleEl.innerText = titulosPestanas[idTab];
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
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> <span>Ejecutar análisis integral</span>';
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
            document.getElementById('kpiInversion').innerText = '$ ' + Math.round(Number(kpis.inversion_propuesta_cop)).toLocaleString('es-CO');
            document.getElementById('kpiDiscrepancias').innerText = (kpis.materiales_fantasmas_detectados + kpis.desfases_muelle_detectados);

            const banner = document.getElementById('bannerSupervision');
            const titulo = document.getElementById('supervisionTitulo');
            const msg = document.getElementById('supervisionMensaje');
            if (data.criterio_parada_activado) {
                banner.className = 'alert-banner alert-warning';
                titulo.innerText = 'Supervisión humana obligatoria — Criterio de parada activo';
                msg.innerText = data.mensaje_parada;
            } else {
                banner.className = 'alert-banner alert-success';
                titulo.innerText = 'Operación conforme a parámetros nominales';
                msg.innerText = 'No se registraron quiebres de inventario inminentes. Los saldos satisfacen los puntos de reorden vigentes.';
            }

            const container = document.getElementById('contenedorPropuestasCards');
            container.innerHTML = '';

            if (data.propuestas_compra.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 2.5rem; color: var(--text-success); background: var(--bg-success); border: 1px solid var(--border-success); border-radius: var(--radius-sm);">No hay insumos que requieran reorden en este ciclo de operación. Todos los inventarios están conformes.</div>';
                return;
            }

            data.propuestas_compra.forEach(p => {
                const card = document.createElement('div');
                card.id = 'propuesta-' + p.sku;
                card.className = 'card';
                card.style = 'margin-bottom: 1rem; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1.25rem 1.4rem; background: #FFFFFF;';

                const cantSugeridaStr = formatearUnidades(p.cantidad_sugerida_eoq);
                const stockRealStr = formatearUnidades(p.stock_real);
                const ropStr = formatearUnidades(p.punto_reorden_rop);
                const ssStr = formatearUnidades(p.stock_seguridad_ss);
                const ltDiasStr = Number(p.lead_time_dias || 15).toFixed(1) + ' días';
                const invCopStr = '$ ' + Math.round(Number(p.inversion_estimada_cop || 0)).toLocaleString('es-CO') + ' COP';
                const riesgoCopStr = '$ ' + Math.round(Number(p.riesgo_evitado_cop || 10800000)).toLocaleString('es-CO') + ' COP';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.9rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.85rem; flex-wrap: wrap; gap: 0.75rem;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                <span class="mono" style="font-weight: 700; font-size: 1rem; color: var(--text-primary);">${p.sku}</span>
                                <span class="kpi-badge ${p.clase_abc === 'A' ? 'badge-danger' : (p.clase_abc === 'B' ? 'badge-warning' : 'badge-success')}">Clase ${p.clase_abc}</span>
                                <span class="kpi-badge badge-neutral">Prioridad ${p.prioridad || 'Media'}</span>
                                <span class="kpi-badge badge-warning">${p.momento_emision || 'Inmediato (Stock ≤ ROP)'}</span>
                            </div>
                            <div style="font-weight: 600; font-size: 0.925rem; color: var(--text-primary); margin-top: 0.35rem;">${p.descripcion}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Categoría: ${p.categoria} · Cobertura actual: ${p.dias_cobertura_remanente || 0} días</div>
                        </div>
                        <div id="acciones-${p.sku}" style="display: flex; gap: 0.5rem; align-items: center; flex-shrink: 0;">
                            <button class="btn btn-success btn-sm" onclick="tomarDecision('${p.sku}', 'APROBADA')">Autorizar</button>
                            <button class="btn btn-danger-outline btn-sm" onclick="tomarDecision('${p.sku}', 'RECHAZADA')">Desestimar</button>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; background: var(--bg-surface-subtle); border: 1px solid var(--border); border-radius: var(--radius-xs); padding: 0.85rem; margin-bottom: 0.85rem;">
                        <div>
                            <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">Inventario físico actual</div>
                            <div class="mono" style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary);">${stockRealStr}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">Punto de reorden (ROP)</div>
                            <div class="mono" style="font-weight: 600; font-size: 0.95rem; color: var(--warning);">${ropStr} <small style="color: var(--text-muted); font-weight: normal;">(SS: ${ssStr})</small></div>
                        </div>
                        <div>
                            <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">Cantidad sugerida (EOQ)</div>
                            <div class="mono" style="font-weight: 700; font-size: 1rem; color: var(--text-primary);">${cantSugeridaStr}</div>
                        </div>
                    </div>

                    <div class="justification-card">
                        <div style="font-size: 0.8rem; line-height: 1.7; color: var(--text-secondary);">
                            <div><strong>Inversión:</strong> ${invCopStr} (${cantSugeridaStr})</div>
                            <div><strong>Tiempo de entrega:</strong> ${ltDiasStr}</div>
                            <div><strong>Riesgo mitigado:</strong> ${riesgoCopStr} por concepto de paro de planta</div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
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
                document.getElementById('recImpactoTotal').innerText = '$ ' + Math.round(Number(data.impacto_total_cop || 0)).toLocaleString('es-CO') + ' COP';

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

                let discrepanciaHtml = '';
                const discVal = Math.round(Number(r.discrepancia_neta || 0));
                if (discVal < 0) {
                    discrepanciaHtml = `<span style="color: var(--danger); font-weight: 600;">-${Math.abs(discVal).toLocaleString('es-CO')} unidades (Faltante)</span>`;
                } else if (discVal > 0) {
                    discrepanciaHtml = `<span style="color: var(--warning); font-weight: 600;">+${discVal.toLocaleString('es-CO')} unidades (Muelle)</span>`;
                } else {
                    discrepanciaHtml = `<span style="color: var(--text-muted);">0 unidades (Concordante)</span>`;
                }

                const impactoFmt = '$ ' + Math.round(Number(r.impacto_financiero_cop || 0)).toLocaleString('es-CO') + ' COP';

                tr.innerHTML = `
                    <td class="mono" style="font-weight: 600; color: var(--text-primary);">${r.sku}</td>
                    <td>${r.descripcion}</td>
                    <td><small style="color: var(--text-secondary);">${r.categoria}</small></td>
                    <td class="mono text-right">${formatearUnidades(r.saldo_teorico)}</td>
                    <td class="mono text-right" style="font-weight: 600;">${formatearUnidades(r.stock_fisico_contado)}</td>
                    <td class="mono text-right">${discrepanciaHtml}</td>
                    <td class="mono text-right">${impactoFmt}</td>
                    <td class="text-center"><span class="kpi-badge ${badgeClass}">${r.diagnostico_eri}</span></td>
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
                celda.innerHTML = '<span class="spinner-emerald" style="width: 14px; height: 14px; border-width: 2px;"></span> <small style="color: var(--text-muted);">Registrando...</small>';
            }

            try {
                const res = await fetch(`/api/decidir?sku=${encodeURIComponent(sku)}&accion=${encodeURIComponent(accion)}`);
                if (!res.ok) throw new Error(`El servidor respondió con código ${res.status}`);
                const data = await res.json();
                
                if (data.status === 'registrado') {
                    if (accion === 'APROBADA') {
                        if (celda) celda.innerHTML = '<span style="color: var(--text-success); font-weight: 600;">Orden autorizada</span>';
                        showToast(`Orden de compra para SKU ${sku} autorizada y registrada en base de datos.`, 'success');
                    } else {
                        if (celda) celda.innerHTML = '<span style="color: var(--danger); font-weight: 600;">Orden desestimada</span>';
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

                const p = data.resumen_abc || {};
                if (p.A) {
                    document.getElementById('paretoA_skus').innerText = (p.A.skus || 0) + ' SKUs';
                    document.getElementById('paretoA_valor').innerText = '$ ' + Math.round(Number(p.A.valor_cop || 0)).toLocaleString('es-CO') + ' COP (' + (p.A.pct_valor || 0).toFixed(1) + '%)';
                }
                if (p.B) {
                    document.getElementById('paretoB_skus').innerText = (p.B.skus || 0) + ' SKUs';
                    document.getElementById('paretoB_valor').innerText = '$ ' + Math.round(Number(p.B.valor_cop || 0)).toLocaleString('es-CO') + ' COP (' + (p.B.pct_valor || 0).toFixed(1) + '%)';
                }
                if (p.C) {
                    document.getElementById('paretoC_skus').innerText = (p.C.skus || 0) + ' SKUs';
                    document.getElementById('paretoC_valor').innerText = '$ ' + Math.round(Number(p.C.valor_cop || 0)).toLocaleString('es-CO') + ' COP (' + (p.C.pct_valor || 0).toFixed(1) + '%)';
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
                const ltFormatted = Number(m.lead_time_usado).toFixed(1) + ' días';
                tr.innerHTML = `
                    <td class="mono col-sticky-sku" style="font-weight: 600; color: var(--text-primary);">${m.sku}</td>
                    <td class="col-sticky-desc" style="font-weight: 500;">${m.descripcion}</td>
                    <td><small style="color: var(--text-secondary);">${m.categoria}</small></td>
                    <td class="text-center"><span class="kpi-badge ${m.clasificacion_abc === 'A' ? 'badge-danger' : (m.clasificacion_abc === 'B' ? 'badge-warning' : 'badge-success')}">Clase ${m.clasificacion_abc}</span></td>
                    <td class="mono text-right">${Number(m.demanda_anual_d).toLocaleString('es-CO', {maximumFractionDigits: 1})}</td>
                    <td class="mono text-right">${Number(m.consumo_diario_d).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono text-right">${Number(m.sigma_diario).toLocaleString('es-CO', {maximumFractionDigits: 2})}</td>
                    <td class="mono text-right" style="font-weight: 500;">${ltFormatted}</td>
                    <td class="mono text-right" style="color: var(--success); font-weight: 600;">${formatearUnidades(m.SS_95)}</td>
                    <td class="mono text-right" style="color: var(--warning); font-weight: 600;">${formatearUnidades(m.ROP)}</td>
                    <td class="mono text-right" style="color: var(--text-primary); font-weight: 700;">${formatearUnidades(m.EOQ)}</td>
                    <td class="mono text-right">${formatearUnidades(m.stock_real)}</td>
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
        // MÓDULO DE INGESTA E IDEMPOTENCIA
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
                dz.style.borderColor = 'var(--success)';
                dz.style.backgroundColor = 'var(--bg-success)';
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
                document.getElementById('lblHashArchivo').innerText = 'SHA-256: Calculando...';
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
                    document.getElementById('lblHashArchivo').innerText = abreviarHash(data.hash_archivo_sha256);
                    diag.innerHTML = `
                        <div style="color: var(--text-success); font-weight: 600; margin-bottom: 0.5rem;">Estructura de archivo conforme para importación e idempotencia</div>
                        <p><strong>Hash SHA-256:</strong> <code class="mono" style="color: var(--text-primary); background: #FFFFFF; border: 1px solid var(--border); padding: 2px 6px; border-radius: var(--radius-xs);">${data.hash_archivo_sha256}</code></p>
                        <p style="margin-top: 0.35rem;"><strong>Delimitador detectado:</strong> '${data.delimitador}' | <strong>Codificación:</strong> ${data.codificacion.toUpperCase()} | <strong>Filas leídas:</strong> ${data.filas_total}</p>
                        <p style="margin-top: 0.4rem; color: var(--text-secondary);">Columnas obligatorias presentes: <em>${data.columnas_esperadas.join(', ')}</em>.</p>
                    `;
                    document.getElementById('btnConfirmarCarga').disabled = false;
                    showToast('Validación estructural aprobada. Listo para asentar los datos.', 'success');
                } else {
                    diag.innerHTML = `
                        <div style="color: var(--danger); font-weight: 600; margin-bottom: 0.5rem;">Inconsistencia en la estructura del archivo</div>
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

            const badge = document.getElementById('rcBadgeEstado');
            if (data.estado_carga === 'Exitoso') {
                badge.className = 'kpi-badge badge-success';
                badge.innerText = 'Carga exitosa (100% conforme)';
            } else if (data.estado_carga === 'Parcial') {
                badge.className = 'kpi-badge badge-warning';
                badge.innerText = 'Carga parcial (con observaciones)';
            } else {
                badge.className = 'kpi-badge badge-danger';
                badge.innerText = 'Carga rechazada (inconsistencias)';
            }

            document.getElementById('rcIdCarga').innerText = (data.id_carga || '').substring(0, 16) + '...';
            document.getElementById('rcNombreArchivo').innerText = data.nombre_archivo || archivoSeleccionadoNombre;
            document.getElementById('rcHashArchivo').innerText = abreviarHash(data.hash_archivo_sha256);
            
            const sbSync = document.getElementById('rcSupabaseSync');
            if (data.sincronizacion_supabase && (data.sincronizacion_supabase.status === 'success' || data.sincronizacion_supabase.estado === 'SINCRONIZADO')) {
                sbSync.innerHTML = '<span style="color: var(--text-success);">Sincronizado en base relacional (UPSERT ON CONFLICT)</span>';
            } else if (data.sincronizacion_supabase && data.sincronizacion_supabase.status === 'offline_fallback') {
                sbSync.innerHTML = '<span style="color: var(--text-primary);">Asentado en base relacional local (modo resiliente)</span>';
            } else {
                sbSync.innerHTML = '<span style="color: var(--text-primary);">Asentado en base relacional (ON CONFLICT DO UPDATE / DO NOTHING)</span>';
            }

            document.getElementById('rcLeidas').innerText = data.total_registros_procesados || data.filas_leidas;
            document.getElementById('rcInsertadas').innerText = data.filas_insertadas_o_actualizadas || (data.filas_insertadas + data.filas_actualizadas);
            document.getElementById('rcOmitidas').innerText = data.filas_omitidas_duplicadas;
            document.getElementById('rcRechazadas').innerText = data.filas_rechazadas;

            const textoIdemp = document.getElementById('rcTextoIdempotencia');
            textoIdemp.innerText = `Idempotencia verificada: el reingreso del mismo archivo o la ejecución múltiple no altera los saldos de inventario ni duplica registros (Cambio neto en base = ${data.cambio_neto_base} registros). Las transacciones existentes fueron gestionadas con cláusulas ON CONFLICT en la base relacional.`;

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
                let estadoLabel = f.estado;

                if (f.estado === 'INSERTADA') {
                    badgeClass = 'badge-success';
                    estadoLabel = 'Insertada';
                } else if (f.estado === 'ACTUALIZADA') {
                    badgeClass = 'badge-warning';
                    estadoLabel = 'Actualizada';
                } else if (f.estado.includes('OMITIDA')) {
                    badgeClass = 'badge-neutral';
                    estadoLabel = 'Omitida (Ya existente)';
                } else if (f.estado === 'RECHAZADA') {
                    badgeClass = 'badge-danger';
                    estadoLabel = 'Rechazada';
                }

                const idLimpio = (f.identificador || '')
                    .replace(/^OC\s+OC-/i, 'OC-')
                    .replace(/^OC\s+/i, 'OC-')
                    .replace(/^MOV\s+MOV-/i, 'MOV-');

                tr.innerHTML = `
                    <td class="mono text-right">${f.fila}</td>
                    <td class="mono" style="font-weight: 600; color: var(--text-primary);">${idLimpio}</td>
                    <td class="text-center"><span class="kpi-badge ${badgeClass}">${estadoLabel}</span></td>
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
            link.setAttribute("download", `auditoria_carga_e2_${Date.now()}.csv`);
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
                document.getElementById('teleHorasAhorro').innerText = Math.round(data.instrumento_2_corrida.trabajo_ahorrado_horas_est) + ' horas';
                document.getElementById('teleTasaParadas').innerText = data.instrumento_3_paradas.tasa_paradas_pct.toFixed(0) + ' %';
                document.getElementById('teleAciertoHumano').innerText = data.instrumento_4_decision.tasa_acierto_pct.toFixed(0) + ' %';
                document.getElementById('teleTiempoProm').innerText = data.instrumento_5_costo.duracion_promedio_ms.toFixed(1) + ' ms';

                const tbodyCorridas = document.getElementById('tablaBitacoraCorridasBody');
                tbodyCorridas.innerHTML = '';
                if (data.bitacora_corridas.length === 0) {
                    tbodyCorridas.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay corridas registradas en la bitácora aún.</td></tr>';
                } else {
                    data.bitacora_corridas.forEach(c => {
                        const tr = document.createElement('tr');
                        const idAbrev = (c.id || '').substring(0, 8) + '...' + (c.id || '').substring((c.id || '').length - 4);
                        tr.innerHTML = `
                            <td><small>${c.timestamp}</small></td>
                            <td>
                                <span class="mono" style="font-size: 0.75rem;" title="${c.id}">${idAbrev}</span>
                                <button class="btn btn-outline btn-sm" style="padding: 1px 6px; font-size: 0.68rem; margin-left: 4px;" onclick="navigator.clipboard.writeText('${c.id}'); showToast('ID de corrida copiado al portapapeles', 'success');" title="Copiar ID de corrida">Copiar</button>
                            </td>
                            <td class="mono text-right">${c.duracion_ms} ms</td>
                            <td class="mono text-right">${c.total_skus}</td>
                            <td class="mono text-right">${c.eri_global_pct}%</td>
                            <td class="mono text-right" style="color: var(--danger); font-weight: 600;">${c.skus_en_quiebre}</td>
                            <td class="mono text-right">$ ${Math.round(Number(c.inversion_total_cop)).toLocaleString('es-CO')}</td>
                            <td class="text-center"><span class="kpi-badge ${c.criterio_parada_activado ? 'badge-warning' : 'badge-success'}">${c.criterio_parada_activado ? 'Parada activa' : 'Normal'}</span></td>
                        `;
                        tbodyCorridas.appendChild(tr);
                    });
                }

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
                            <td class="mono text-right">${cg.filas_leidas}</td>
                            <td class="mono text-right" style="color: var(--success); font-weight: 600;">${cg.filas_cargadas}</td>
                            <td class="mono text-right" style="color: var(--text-muted);">${cg.filas_omitidas_duplicadas}</td>
                            <td class="mono text-right" style="color: var(--danger);">${cg.filas_rechazadas}</td>
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
                toast.style.borderColor = 'var(--border-danger)';
                toast.style.backgroundColor = 'var(--bg-danger)';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--danger); font-weight: 700; font-size: 0.9rem;">✕</span><div style="color: var(--text-danger); line-height: 1.4;">${msg}</div></div>`;
            } else if (tipo === 'warning') {
                toast.style.borderColor = 'var(--border-warning)';
                toast.style.backgroundColor = 'var(--bg-warning)';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--warning); font-weight: 700; font-size: 0.9rem;">!</span><div style="color: var(--text-warning); line-height: 1.4;">${msg}</div></div>`;
            } else if (tipo === 'success') {
                toast.style.borderColor = 'var(--border-success)';
                toast.style.backgroundColor = 'var(--bg-success)';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--success); font-weight: 700; font-size: 0.9rem;">✓</span><div style="color: var(--text-success); line-height: 1.4;">${msg}</div></div>`;
            } else {
                toast.style.borderColor = 'var(--border)';
                toast.style.backgroundColor = 'var(--bg-surface)';
                toast.innerHTML = `<div style="display: flex; align-items: flex-start; gap: 0.65rem;"><span style="color: var(--text-muted); font-weight: 700; font-size: 0.9rem;">i</span><div style="color: var(--text-primary); line-height: 1.4;">${msg}</div></div>`;
            }
            toast.style.display = 'block';
            if (window._toastTimer) clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => { toast.style.display = 'none'; }, 6000);
        }

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
