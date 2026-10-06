"""
APLICACIÓN LOCAL DE CONTROL Y SUPERVISIÓN - E2 SAS (Producción 4.0 / Énfasis II)
Tablero de Control de Inventarios:
  - Disparo de Orquestación con 1 Clic
  - Indicadores en Tiempo Real (ERI, Quiebres, Inversión, Pareto ABC)
  - Tabla de Propuestas con Justificación en Lenguaje Natural (IA)
  - Botones de Aprobación / Rechazo Humano con Registro de Auditoría
"""

import os
import sys
import json
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import orquestador
from nucleo import datos

PORT = 8501

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2 SAS — Tablero de Reposición y Orquestación</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --surface: rgba(18, 26, 43, 0.85);
            --surface-card: rgba(26, 38, 63, 0.65);
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(14, 165, 233, 0.4);
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --accent: #38bdf8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --radius: 14px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body { background: radial-gradient(circle at 50% 0%, #172554 0%, #0b0f19 80%); color: var(--text); min-height: 100vh; padding: 2.5rem 2rem; }

        .container { max-width: 1280px; margin: 0 auto; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }
        .logo-badge { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); background: rgba(56, 189, 248, 0.1); padding: 0.35rem 0.8rem; border-radius: 20px; border: 1px solid rgba(56, 189, 248, 0.25); display: inline-block; margin-bottom: 0.5rem; }
        h1 { font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px; }
        p.subtitle { color: var(--text-muted); font-size: 1rem; margin-top: 0.2rem; }

        /* Actions Bar */
        .actions-bar { display: flex; gap: 1rem; align-items: center; }
        button.btn-run {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #fff;
            border: none;
            padding: 0.9rem 1.8rem;
            font-size: 1.05rem;
            font-weight: 600;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
            display: flex;
            align-items: center;
            gap: 0.6rem;
            transition: all 0.2s ease;
        }
        button.btn-run:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(37, 99, 235, 0.6); }
        button.btn-run:active { transform: translateY(0); }

        /* KPIs */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1.2rem; margin-bottom: 2.5rem; }
        .kpi-card { background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; backdrop-filter: blur(12px); }
        .kpi-title { font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 0.4rem; }
        .kpi-value { font-size: 2rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
        .kpi-badge { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 6px; display: inline-block; margin-top: 0.5rem; font-weight: 600; }
        
        /* Banner de Parada */
        .supervision-banner { background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: var(--radius); padding: 1.2rem 1.5rem; margin-bottom: 2.5rem; display: flex; align-items: center; gap: 1rem; }
        .supervision-banner.safe { background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.35); }
        .supervision-icon { font-size: 1.8rem; }

        /* Table Section */
        .section-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 1.2rem; }
        .section-title { font-size: 1.4rem; font-weight: 600; }
        
        .table-container { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; backdrop-filter: blur(16px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: rgba(255, 255, 255, 0.03); color: var(--text-muted); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; padding: 1.1rem 1.2rem; border-bottom: 1px solid var(--border); }
        td { padding: 1.2rem; border-bottom: 1px solid var(--border); vertical-align: middle; font-size: 0.95rem; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }

        .sku-tag { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent); background: rgba(56, 189, 248, 0.1); padding: 0.2rem 0.5rem; border-radius: 6px; }
        .badge-abc { font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem; display: inline-block; }
        .badge-A { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-B { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .badge-C { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }

        .justification-box { font-size: 0.9rem; color: #cbd5e1; line-height: 1.45; background: rgba(0,0,0,0.25); padding: 0.75rem 1rem; border-radius: 8px; border-left: 3px solid var(--accent); }

        .btn-decision { padding: 0.55rem 1rem; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }
        .btn-approve { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); margin-right: 0.4rem; }
        .btn-approve:hover { background: var(--success); color: #fff; }
        .btn-reject { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .btn-reject:hover { background: var(--danger); color: #fff; }

        .spinner { display: inline-block; width: 18px; height: 18px; border: 3px solid rgba(255,255,255,.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Toast */
        #toast { position: fixed; bottom: 2rem; right: 2rem; background: #1e293b; color: #fff; padding: 1rem 1.5rem; border-radius: 10px; border: 1px solid var(--border-highlight); box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: none; z-index: 999; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <span class="logo-badge">Producción 4.0 · UdeM</span>
                <h1>Tablero de Orquestación y Reposición</h1>
                <p class="subtitle">E2 SAS — Sistema de Decisión Asistida con Criterio de Parada y Supervisión Humana</p>
            </div>
            <div class="actions-bar">
                <button id="btnRun" class="btn-run" onclick="correrOrquestacion()">
                    <span id="btnIcon">⚡</span>
                    <span id="btnText">Correr Reposición</span>
                </button>
            </div>
        </header>

        <!-- Banner de Supervisión -->
        <div id="supervisionBanner" class="supervision-banner">
            <div class="supervision-icon">🛑</div>
            <div>
                <strong style="font-size: 1.05rem;">Criterio de Parada Activo (Supervisión Humana Requerida)</strong>
                <p id="supervisionMsg" style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.2rem;">
                    El sistema detectó necesidades de reorden y se ha detenido. Ninguna orden de compra compromete dinero sin la aprobación explícita del planeador.
                </p>
            </div>
        </div>

        <!-- KPIs -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Exactitud de Inventario (ERI)</div>
                <div id="kpiEri" class="kpi-value">-- %</div>
                <span id="badgeEri" class="kpi-badge badge-A">Tolerancia ±5%</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">SKUs en Riesgo de Quiebre</div>
                <div id="kpiQuiebres" class="kpi-value" style="color: #f87171;">--</div>
                <span class="kpi-badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">Stock ≤ ROP</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Inversión Sugerida (EOQ)</div>
                <div id="kpiInversion" class="kpi-value" style="font-size: 1.6rem; color: #38bdf8;">$ --</div>
                <span class="kpi-badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8;">Presupuesto Requerido</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Materiales Fantasmas (Q3)</div>
                <div id="kpiFantasmas" class="kpi-value" style="color: #fbbf24;">--</div>
                <span class="kpi-badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">Kardex > Físico</span>
            </div>
        </div>

        <!-- Tabla de Propuestas -->
        <div class="section-header">
            <div>
                <div class="section-title">Propuestas de Compra Generadas por la IA</div>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Revise la justificación contextual y apruebe o rechace cada fila para registrar en la base.</p>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Clase ABC</th>
                        <th>Stock Actual</th>
                        <th>Punto Reorden</th>
                        <th>Pedido Sugerido (EOQ)</th>
                        <th style="width: 42%;">Justificación en Lenguaje Natural</th>
                        <th>Decisión Humana</th>
                    </tr>
                </thead>
                <tbody id="tablaPropuestas">
                    <tr>
                        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 3rem;">
                            Haga clic en <strong>"Correr Reposición"</strong> para ejecutar la orquestación de extremo a extremo.
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        async function correrOrquestacion() {
            const btn = document.getElementById('btnRun');
            const icon = document.getElementById('btnIcon');
            const text = document.getElementById('btnText');
            
            btn.disabled = true;
            icon.innerHTML = '<span class="spinner"></span>';
            text.innerText = 'Orquestando módulos...';

            try {
                const response = await fetch('/api/correr');
                const data = await response.json();
                renderTablero(data);
                showToast('✅ Orquestación completada exitosamente.');
            } catch (err) {
                showToast('❌ Error al ejecutar la orquestación: ' + err.message);
            } finally {
                btn.disabled = false;
                icon.innerHTML = '⚡';
                text.innerText = 'Correr Reposición';
            }
        }

        function renderTablero(data) {
            if (data.status !== 'completado') {
                showToast('⚠️ Error: ' + data.mensaje);
                return;
            }

            const kpis = data.kpis;
            document.getElementById('kpiEri').innerText = kpis.eri_global_pct + '%';
            document.getElementById('kpiQuiebres').innerText = kpis.skus_en_quiebre;
            document.getElementById('kpiInversion').innerText = '$' + Number(kpis.inversion_propuesta_cop).toLocaleString('es-CO');
            document.getElementById('kpiFantasmas').innerText = kpis.materiales_fantasmas_detectados;

            const banner = document.getElementById('supervisionBanner');
            const msg = document.getElementById('supervisionMsg');
            if (data.criterio_parada_activado) {
                banner.className = 'supervision-banner';
                banner.querySelector('.supervision-icon').innerText = '🛑';
                msg.innerText = data.mensaje_parada;
            } else {
                banner.className = 'supervision-banner safe';
                banner.querySelector('.supervision-icon').innerText = '✅';
                msg.innerText = 'Operación en parámetros normales. No hay quiebres inminentes de inventario.';
            }

            const tbody = document.getElementById('tablaPropuestas');
            tbody.innerHTML = '';

            if (data.propuestas_compra.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: #34d399;">✅ No hay materiales bajo el punto de reorden en este ciclo.</td></tr>';
                return;
            }

            data.propuestas_compra.forEach((p, idx) => {
                const tr = document.createElement('tr');
                tr.id = 'row-' + p.sku;
                tr.innerHTML = `
                    <td>
                        <span class="sku-tag">${p.sku}</span><br>
                        <strong style="font-size: 0.95rem; color: #fff;">${p.descripcion}</strong><br>
                        <small style="color: var(--text-muted);">${p.categoria}</small>
                    </td>
                    <td><span class="badge-abc badge-${p.clase_abc}">Clase ${p.clase_abc}</span></td>
                    <td><strong style="font-family: 'JetBrains Mono';">${p.stock_real}</strong> unids</td>
                    <td><strong style="font-family: 'JetBrains Mono'; color: #fbbf24;">${p.punto_reorden_rop}</strong> unids</td>
                    <td>
                        <strong style="font-family: 'JetBrains Mono'; color: #38bdf8; font-size: 1.1rem;">${p.cantidad_sugerida_eoq}</strong> unids<br>
                        <small style="color: var(--text-muted);">$${Number(p.inversion_estimada_cop).toLocaleString('es-CO')}</small>
                    </td>
                    <td>
                        <div class="justification-box">
                            🤖 ${p.justificacion_ejecutiva}
                        </div>
                    </td>
                    <td id="actions-${p.sku}">
                        <button class="btn-decision btn-approve" onclick="decidir('${p.sku}', 'APROBADA')">✓ Aprobar</button>
                        <button class="btn-decision btn-reject" onclick="decidir('${p.sku}', 'RECHAZADA')">✗ Rechazar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function decidir(sku, decision) {
            try {
                const res = await fetch(`/api/decidir?sku=${sku}&accion=${decision}`);
                const data = await res.json();
                
                const actionsCell = document.getElementById('actions-' + sku);
                if (decision === 'APROBADA') {
                    actionsCell.innerHTML = '<span style="color: #34d399; font-weight: 700;">✓ APROBADA (Registrada)</span>';
                    showToast(`✅ Orden para SKU ${sku} APROBADA y asentada en la base.`);
                } else {
                    actionsCell.innerHTML = '<span style="color: #f87171; font-weight: 700;">✗ RECHAZADA (Registrada)</span>';
                    showToast(`⚠️ Orden para SKU ${sku} RECHAZADA y registrada.`);
                }
            } catch (err) {
                showToast('❌ Error al registrar decisión: ' + err.message);
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        // Cargar automáticamente al abrir
        window.onload = correrOrquestacion;
    </script>
</body>
</html>
"""

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
        elif parsed.path == '/api/correr':
            resultado = orquestador.ejecutar_orquestacion()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode('utf-8'))
            
        elif parsed.path == '/api/decidir':
            query = parse_qs(parsed.query)
            sku = query.get('sku', [''])[0]
            accion = query.get('accion', ['APROBADA'])[0]
            
            res = datos.registrar_decision(sku, accion, planeador="Planeador Compras E2")
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_error(404, "Ruta no encontrada")

def iniciar_servidor():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n========================================================")
    print(f"🚀 Tablero Local de Reposición E2 SAS iniciado")
    print(f"🌐 Servidor corriendo en: {url}")
    print(f"🛑 Para apagar el servidor: Presione Ctrl+C en esta consola")
    print(f"========================================================\n")
    
    # Abrir navegador automáticamente
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nApagando servidor...")
        httpd.server_close()

if __name__ == '__main__':
    iniciar_servidor()
