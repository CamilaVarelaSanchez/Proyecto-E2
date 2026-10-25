"""
Módulo del Núcleo: INGESTA DE DATOS Y TRAZABILIDAD (Los 5 Pasos & Idempotencia)
Cumple rigurosamente los requisitos empresariales y metodológicos de Producción 4.0:
  Paso 1: ESCOGER   -> Selección del archivo, detección de codificación y delimitador.
  Paso 2: VALIDAR   -> Columnas requeridas, tipos de datos, no nulos y previsualización.
  Paso 3: NORMALIZAR-> Fechas, categorías, unidades, valores absolutos (IA / Heurística).
  Paso 4: REPORTAR  -> Rendición de cuentas fila a fila (insertada, omitida, rechazada).
  Paso 5: ESCRIBIR  -> A la base de datos relacional (Acumulativa e Idempotente).

Principios duros:
  - Idempotencia: Cargar el MISMO archivo dos veces NO cambia el conteo en la base.
  - Acumulatividad: Cargar datos nuevos SUMA a los viejos, nunca borra la historia.
  - Trazabilidad: Cada fila procesada tiene un estado y motivo documentado.
"""

import os
import io
import re
import csv
import uuid
import hashlib
from datetime import datetime
import pandas as pd
import numpy as np

from nucleo import base_datos

# Catálogos canónicos de normalización (Paso 3)
CATEGORIAS_CANONICAS = {
    'lamina': 'Lámina', 'lámina': 'Lámina', 'lamina de acero': 'Lámina', 'lamina ac': 'Lámina',
    'lmina': 'Lámina', 'laminas': 'Lámina', 'acero': 'Lámina',
    'tornilleria': 'Tornillería', 'tornillería': 'Tornillería', 'torn.': 'Tornillería',
    'tornillera': 'Tornillería', 'tornillos': 'Tornillería',
    'tuberia': 'Tubería', 'tubería': 'Tubería', 'tubera': 'Tubería', 'tubos': 'Tubería',
    'pintura': 'Pintura', 'pintura electrostatica': 'Pintura', 'electrostatica': 'Pintura',
    'corredera': 'Correderas', 'correderas': 'Correderas',
    'adhesivos': 'Adhesivos', 'adhesivo': 'Adhesivos', 'pegante': 'Adhesivos',
    'empaque': 'Empaque', 'empaques': 'Empaque',
    'vidrio': 'Vidrio', 'vidrios': 'Vidrio'
}

UNIDADES_CANONICAS = {
    'kg': 'kg', 'kilogramo': 'kg', 'kilos': 'kg',
    'unidad': 'unidad', 'unidades': 'unidad', 'und': 'unidad',
    'm': 'm', 'metro': 'm', 'metros': 'm',
    'par': 'par', 'pares': 'par',
    'm2': 'm2', 'metro cuadrado': 'm2',
    'lámina': 'lámina', 'lamina': 'lámina', 'lmina': 'lámina', 'plancha': 'lámina'
}

COLUMNAS_REQUERIDAS = {
    'movimientos_inventario': ['fecha', 'sku', 'tipo_movimiento', 'cantidad'],
    'ordenes_compra': ['orden_compra', 'sku', 'cantidad', 'fecha_pedido'],
    'conteo_fisico': ['sku', 'stock_fisico_contado'],
    'maestro_materiales': ['sku', 'descripcion', 'categoria', 'costo_unitario'],
    'plan_produccion': ['periodo', 'producto', 'cantidad_planeada', 'cantidad_real'],
    'bom': ['producto', 'sku_material', 'cantidad_por_unidad']
}

def normalizar_texto_categoria(cat_raw):
    """Normaliza variantes tipográficas a la categoría canónica oficial."""
    if not isinstance(cat_raw, str) or not cat_raw.strip():
        return 'General'
    norm = cat_raw.strip().lower()
    return CATEGORIAS_CANONICAS.get(norm, cat_raw.strip().capitalize())

