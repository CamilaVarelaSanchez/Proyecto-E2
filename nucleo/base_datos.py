"""
Módulo del Núcleo: BASE DE DATOS (Capa Relacional SQL & Kardex)
Responsabilidad Única: Administrar el esquema relacional, conexiones y operaciones
                     idempotentes sobre la base de datos (SQLite canónico local + Supabase).
Principio: "El archivo no es el dato. Ningún módulo lee del archivo: todos leen de la base."
"""

import os
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

def get_base_dir():
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur and os.path.dirname(cur) != cur:
        if os.path.exists(os.path.join(cur, 'datos_limpios')) or os.path.exists(os.path.join(cur, 'datos_iniciales')):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()

DB_PATH = os.path.join(get_base_dir(), 'datos_limpios', 'kardex_e2.db')

def get_connection():
    """Retorna una conexión a la base de datos relacional SQLite."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Habilitar soporte de llaves foráneas y modo WAL para concurrencia
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def inicializar_esquema():
    """Crea las tablas relacionales y bitácoras si no existen."""
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Catálogo Maestro de Materiales
    cur.execute("""
    CREATE TABLE IF NOT EXISTS maestro_materiales (
        sku TEXT PRIMARY KEY,
        descripcion TEXT NOT NULL,
        categoria TEXT NOT NULL,
        unidad TEXT NOT NULL,
        costo_unitario REAL NOT NULL,
        lead_time_declarado_dias INTEGER NOT NULL
    );
    """)

    # 2. Catálogo Maestro de Productos Terminados
    cur.execute("""
    CREATE TABLE IF NOT EXISTS maestro_productos (
        producto TEXT PRIMARY KEY,
        nombre_producto TEXT NOT NULL
    );
    """)

    # 3. Movimientos de Inventario (Kardex Transaccional Idempotente)
    # id_movimiento es un hash determinístico de negocio para evitar duplicación al recargar
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_inventarios (
        id_movimiento TEXT PRIMARY KEY,
        fecha TEXT NOT NULL,
        sku TEXT NOT NULL,
        tipo_movimiento TEXT NOT NULL,
        cantidad REAL NOT NULL,
        documento TEXT,
        bodega TEXT,
        usuario TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (sku) REFERENCES maestro_materiales(sku)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mov_sku ON movimientos_inventarios (sku);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos_inventarios (fecha);")

    # 4. Órdenes de Compra
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ordenes_compra (
        orden_compra TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        proveedor TEXT,
        cantidad REAL NOT NULL,
        fecha_pedido TEXT NOT NULL,
        fecha_recepcion TEXT,
        costo_unitario REAL,
        estado TEXT,
        lead_time_dias INTEGER,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (sku) REFERENCES maestro_materiales(sku)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_oc_sku ON ordenes_compra (sku);")

    # 5. Conteo Físico Auditado
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conteo_fisico (
        sku TEXT PRIMARY KEY,
        stock_fisico_contado REAL NOT NULL,
        fecha_conteo TEXT,
        auditor TEXT,
        FOREIGN KEY (sku) REFERENCES maestro_materiales(sku)
    );
    """)

    # 6. Inventario Inicial
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventario_inicial (
        sku TEXT PRIMARY KEY,
        stock_inicial REAL NOT NULL,
        fecha_corte TEXT,
        FOREIGN KEY (sku) REFERENCES maestro_materiales(sku)
    );
    """)

    # 6.1 Inventario paralelo reportado por el jefe de bodega
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventario_bodega_jefe (
        codigo TEXT PRIMARY KEY,
        material TEXT,
        conteo_jefe INTEGER,
        observacion TEXT,
        FOREIGN KEY (codigo) REFERENCES maestro_materiales(sku)
    );
    """)

    # 7. Plan de Producción
    cur.execute("""
    CREATE TABLE IF NOT EXISTS plan_produccion (
        id_plan TEXT PRIMARY KEY,
        periodo TEXT NOT NULL,
        producto TEXT NOT NULL,
        cantidad_planeada REAL NOT NULL,
        cantidad_real REAL NOT NULL,
        FOREIGN KEY (producto) REFERENCES maestro_productos(producto)
    );
    """)

    # 8. Lista de Materiales (BOM)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bom (
        id_bom TEXT PRIMARY KEY,
        producto TEXT NOT NULL,
        sku_material TEXT NOT NULL,
        cantidad_por_unidad REAL NOT NULL,
        unidad TEXT,
        FOREIGN KEY (producto) REFERENCES maestro_productos(producto),
        FOREIGN KEY (sku_material) REFERENCES maestro_materiales(sku)
    );
    """)

    # 9. BITÁCORA DE CARGAS (Instrumento 1: Rendición de cuentas de ingestas)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bitacora_cargas (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        nombre_archivo TEXT NOT NULL,
        tipo_documento TEXT NOT NULL,
        filas_leidas INTEGER NOT NULL,
        filas_cargadas INTEGER NOT NULL,
        filas_rechazadas INTEGER NOT NULL,
        filas_omitidas_duplicadas INTEGER NOT NULL,
        detalle_rechazos TEXT,
        usuario TEXT DEFAULT 'Operador Ingesta',
        hash_archivo_sha256 TEXT
    );
    """)
    try:
        cur.execute("ALTER TABLE bitacora_cargas ADD COLUMN hash_archivo_sha256 TEXT;")
    except Exception:
        pass

    # 10. BITÁCORA DE CORRIDAS (Instrumentos 2, 3, 5: Rendición de cuentas del sistema)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bitacora_corridas (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        duracion_ms REAL NOT NULL,
        total_skus INTEGER NOT NULL,
        eri_global_pct REAL NOT NULL,
        skus_en_quiebre INTEGER NOT NULL,
        inversion_total_cop REAL NOT NULL,
        materiales_fantasmas INTEGER NOT NULL,
        desfases_muelle INTEGER NOT NULL,
        criterio_parada_activado INTEGER NOT NULL,
        motivo_parada TEXT,
        status TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS control_ingesta_supabase (
        tipo_documento TEXT NOT NULL,
        hash_archivo_sha256 TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        PRIMARY KEY (tipo_documento, hash_archivo_sha256)
    );
    """)

    # 11. PROPUESTAS DE REPOSICIÓN GENERADAS POR CORRIDA
    cur.execute("""
    CREATE TABLE IF NOT EXISTS propuestas_reposicion (
        id TEXT PRIMARY KEY,
        corrida_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        descripcion TEXT,
        categoria TEXT,
        clase_abc TEXT,
        stock_real REAL,
        punto_reorden_rop REAL,
        stock_seguridad_ss REAL,
        cantidad_sugerida_eoq REAL,
        costo_unitario_cop REAL,
        inversion_estimada_cop REAL,
        justificacion_ejecutiva TEXT,
        estado_decision TEXT DEFAULT 'PENDIENTE',
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (corrida_id) REFERENCES bitacora_corridas(id)
    );
    """)

    # 12. REGISTRO DE DECISIONES HUMANAS (Instrumento 4: Acierto del sistema)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS registro_decisiones_compras (
        id TEXT PRIMARY KEY,
        corrida_id TEXT,
        sku TEXT NOT NULL,
        decision TEXT NOT NULL,
        planeador TEXT NOT NULL,
        motivo TEXT,
        timestamp TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def poblar_estado_inicial_si_vacio():
    """
    Si la base de datos no tiene datos, la inicializa a partir de los datos saneados canónicos.
    Esto garantiza que el sistema siempre arranca con su estado canónico en SQL.
    """
    inicializar_esquema()
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM maestro_materiales;")
    if cur.fetchone()[0] > 0:
        conn.close()
        return False # Ya estaba poblada
        
    print("[Base de Datos] Inicializando tablas relacionales desde datos canónicos...")
    base_dir = get_base_dir()
    clean_dir = os.path.join(base_dir, 'datos_limpios')
    
    # 1. Maestro Materiales
    mm_path = os.path.join(clean_dir, 'maestro_materiales_clean.csv')
    if os.path.exists(mm_path):
        df_mm = pd.read_csv(mm_path)
        for _, r in df_mm.iterrows():
            cur.execute("""
            INSERT OR IGNORE INTO maestro_materiales (sku, descripcion, categoria, unidad, costo_unitario, lead_time_declarado_dias)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (r['sku'], r['descripcion'], r['categoria'], r['unidad'], float(r['costo_unitario']), int(r['lead_time_declarado_dias'])))

    # 2. Maestro Productos
    mp_path = os.path.join(clean_dir, 'maestro_productos_clean.csv')
    if os.path.exists(mp_path):
        df_mp = pd.read_csv(mp_path)
        for _, r in df_mp.iterrows():
            cur.execute("""
            INSERT OR IGNORE INTO maestro_productos (producto, nombre_producto)
            VALUES (?, ?);
            """, (r['producto'], r['nombre_producto']))
            
    # 3. BOM
    bom_path = os.path.join(clean_dir, 'bom_clean.csv')
    if os.path.exists(bom_path):
        df_bom = pd.read_csv(bom_path)
        for _, r in df_bom.iterrows():
            id_bom = f"{r['producto']}_{r['sku_material']}"
            cur.execute("""
            INSERT OR IGNORE INTO bom (id_bom, producto, sku_material, cantidad_por_unidad, unidad)
            VALUES (?, ?, ?, ?, ?);
            """, (id_bom, r['producto'], r['sku_material'], float(r['cantidad_por_unidad']), str(r.get('unidad', ''))))

    # 4. Plan Producción
    pp_path = os.path.join(clean_dir, 'plan_produccion_clean.csv')
    if os.path.exists(pp_path):
        df_pp = pd.read_csv(pp_path)
        for _, r in df_pp.iterrows():
            id_plan = f"{r['periodo']}_{r['producto']}"
            cur.execute("""
            INSERT OR IGNORE INTO plan_produccion (id_plan, periodo, producto, cantidad_planeada, cantidad_real)
            VALUES (?, ?, ?, ?, ?);
            """, (id_plan, str(r['periodo']), r['producto'], float(r['cantidad_planeada']), float(r['cantidad_real'])))

    # 5. Inventario Inicial
    ii_path = os.path.join(clean_dir, 'inventario_inicial_clean.csv')
    if os.path.exists(ii_path):
        df_ii = pd.read_csv(ii_path)
        for _, r in df_ii.iterrows():
            cur.execute("""
            INSERT OR IGNORE INTO inventario_inicial (sku, stock_inicial, fecha_corte)
            VALUES (?, ?, ?);
            """, (r['sku'], float(r['stock_inicial']), r.get('fecha_corte', '2025-01-01')))

    # 6. Conteo Físico
    cf_path = os.path.join(clean_dir, 'conteo_fisico_clean.csv')
    if os.path.exists(cf_path):
        df_cf = pd.read_csv(cf_path)
        for _, r in df_cf.iterrows():
            cur.execute("""
            INSERT OR IGNORE INTO conteo_fisico (sku, stock_fisico_contado, fecha_conteo, auditor)
            VALUES (?, ?, ?, ?);
            """, (r['sku'], float(r['stock_fisico_contado']), r.get('fecha_conteo', '2026-03-31'), r.get('auditor', 'Auditor E2')))

    # 7. Órdenes de Compra
    oc_path = os.path.join(clean_dir, 'ordenes_compra_clean.csv')
    if os.path.exists(oc_path):
        df_oc = pd.read_csv(oc_path)
        for _, r in df_oc.iterrows():
            cur.execute("""
            INSERT OR IGNORE INTO ordenes_compra (orden_compra, sku, proveedor, cantidad, fecha_pedido, fecha_recepcion, costo_unitario, estado, lead_time_dias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                r['orden_compra'], r['sku'], r.get('proveedor'), float(r['cantidad']),
                str(r['fecha_pedido']), str(r['fecha_recepcion']), float(r.get('costo_unitario', 0.0)),
                r.get('estado', 'recibido'), int(r.get('lead_time_dias', 0)) if pd.notna(r.get('lead_time_dias')) else None
            ))

    # 8. Movimientos Inventario
    mov_path = os.path.join(clean_dir, 'movimientos_inventario_clean.csv')
    if os.path.exists(mov_path):
        df_mov = pd.read_csv(mov_path)
        for _, r in df_mov.iterrows():
            doc = str(r.get('documento', ''))
            id_mov = hashlib.sha256(f"{r['fecha']}_{r['sku']}_{r['tipo_movimiento']}_{r['cantidad']}_{doc}".encode()).hexdigest()[:24]
            cur.execute("""
            INSERT OR IGNORE INTO movimientos_inventarios (id_movimiento, fecha, sku, tipo_movimiento, cantidad, documento, bodega, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                id_mov, str(r['fecha']), r['sku'], r['tipo_movimiento'],
                abs(float(r['cantidad'])), doc, str(r.get('bodega', '')), str(r.get('usuario', ''))
            ))

    conn.commit()
    conn.close()
    print("[Base de Datos] Inicialización completada exitosamente.")
    return True

def obtener_conteos_tablas():
    """Retorna un diccionario con el total de filas registradas en cada tabla."""
    conn = get_connection()
    cur = conn.cursor()
    tablas = [
        'maestro_materiales', 'maestro_productos', 'movimientos_inventarios',
        'ordenes_compra', 'conteo_fisico', 'inventario_inicial',
        'plan_produccion', 'bom', 'bitacora_cargas', 'bitacora_corridas',
        'propuestas_reposicion', 'registro_decisiones_compras'
    ]
    conteos = {}
    for t in tablas:
        try:
            cur.execute(f"SELECT count(*) FROM {t};")
            conteos[t] = cur.fetchone()[0]
        except Exception:
            conteos[t] = 0
    conn.close()
    return conteos