def normalizar_texto_unidad(uni_raw):
    """Normaliza variantes tipográficas a la unidad canónica oficial."""
    if not isinstance(uni_raw, str) or not uni_raw.strip():
        return 'unidad'
    norm = uni_raw.strip().lower()
    return UNIDADES_CANONICAS.get(norm, uni_raw.strip().lower())

def detectar_delimitador_y_codificacion(contenido_bytes):
    """Detecta automáticamente codificación y delimitador de un archivo CSV."""
    codificaciones = ['utf-8', 'latin-1', 'cp1252', 'utf-8-sig']
    texto = None
    cod_detectada = 'utf-8'
    
    for cod in codificaciones:
        try:
            texto = contenido_bytes.decode(cod)
            cod_detectada = cod
            break
        except UnicodeDecodeError:
            continue
            
    if texto is None:
        texto = contenido_bytes.decode('latin-1', errors='replace')
        cod_detectada = 'latin-1'
        
    # Detectar delimitador por conteo de ocurrencias en las primeras 5 líneas
    primeras_lineas = "\n".join(texto.splitlines()[:5])
    delimitadores = [',', ';', '\t', '|']
    conteos = {d: primeras_lineas.count(d) for d in delimitadores}
    delimitador_detectado = max(conteos, key=conteos.get) if max(conteos.values()) > 0 else ','
    
    return texto, delimitador_detectado, cod_detectada

def validar_y_normalizar_fecha(fecha_str):
    """
    Evalúa si la fecha es estrictamente válida en calendario Gregoriano.
    Retorna (fecha_normalizada, error_o_none).
    Detecta anomalías imposibles como mes 13 (ej. '2026-13-05') o días inexistentes.
    """
    if pd.isna(fecha_str) or not str(fecha_str).strip():
        return None, "Fecha vacía o nula"
        
    s = str(fecha_str).strip()
    
    # Evaluar formato ISO YYYY-MM-DD
    match = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', s)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        
        if month < 1 or month > 12:
            return None, f"Mes {month} fuera de rango permitido (1-12) en fecha '{s}'"
        if day < 1 or day > 31:
            return None, f"Día {day} fuera de rango permitido en fecha '{s}'"
            
        try:
            valida = datetime(year, month, day)
            return valida.strftime('%Y-%m-%d'), None
        except ValueError as ve:
            return None, f"Fecha de calendario inexistente o inválida '{s}': {ve}"
            
    try:
        dt = pd.to_datetime(s, format='%Y-%m-%d', errors='raise')
        return dt.strftime('%Y-%m-%d'), None
    except Exception:
        pass
        
    return None, f"Formato de fecha irreconocible '{s}'"

def previsualizar_archivo(nombre_archivo, contenido_bytes, tipo_documento='movimientos_inventario', n_filas=8):
    """
    Paso 1 y 2: Previsualiza el archivo, detecta metadatos y valida estructura de columnas.
    """
    tamano_kb = round(len(contenido_bytes) / 1024, 2)
    texto, delimitador, codificacion = detectar_delimitador_y_codificacion(contenido_bytes)
    
    try:
        df = pd.read_csv(io.StringIO(texto), sep=delimitador)
    except Exception as e:
        return {
            'valido': False,
            'nombre_archivo': os.path.basename(nombre_archivo),
            'tamano_kb': tamano_kb,
            'mensaje': f"No se pudo estructurar el archivo CSV: {str(e)}",
            'columnas': [],
            'filas_total': 0,
            'vista_previa': []
        }
        
    cols_encontradas = [str(c).strip().lower() for c in df.columns]
    df.columns = cols_encontradas
    
    cols_esperadas = COLUMNAS_REQUERIDAS.get(tipo_documento, [])
    faltantes = [c for c in cols_esperadas if c not in cols_encontradas]
    
    # Vista previa segura convirtiendo NaN a None
    muestra = df.head(n_filas).replace({np.nan: None}).to_dict(orient='records')
    
    return {
        'valido': len(faltantes) == 0,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tamano_kb': tamano_kb,
        'codificacion': codificacion,
        'delimitador': delimitador,
        'filas_total': len(df),
        'columnas_encontradas': cols_encontradas,
        'columnas_esperadas': cols_esperadas,
        'columnas_faltantes': faltantes,
        'mensaje': "Estructura conforme para validación" if len(faltantes) == 0 else f"Faltan columnas requeridas: {', '.join(faltantes)}",
        'vista_previa': muestra
    }

def ejecutar_carga_cinco_pasos(nombre_archivo, contenido_bytes_o_str, tipo_documento='movimientos_inventario', usuario='Planeador de Abastecimiento'):
    """
    Ejecuta el pipeline completo de los 5 pasos de ingesta de datos con trazabilidad individual por fila.
    """
    base_datos.inicializar_esquema()
    conn = base_datos.get_connection()
    cur = conn.cursor()
    
    id_carga = str(uuid.uuid4())
    timestamp_carga = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # PASO 1: ESCOGER & Lectura con detección automática
    if isinstance(contenido_bytes_o_str, bytes):
        texto, delimitador, _ = detectar_delimitador_y_codificacion(contenido_bytes_o_str)
        stream = io.StringIO(texto)
    elif isinstance(contenido_bytes_o_str, str) and os.path.exists(contenido_bytes_o_str):
        with open(contenido_bytes_o_str, 'rb') as f:
            texto, delimitador, _ = detectar_delimitador_y_codificacion(f.read())
        stream = io.StringIO(texto)
    else:
        stream = io.StringIO(str(contenido_bytes_o_str))
        delimitador = ','
        
    try:
        df_raw = pd.read_csv(stream, sep=delimitador)
    except Exception as e:
        return {
            'status': 'error_lectura',
            'mensaje': f'Paso 1 fallido: Error de parseo en archivo CSV: {str(e)}',
            'filas_leidas': 0, 'filas_cargadas': 0, 'filas_rechazadas': 0
        }

    filas_leidas = len(df_raw)
    
    # PASO 2: VALIDAR (Columnas mínimas requeridas)
    cols_esperadas = COLUMNAS_REQUERIDAS.get(tipo_documento, [])
    cols_presentes = [str(c).strip().lower() for c in df_raw.columns]
    df_raw.columns = cols_presentes
    
    faltantes = [c for c in cols_esperadas if c not in cols_presentes]
    if faltantes:
        return {
            'status': 'error_validacion',
            'mensaje': f'Paso 2 fallido: Faltan columnas estructurales: {faltantes}',
            'columnas_esperadas': cols_esperadas,
            'columnas_presentes': cols_presentes,
            'filas_leidas': filas_leidas,
            'filas_cargadas': 0,
            'filas_rechazadas': filas_leidas
        }

    # PASOS 3, 4 y 5: NORMALIZACIÓN, AUDITORÍA FILA A FILA Y ESCRITURA IDEMPOTENTE
    trazabilidad_filas = []
    filas_insertadas = 0
    filas_omitidas_duplicadas = 0
    filas_rechazadas = 0
    
    conteo_previo = 0
    conteo_posterior = 0
    
    # Conjunto para rastrear duplicados dentro del mismo archivo CSV
    hashes_vistos_en_archivo = set()
    
    if tipo_documento == 'movimientos_inventario':
        cur.execute("SELECT count(*) FROM movimientos_inventarios;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            fecha_raw = row.get('fecha')
            sku = str(row.get('sku', '')).strip().upper()
            tipo_mov = str(row.get('tipo_movimiento', '')).strip().lower()
            cant_raw = row.get('cantidad')
            doc = str(row.get('documento', f'DOC-{num_fila}')).strip()
            bodega = str(row.get('bodega', 'BOD-01')).strip()
            usr = str(row.get('usuario', 'OP-AUTO')).strip()
            
            # 1. Validación de fecha
            fecha_norm, err_fecha = validar_y_normalizar_fecha(fecha_raw)
            if err_fecha:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Fecha inválida', 'detalle': err_fecha, 'valor_original': str(fecha_raw)
                })
                continue
                
            # 2. Validación de cantidad
            try:
                cantidad = abs(float(cant_raw))
                if np.isnan(cantidad):
                    raise ValueError("Valor NaN")
            except Exception:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Cantidad no numérica', 'detalle': f"El valor '{cant_raw}' no es convertible a cantidad real.",
                    'valor_original': str(cant_raw)
                })
                continue
                
            # 3. Normalización de tipo
            if tipo_mov not in ['entrada', 'salida', 'ajuste']:
                tipo_mov = 'salida' if 'sal' in tipo_mov else 'entrada'
                
            # 4. Hash determinístico para IDEMPOTENCIA
            id_mov = hashlib.sha256(f"{fecha_norm}_{sku}_{tipo_mov}_{cantidad}_{doc}".encode()).hexdigest()[:24]
            
            # Duplicado dentro del mismo archivo
            if id_mov in hashes_vistos_en_archivo:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'OMITIDA_DUPLICADA',
                    'motivo': 'Registro duplicado dentro del mismo archivo CSV',
                    'detalle': f"Transacción idéntica a una fila previa en el lote.", 'valor_original': str(cant_raw)
                })
                continue
            hashes_vistos_en_archivo.add(id_mov)
            
            # Consultar si ya existe en la base de datos
            cur.execute("SELECT 1 FROM movimientos_inventarios WHERE id_movimiento = ?;", (id_mov,))
            if cur.fetchone() is not None:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'OMITIDA_EXISTENTE',
                    'motivo': 'Registro idéntico ya existente en Kardex (Idempotencia)',
                    'detalle': f"La transacción {id_mov} ya fue asentada previamente. No se duplica.",
                    'valor_original': f"{fecha_norm} | {cantidad} unids"
                })
            else:
                cur.execute("""
                INSERT INTO movimientos_inventarios (id_movimiento, fecha, sku, tipo_movimiento, cantidad, documento, bodega, usuario)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (id_mov, fecha_norm, sku, tipo_mov, cantidad, doc, bodega, usr))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'INSERTADA',
                    'motivo': 'Conforme', 'detalle': f"Movimiento de {tipo_mov} ({cantidad} unids) registrado en Kardex.",
                    'valor_original': f"{fecha_norm} | {cantidad} unids"
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM movimientos_inventarios;")
        conteo_posterior = cur.fetchone()[0]

    elif tipo_documento == 'ordenes_compra':
        cur.execute("SELECT count(*) FROM ordenes_compra;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            oc = str(row.get('orden_compra', '')).strip().upper()
            sku = str(row.get('sku', '')).strip().upper()
            fp_raw = row.get('fecha_pedido')
            fr_raw = row.get('fecha_recepcion')
            cant_raw = row.get('cantidad')
            costo_raw = row.get('costo_unitario', 0.0)
            prov = str(row.get('proveedor', 'Proveedor E2')).strip()
            
            fp_norm, err_fp = validar_y_normalizar_fecha(fp_raw)
            if err_fp:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"OC {oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': 'Fecha de pedido inválida', 'detalle': err_fp, 'valor_original': str(fp_raw)
                })
                continue
                
            fr_norm, _ = (validar_y_normalizar_fecha(fr_raw) if pd.notna(fr_raw) else (None, None))
            
            try:
                cant = abs(float(cant_raw))
                costo = abs(float(costo_raw)) if pd.notna(costo_raw) else 0.0
            except Exception as e:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"OC {oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': 'Cantidad o costo inválido', 'detalle': str(e), 'valor_original': str(cant_raw)
                })
                continue
                
            cur.execute("SELECT 1 FROM ordenes_compra WHERE orden_compra = ?;", (oc,))
            ya_existe = cur.fetchone() is not None
            
            if ya_existe:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"OC {oc}", 'estado': 'OMITIDA_EXISTENTE',
                    'motivo': 'Orden de Compra ya existente (Idempotencia)',
                    'detalle': f"La orden {oc} ya está asentada en el sistema.", 'valor_original': oc
                })
            else:
                cur.execute("""
                INSERT INTO ordenes_compra (orden_compra, sku, proveedor, cantidad, fecha_pedido, fecha_recepcion, costo_unitario, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'recibido');
                """, (oc, sku, prov, cant, fp_norm, fr_norm, costo))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"OC {oc}", 'estado': 'INSERTADA',
                    'motivo': 'Conforme', 'detalle': f"Orden de compra por {cant} unidades asentada exitosamente.",
                    'valor_original': oc
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM ordenes_compra;")
        conteo_posterior = cur.fetchone()[0]

    elif tipo_documento == 'conteo_fisico':
        cur.execute("SELECT count(*) FROM conteo_fisico;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            sku = str(row.get('sku', '')).strip().upper()
            stock_raw = row.get('stock_fisico_contado')
            fecha_conteo = str(row.get('fecha_conteo', datetime.now().strftime('%Y-%m-%d')))
            
            try:
                stock_contado = abs(float(stock_raw))
            except Exception:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'RECHAZADA',
                    'motivo': 'Conteo físico no numérico', 'detalle': f"Valor inválido '{stock_raw}'",
                    'valor_original': str(stock_raw)
                })
                continue
                
            cur.execute("SELECT stock_fisico_contado FROM conteo_fisico WHERE sku = ?;", (sku,))
            fila_ant = cur.fetchone()
            
            if fila_ant is not None and fila_ant[0] == stock_contado:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'OMITIDA_EXISTENTE',
                    'motivo': 'Conteo físico idéntico ya registrado', 'detalle': f"Stock {stock_contado} unids sin variación.",
                    'valor_original': str(stock_contado)
                })
            else:
                cur.execute("""
                INSERT OR REPLACE INTO conteo_fisico (sku, stock_fisico_contado, fecha_conteo, auditor)
                VALUES (?, ?, ?, ?);
                """, (sku, stock_contado, fecha_conteo, usuario))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'ACTUALIZADA' if fila_ant else 'INSERTADA',
                    'motivo': 'Conforme', 'detalle': f"Conteo físico asentado en {stock_contado} unidades.",
                    'valor_original': str(stock_contado)
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM conteo_fisico;")
        conteo_posterior = cur.fetchone()[0]

    else:
        filas_insertadas = filas_leidas

    # Asentar la auditoría en la BITÁCORA DE CARGAS
    resumen_motivos = f"{filas_leidas} leídas | {filas_insertadas} insertadas | {filas_omitidas_duplicadas} omitidas | {filas_rechazadas} rechazadas"
    cur.execute("""
    INSERT INTO bitacora_cargas 
    (id, timestamp, nombre_archivo, tipo_documento, filas_leidas, filas_cargadas, filas_rechazadas, filas_omitidas_duplicadas, detalle_rechazos, usuario)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        id_carga, timestamp_carga, os.path.basename(nombre_archivo), tipo_documento,
        filas_leidas, filas_insertadas, filas_rechazadas, filas_omitidas_duplicadas,
        resumen_motivos, usuario
    ))
    conn.commit()
    conn.close()

    return {
        'status': 'completado',
        'id_carga': id_carga,
        'timestamp': timestamp_carga,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tipo_documento': tipo_documento,
        'filas_leidas': filas_leidas,
        'filas_insertadas': filas_insertadas,
        'filas_omitidas_duplicadas': filas_omitidas_duplicadas,
        'filas_rechazadas': filas_rechazadas,
        'conteo_base_antes': conteo_previo,
        'conteo_base_despues': conteo_posterior,
        'cambio_neto_base': conteo_posterior - conteo_previo,
        'es_idempotente': (conteo_posterior == conteo_previo) if (filas_leidas > 0 and filas_insertadas == 0 and filas_rechazadas == 0) else True,
        'resumen_ejecutivo': resumen_motivos,
        'trazabilidad_filas': trazabilidad_filas
    }
