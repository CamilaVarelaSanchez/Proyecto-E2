"""
Módulo del Núcleo: INGESTA DE DATOS Y TRAZABILIDAD (Los 5 Pasos & Idempotencia)
Cumple rigurosamente los requisitos empresariales y metodológicos de Producción 4.0:
  Paso 1: ESCOGER   -> Selección del archivo, detección de codificación, delimitador y cálculo de hashes (SHA256/MD5).
  Paso 2: VALIDAR   -> Columnas requeridas, tipos de datos, no nulos, integridad referencial y previsualización.
  Paso 3: NORMALIZAR-> Fechas gregorianas, categorías canónicas, unidades, valores numéricos absolutos.
  Paso 4: REPORTAR  -> Rendición de cuentas cuantitativa fila a fila (insertada, actualizada, omitida, rechazada).
  Paso 5: ESCRIBIR  -> A la base de datos relacional y Supabase (Acumulativa, Idempotente con UPSERT / ON CONFLICT).

Principios duros:
  - Idempotencia: Cargar el MISMO archivo o presionar el botón múltiples veces NO altera los saldos ni duplica registros (net change = 0).
  - Integridad Referencial (3FN): Materiales no existentes en el maestro son rechazados con causal técnica explícita.
  - Trazabilidad Absoluta: Cada fila procesada reporta estado, motivo y valor original.
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
from nucleo.ingesta_supabase import (
    TIPOS_DOCUMENTO_ADICIONALES,
    columnas_esperadas as columnas_esperadas_supabase,
    ejecutar_ingesta as ejecutar_ingesta_supabase,
    faltan_columnas as faltan_columnas_supabase
)

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
}

TIPOS_DOCUMENTO_SOPORTADOS = frozenset(COLUMNAS_REQUERIDAS) | TIPOS_DOCUMENTO_ADICIONALES

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

def _parsear_numero(valor, campo, entero=False):
    if pd.isna(valor) or not str(valor).strip():
        raise ValueError(f'{campo} debe tener un valor numérico.')
    try:
        numero = float(str(valor).strip().replace(',', '.'))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{valor}' no tiene un formato numérico válido para {campo}.") from exc
    if not np.isfinite(numero):
        raise ValueError(f'{campo} debe ser un número finito.')
    if entero and not numero.is_integer():
        raise ValueError(f'{campo} debe ser un número entero.')
    return int(numero) if entero else numero

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
    Evalúa si la fecha es estrictamente válida en calendario Gregoriano dentro del horizonte operacional (2000-2050).
    Retorna (fecha_normalizada, error_o_none).
    Detecta anomalías imposibles como mes 13 (ej. '2026-13-05'), días inexistentes (ej. '2026-02-30') o años fuera de rango.
    """
    if pd.isna(fecha_str) or not str(fecha_str).strip():
        return None, "Fecha vacía o nula"
        
    s = str(fecha_str).strip()
    
    # 1. Formato ISO YYYY-MM-DD o YYYY/MM/DD
    match_iso = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', s)
    if match_iso:
        year = int(match_iso.group(1))
        month = int(match_iso.group(2))
        day = int(match_iso.group(3))
        
        if year < 2000 or year > 2050:
            return None, f"Año {year} fuera del horizonte operacional permitido (2000-2050) en fecha '{s}'"
        if month < 1 or month > 12:
            return None, f"Mes {month} fuera de rango permitido (1-12) en fecha '{s}'"
        if day < 1 or day > 31:
            return None, f"Día {day} fuera de rango permitido en fecha '{s}'"
            
        try:
            valida = datetime(year, month, day)
            return valida.strftime('%Y-%m-%d'), None
        except ValueError as ve:
            return None, f"Fecha de calendario inexistente o inválida '{s}': {ve}"

    # 2. Formato latino DD-MM-YYYY o DD/MM/YYYY
    match_dmy = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', s)
    if match_dmy:
        day = int(match_dmy.group(1))
        month = int(match_dmy.group(2))
        year = int(match_dmy.group(3))
        
        if year < 2000 or year > 2050:
            return None, f"Año {year} fuera del horizonte operacional permitido (2000-2050) en fecha '{s}'"
        if month < 1 or month > 12:
            return None, f"Mes {month} fuera de rango permitido (1-12) en fecha '{s}'"
        if day < 1 or day > 31:
            return None, f"Día {day} fuera de rango permitido en fecha '{s}'"
            
        try:
            valida = datetime(year, month, day)
            return valida.strftime('%Y-%m-%d'), None
        except ValueError as ve:
            return None, f"Fecha de calendario inexistente o inválida '{s}': {ve}"
            
    # 3. Fallback general controlado
    try:
        dt = pd.to_datetime(s, errors='raise')
        if dt.year < 2000 or dt.year > 2050:
            return None, f"Año {dt.year} fuera del horizonte operacional permitido (2000-2050) en fecha '{s}'"
        return dt.strftime('%Y-%m-%d'), None
    except Exception:
        pass
        
    return None, f"Formato de fecha no válido ('{s}'). Se requiere formato YYYY-MM-DD"

def previsualizar_archivo(nombre_archivo, contenido_bytes, tipo_documento='movimientos_inventario', n_filas=8):
    """
    Paso 1 y 2: Previsualiza el archivo, calcula hashes criptográficos y valida estructura de columnas de forma defensiva.
    """
    if not isinstance(contenido_bytes, (bytes, bytearray)):
        contenido_bytes = str(contenido_bytes or '').encode('utf-8')

    tamano_kb = round(len(contenido_bytes) / 1024, 2)
    hash_sha256 = hashlib.sha256(contenido_bytes).hexdigest()
    hash_md5 = hashlib.md5(contenido_bytes).hexdigest()
    if tipo_documento not in TIPOS_DOCUMENTO_SOPORTADOS:
        return {
            'valido': False,
            'nombre_archivo': os.path.basename(nombre_archivo),
            'tamano_kb': tamano_kb,
            'hash_archivo_sha256': hash_sha256,
            'hash_archivo_md5': hash_md5,
            'codificacion': None,
            'delimitador': None,
            'filas_total': 0,
            'columnas_encontradas': [],
            'columnas_esperadas': [],
            'columnas_faltantes': [],
            'mensaje': f'Tipo de documento no soportado: {tipo_documento}'
        }
    cols_esperadas = (
        columnas_esperadas_supabase(tipo_documento)
        if tipo_documento in TIPOS_DOCUMENTO_ADICIONALES
        else COLUMNAS_REQUERIDAS.get(tipo_documento, [])
    )

    # Manejo defensivo: Archivo vacío (0 bytes o solo espacios)
    if not contenido_bytes.strip():
        return {
            'valido': False,
            'nombre_archivo': os.path.basename(nombre_archivo),
            'tamano_kb': 0.0,
            'hash_archivo_sha256': hash_sha256,
            'hash_archivo_md5': hash_md5,
            'codificacion': 'utf-8',
            'delimitador': ',',
            'filas_total': 0,
            'columnas_encontradas': [],
            'columnas_esperadas': cols_esperadas,
            'columnas_faltantes': cols_esperadas,
            'mensaje': "El archivo está vacío (0 bytes). Seleccione un archivo CSV con registros tabulares.",
            'vista_previa': []
        }
    
    texto, delimitador, codificacion = detectar_delimitador_y_codificacion(contenido_bytes)
    
    try:
        df = pd.read_csv(io.StringIO(texto), sep=delimitador, on_bad_lines='skip')
        if df.empty and len(texto.strip()) > 0:
            raise ValueError("El archivo no contiene filas con datos estructurados.")
    except Exception as e:
        return {
            'valido': False,
            'nombre_archivo': os.path.basename(nombre_archivo),
            'tamano_kb': tamano_kb,
            'hash_archivo_sha256': hash_sha256,
            'hash_archivo_md5': hash_md5,
            'codificacion': codificacion,
            'delimitador': delimitador,
            'mensaje': f"No se pudo estructurar el archivo CSV (archivo corrupto o líneas malformadas): {str(e)}",
            'columnas_encontradas': [],
            'columnas_esperadas': cols_esperadas,
            'columnas_faltantes': cols_esperadas,
            'filas_total': 0,
            'vista_previa': []
        }
        
    cols_encontradas = [str(c).strip().lower().replace('"', '').replace("'", '') for c in df.columns]
    df.columns = cols_encontradas
    
    if tipo_documento in TIPOS_DOCUMENTO_ADICIONALES:
        faltantes = faltan_columnas_supabase(tipo_documento, cols_encontradas)
    else:
        faltantes = [c for c in cols_esperadas if c not in cols_encontradas]
    
    # Vista previa segura convirtiendo NaN a None
    muestra = df.head(n_filas).replace({np.nan: None}).to_dict(orient='records')
    
    return {
        'valido': len(faltantes) == 0,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tamano_kb': tamano_kb,
        'hash_archivo_sha256': hash_sha256,
        'hash_archivo_md5': hash_md5,
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
    Ejecuta el pipeline completo de los 5 pasos de ingesta de datos con:
      1. Cálculo de Hashes (SHA256 / MD5) para idempotencia global.
      2. Validación estructural y relacional (3FN) estricta.
      3. Claves determinísticas por fila y sentencias UPSERT (ON CONFLICT).
      4. Sincronización idempotente con Supabase.
      5. Tarjeta de auditoría cuantitativa de 5 puntos.
    """
    if tipo_documento not in TIPOS_DOCUMENTO_SOPORTADOS:
        return {
            'status': 'error_validacion',
            'mensaje': f'Tipo de documento no soportado: {tipo_documento}',
            'nombre_archivo': os.path.basename(nombre_archivo),
            'tipo_documento': tipo_documento,
            'estado_carga': 'Rechazado',
            'filas_leidas': 0,
            'filas_insertadas': 0,
            'filas_actualizadas': 0,
            'filas_insertadas_o_actualizadas': 0,
            'filas_cargadas': 0,
            'filas_omitidas_duplicadas': 0,
            'filas_rechazadas': 0,
            'sincronizacion_supabase': {'status': 'skipped', 'msg': 'El tipo de documento no está soportado'},
            'resumen_ejecutivo': f'Tipo de documento no soportado: {tipo_documento}',
            'trazabilidad_filas': []
        }

    base_datos.inicializar_esquema()
    conn = base_datos.get_connection()
    cur = conn.cursor()
    
    id_carga = str(uuid.uuid4())
    timestamp_carga = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Hashes criptográficos del archivo para idempotencia global
    if isinstance(contenido_bytes_o_str, bytes):
        raw_bytes = contenido_bytes_o_str
        texto, delimitador, _ = detectar_delimitador_y_codificacion(raw_bytes)
        stream = io.StringIO(texto)
    elif isinstance(contenido_bytes_o_str, str) and os.path.exists(contenido_bytes_o_str):
        with open(contenido_bytes_o_str, 'rb') as f:
            raw_bytes = f.read()
        texto, delimitador, _ = detectar_delimitador_y_codificacion(raw_bytes)
        stream = io.StringIO(texto)
    else:
        raw_bytes = str(contenido_bytes_o_str or '').encode('utf-8')
        texto, delimitador, _ = detectar_delimitador_y_codificacion(raw_bytes)
        stream = io.StringIO(texto)
        
    hash_archivo_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    hash_archivo_md5 = hashlib.md5(raw_bytes).hexdigest()

    # Manejo defensivo: Archivo vacío
    if not raw_bytes.strip():
        conn.close()
        return {
            'status': 'error_lectura',
            'mensaje': 'Paso 1 fallido: El archivo cargado está vacío (0 bytes o sin registros).',
            'hash_archivo_sha256': hash_archivo_sha256,
            'hash_archivo_md5': hash_archivo_md5,
            'filas_leidas': 0, 'filas_cargadas': 0, 'filas_rechazadas': 0,
            'filas_insertadas': 0, 'filas_actualizadas': 0, 'filas_insertadas_o_actualizadas': 0,
            'filas_omitidas_duplicadas': 0,
            'total_registros_procesados': 0, 'estado_carga': 'Rechazado',
            'trazabilidad_filas': [],
            'resumen_ejecutivo': 'El archivo cargado está vacío. No se realizaron cambios en la base de datos.'
        }
        
    try:
        df_raw = pd.read_csv(stream, sep=delimitador, on_bad_lines='skip')
        if df_raw.empty and len(raw_bytes.strip()) > 0:
            raise ValueError("No se encontraron registros tabulares válidos en el archivo.")
    except Exception as e:
        conn.close()
        return {
            'status': 'error_lectura',
            'mensaje': f'Paso 1 fallido: Error de interpretación en archivo CSV ({str(e)})',
            'hash_archivo_sha256': hash_archivo_sha256,
            'hash_archivo_md5': hash_archivo_md5,
            'filas_leidas': 0, 'filas_cargadas': 0, 'filas_rechazadas': 0,
            'filas_insertadas': 0, 'filas_actualizadas': 0, 'filas_insertadas_o_actualizadas': 0,
            'filas_omitidas_duplicadas': 0,
            'total_registros_procesados': 0, 'estado_carga': 'Rechazado',
            'trazabilidad_filas': [],
            'resumen_ejecutivo': f'Archivo corrupto o malformado: {str(e)}'
        }

    filas_leidas = len(df_raw)
    
    # PASO 2: VALIDAR (Columnas mínimas requeridas, insensibles al orden y espacios)
    cols_esperadas = COLUMNAS_REQUERIDAS.get(tipo_documento, [])
    cols_presentes = [str(c).strip().lower().replace('"', '').replace("'", '') for c in df_raw.columns]
    df_raw.columns = cols_presentes

    if tipo_documento in TIPOS_DOCUMENTO_ADICIONALES:
        conn.close()
        return ejecutar_ingesta_supabase(
            nombre_archivo, raw_bytes, df_raw, tipo_documento, usuario
        )

    faltantes = [c for c in cols_esperadas if c not in cols_presentes]
    if faltantes:
        conn.close()
        return {
            'status': 'error_validacion',
            'mensaje': f'Paso 2 fallido: Faltan columnas estructurales: {faltantes}',
            'hash_archivo_sha256': hash_archivo_sha256,
            'hash_archivo_md5': hash_archivo_md5,
            'columnas_esperadas': cols_esperadas,
            'columnas_presentes': cols_presentes,
            'filas_leidas': filas_leidas,
            'total_registros_procesados': filas_leidas,
            'filas_insertadas': 0,
            'filas_actualizadas': 0,
            'filas_insertadas_o_actualizadas': 0,
            'filas_cargadas': 0,
            'filas_omitidas_duplicadas': 0,
            'filas_rechazadas': filas_leidas,
            'estado_carga': 'Rechazado',
            'resumen_ejecutivo': f"Estructura no conforme: faltan columnas requeridas {faltantes}.",
            'trazabilidad_filas': [{
                'fila': i + 1, 'identificador': f"Fila {i + 1}", 'estado': 'RECHAZADA',
                'motivo': 'Columnas estructurales faltantes', 'detalle': f"El archivo carece de {faltantes}",
                'valor_original': 'Encabezado CSV inválido'
            } for i in range(min(filas_leidas, 10))]
        }

    # PASOS 3, 4 y 5: NORMALIZACIÓN, AUDITORÍA FILA A FILA Y ESCRITURA IDEMPOTENTE
    trazabilidad_filas = []
    filas_insertadas = 0
    filas_actualizadas = 0
    filas_omitidas_duplicadas = 0
    filas_rechazadas = 0
    registros_supabase = []
    
    conteo_previo = 0
    conteo_posterior = 0
    
    # Conjunto para rastrear duplicados dentro del mismo archivo CSV
    hashes_vistos_en_archivo = set()
    
    # -------------------------------------------------------------
    # TABLA: movimientos_inventarios
    # -------------------------------------------------------------
    if tipo_documento == 'movimientos_inventario':
        cur.execute("SELECT count(*) FROM movimientos_inventarios;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            fecha_raw = row.get('fecha')
            sku = str(row.get('sku', '')).strip().upper() if pd.notna(row.get('sku')) else ''
            tipo_mov = str(row.get('tipo_movimiento', '')).strip().lower()
            cant_raw = row.get('cantidad')
            doc_raw = row.get('documento')
            doc = str(doc_raw).strip() if pd.notna(doc_raw) and str(doc_raw).strip() else f'DOC-{num_fila}'
            bodega = str(row.get('bodega', 'BOD-01')).strip()
            responsable_raw = row.get('responsable', row.get('usuario', 'OP-AUTO'))
            usr = str(responsable_raw).strip() if pd.notna(responsable_raw) else 'OP-AUTO'
            
            # Validación de SKU obligatorio
            if not sku:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"Fila {num_fila} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Campo obligatorio nulo (SKU)', 'detalle': "El código SKU es obligatorio en movimientos de inventario.",
                    'valor_original': ''
                })
                continue
                
            # Integridad referencial (3FN): SKU debe existir en maestro_materiales
            cur.execute("SELECT 1 FROM maestro_materiales WHERE sku = ?;", (sku,))
            if cur.fetchone() is None:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Inconsistencia referencial (SKU huérfano)',
                    'detalle': f"El SKU '{sku}' no existe en el catálogo maestro de materiales.",
                    'valor_original': sku
                })
                continue
            
            # Validación de fecha de movimiento
            fecha_norm, err_fecha = validar_y_normalizar_fecha(fecha_raw)
            if err_fecha:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Fecha inválida', 'detalle': err_fecha, 'valor_original': str(fecha_raw)
                })
                continue
                
            # Validación de cantidad numérica
            try:
                cantidad = abs(_parsear_numero(cant_raw, 'cantidad'))
            except (TypeError, ValueError, OverflowError) as exc:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'RECHAZADA',
                    'motivo': 'Cantidad no numérica', 'detalle': str(exc),
                    'valor_original': str(cant_raw)
                })
                continue
                
            # Normalización de tipo
            if tipo_mov not in ['entrada', 'salida', 'ajuste']:
                tipo_mov = 'salida' if 'sal' in tipo_mov else 'entrada'
                
            # Clave natural determinística (Hash SHA256) para Idempotencia
            id_mov = hashlib.sha256(f"{fecha_norm}_{sku}_{tipo_mov}_{cantidad}_{doc}".encode('utf-8')).hexdigest()[:24]
            
            # Idempotencia intra-archivo
            if id_mov in hashes_vistos_en_archivo:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'OMITIDA_DUPLICADA',
                    'motivo': 'Registro duplicado dentro del mismo archivo CSV',
                    'detalle': "Transacción idéntica a una fila previa en el lote CSV.", 'valor_original': str(cant_raw)
                })
                continue
            hashes_vistos_en_archivo.add(id_mov)
            registros_supabase.append({
                'fecha': fecha_norm,
                'sku': sku,
                'tipo_movimiento': tipo_mov,
                'cantidad': cantidad,
                'documento': doc,
                'bodega': bodega,
                'responsable': usr
            })
            
            # Idempotencia en base de datos: ON CONFLICT (id_movimiento) DO NOTHING
            cur.execute("SELECT 1 FROM movimientos_inventarios WHERE id_movimiento = ?;", (id_mov,))
            if cur.fetchone() is not None:
                filas_omitidas_duplicadas += 1
                cant_mov_disp = int(cantidad) if float(cantidad).is_integer() else cantidad
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'OMITIDA_EXISTENTE',
                    'motivo': 'Registro idéntico ya existente en Kardex (Idempotencia)',
                    'detalle': f"La transacción {id_mov} ya fue asentada previamente. No se duplica ni altera saldos.",
                    'valor_original': f"{fecha_norm} | {cant_mov_disp} unidades"
                })
            else:
                cur.execute("""
                INSERT INTO movimientos_inventarios (id_movimiento, fecha, sku, tipo_movimiento, cantidad, documento, bodega, usuario)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (id_mov, fecha_norm, sku, tipo_mov, cantidad, doc, bodega, usr))
                filas_insertadas += 1
                cant_mov_disp = int(cantidad) if float(cantidad).is_integer() else cantidad
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{sku} / {doc}", 'estado': 'INSERTADA',
                    'motivo': 'Conforme', 'detalle': f"Movimiento de {tipo_mov} ({cant_mov_disp} unidades) registrado en Kardex.",
                    'valor_original': f"{fecha_norm} | {cant_mov_disp} unidades"
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM movimientos_inventarios;")
        conteo_posterior = cur.fetchone()[0]

    # -------------------------------------------------------------
    # TABLA: ordenes_compra
    # -------------------------------------------------------------
    elif tipo_documento == 'ordenes_compra':
        cur.execute("SELECT count(*) FROM ordenes_compra;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            oc = str(row.get('orden_compra', '')).strip().upper() if pd.notna(row.get('orden_compra')) else ''
            sku = str(row.get('sku', '')).strip().upper() if pd.notna(row.get('sku')) else ''
            fp_raw = row.get('fecha_pedido')
            fr_raw = row.get('fecha_recepcion')
            cant_raw = row.get('cantidad')
            costo_raw = row.get('costo_unitario', 0.0)
            prov = str(row.get('proveedor', 'Proveedor E2')).strip()
            
            # Formatear identificador limpio sin duplicación de prefijos (ej. OC-9035 en lugar de OC OC-9035)
            if oc.startswith("OC-"):
                id_oc = oc
            elif oc.startswith("OC "):
                id_oc = oc.replace("OC ", "OC-")
            elif oc.startswith("OC"):
                id_oc = f"OC-{oc[2:].lstrip('- ')}"
            else:
                id_oc = f"OC-{oc}"

            if not oc:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"Fila {num_fila}", 'estado': 'RECHAZADA',
                    'motivo': 'Campo obligatorio nulo (Número de Orden)', 'detalle': "El número de orden de compra es obligatorio.",
                    'valor_original': ''
                })
                continue

            if not sku:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': id_oc, 'estado': 'RECHAZADA',
                    'motivo': 'Campo obligatorio nulo (SKU)', 'detalle': "El código SKU es obligatorio en la orden de compra.",
                    'valor_original': ''
                })
                continue

            # Integridad referencial: SKU debe existir en maestro_materiales
            cur.execute("SELECT 1 FROM maestro_materiales WHERE sku = ?;", (sku,))
            if cur.fetchone() is None:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{id_oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': 'Inconsistencia referencial (SKU huérfano)',
                    'detalle': f"El SKU '{sku}' no existe en el catálogo maestro de materiales.",
                    'valor_original': sku
                })
                continue
                
            fp_norm, err_fp = validar_y_normalizar_fecha(fp_raw)
            if err_fp:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{id_oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': 'Fecha de pedido inválida', 'detalle': err_fp, 'valor_original': str(fp_raw)
                })
                continue

            fecha_promesa_raw = row.get('fecha_promesa')
            fecha_promesa_norm, err_fecha_promesa = (
                validar_y_normalizar_fecha(fecha_promesa_raw)
                if pd.notna(fecha_promesa_raw) and str(fecha_promesa_raw).strip()
                else (None, None)
            )
            if err_fecha_promesa:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{id_oc} / {sku}",
                    'estado': 'RECHAZADA', 'motivo': 'Fecha promesa inválida',
                    'detalle': err_fecha_promesa, 'valor_original': str(fecha_promesa_raw)
                })
                continue
                
            fr_norm, err_fr = (validar_y_normalizar_fecha(fr_raw) if pd.notna(fr_raw) and str(fr_raw).strip() else (None, None))
            if err_fr:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{id_oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': 'Fecha de recepción inválida', 'detalle': err_fr, 'valor_original': str(fr_raw)
                })
                continue
            
            try:
                cant = abs(_parsear_numero(cant_raw, 'cantidad', entero=True))
                costo = abs(_parsear_numero(costo_raw, 'costo_unitario', entero=True)) if pd.notna(costo_raw) else 0
            except (TypeError, ValueError, OverflowError) as e:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"{id_oc} / {sku}", 'estado': 'RECHAZADA',
                    'motivo': (
                        'Cantidad inválida: no se permiten valores decimales en órdenes de compra'
                        if 'debe ser un número entero' in str(e)
                        else 'Cantidad o costo inválido'
                    ),
                    'detalle': str(e),
                    'valor_original': f'Cantidad: {cant_raw}, costo_unitario: {costo_raw}'
                })
                continue
                
            # Idempotencia intra-archivo
            if oc in hashes_vistos_en_archivo:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': id_oc, 'estado': 'OMITIDA_DUPLICADA',
                    'motivo': 'Orden de compra duplicada en el mismo lote CSV',
                    'detalle': f"La orden {id_oc} se repite en este archivo.", 'valor_original': oc
                })
                continue
            hashes_vistos_en_archivo.add(oc)
            registros_supabase.append({
                'orden_compra': oc,
                'fecha_pedido': fp_norm,
                'sku': sku,
                'cantidad': cant,
                'proveedor': prov,
                'fecha_promesa': fecha_promesa_norm,
                'fecha_recepcion': fr_norm,
                'costo_unitario': costo
            })

            cur.execute("""
            SELECT sku, proveedor, cantidad, fecha_pedido, fecha_recepcion, costo_unitario
            FROM ordenes_compra
            WHERE orden_compra = ?;
            """, (oc,))
            fila_ant = cur.fetchone()
            
            cant_display = int(cant) if float(cant).is_integer() else cant

            if fila_ant is not None:
                if (
                    fila_ant[0] == sku
                    and fila_ant[1] == prov
                    and fila_ant[2] == cant
                    and fila_ant[3] == fp_norm
                    and fila_ant[4] == fr_norm
                    and fila_ant[5] == costo
                ):
                    filas_omitidas_duplicadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': id_oc, 'estado': 'OMITIDA_EXISTENTE',
                        'motivo': 'Orden de compra idéntica ya existente (Idempotencia)',
                        'detalle': f"La orden {id_oc} ya está asentada sin cambios.", 'valor_original': oc
                    })
                else:
                    # UPSERT: ON CONFLICT (orden_compra) DO UPDATE
                    cur.execute("""
                    UPDATE ordenes_compra
                    SET sku = ?, proveedor = ?, cantidad = ?, fecha_pedido = ?, fecha_recepcion = ?, costo_unitario = ?
                    WHERE orden_compra = ?;
                    """, (sku, prov, cant, fp_norm, fr_norm, costo, oc))
                    filas_actualizadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': id_oc, 'estado': 'ACTUALIZADA',
                        'motivo': 'Orden de compra actualizada (UPSERT)',
                        'detalle': f"La orden {id_oc} fue actualizada con nueva cantidad/costo ({cant_display} unidades).", 'valor_original': oc
                    })
            else:
                cur.execute("""
                INSERT INTO ordenes_compra (orden_compra, sku, proveedor, cantidad, fecha_pedido, fecha_recepcion, costo_unitario, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'recibido');
                """, (oc, sku, prov, cant, fp_norm, fr_norm, costo))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': id_oc, 'estado': 'INSERTADA',
                    'motivo': 'Conforme', 'detalle': f"Orden de compra por {cant_display} unidades asentada exitosamente.",
                    'valor_original': oc
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM ordenes_compra;")
        conteo_posterior = cur.fetchone()[0]

    # -------------------------------------------------------------
    # TABLA: conteo_fisico
    # -------------------------------------------------------------
    elif tipo_documento == 'conteo_fisico':
        cur.execute("SELECT count(*) FROM conteo_fisico;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            sku = str(row.get('sku', '')).strip().upper() if pd.notna(row.get('sku')) else ''
            stock_raw = row.get('stock_fisico_contado')
            fecha_conteo = str(row.get('fecha_conteo', datetime.now().strftime('%Y-%m-%d'))).strip()
            
            # Validación SKU obligatorio
            if not sku:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"Fila {num_fila}", 'estado': 'RECHAZADA',
                    'motivo': 'Campo obligatorio nulo (SKU)', 'detalle': "El código SKU es obligatorio y no puede estar vacío.",
                    'valor_original': ''
                })
                continue
                
            # Validación integridad referencial (3FN): SKU debe existir en maestro_materiales
            cur.execute("SELECT 1 FROM maestro_materiales WHERE sku = ?;", (sku,))
            if cur.fetchone() is None:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'RECHAZADA',
                    'motivo': 'Inconsistencia referencial (SKU huérfano)',
                    'detalle': f"El SKU '{sku}' no existe en el catálogo maestro de materiales.",
                    'valor_original': sku
                })
                continue
                
            # Validación numérica de conteo
            try:
                stock_contado = abs(_parsear_numero(stock_raw, 'conteo físico'))
            except (TypeError, ValueError, OverflowError) as exc:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'RECHAZADA',
                    'motivo': 'Conteo físico no numérico o inválido', 'detalle': str(exc),
                    'valor_original': str(stock_raw)
                })
                continue
                
            # Validación de fecha de conteo
            fecha_norm, err_fecha = validar_y_normalizar_fecha(fecha_conteo)
            if err_fecha:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'RECHAZADA',
                    'motivo': 'Fecha de conteo inválida', 'detalle': err_fecha,
                    'valor_original': str(fecha_conteo)
                })
                continue

            # Idempotencia intra-archivo
            if sku in hashes_vistos_en_archivo:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'OMITIDA_DUPLICADA',
                    'motivo': 'Registro duplicado dentro del mismo archivo CSV',
                    'detalle': f"El SKU '{sku}' ya fue especificado en una fila previa de este archivo.",
                    'valor_original': str(stock_contado)
                })
                continue
            hashes_vistos_en_archivo.add(sku)
            registros_supabase.append({
                'sku': sku,
                'stock_fisico_contado': stock_contado,
                'fecha_conteo': fecha_norm
            })
                
            cur.execute("""
            SELECT stock_fisico_contado, fecha_conteo
            FROM conteo_fisico
            WHERE sku = ?;
            """, (sku,))
            fila_ant = cur.fetchone()
            
            if fila_ant is not None:
                if fila_ant[0] == stock_contado and fila_ant[1] == fecha_norm:
                    filas_omitidas_duplicadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': sku, 'estado': 'OMITIDA_EXISTENTE',
                        'motivo': 'Conteo físico idéntico ya registrado (Idempotencia)',
                        'detalle': f"Stock {int(stock_contado) if stock_contado.is_integer() else stock_contado} unidades sin variación respecto a la base.",
                        'valor_original': str(int(stock_contado) if stock_contado.is_integer() else stock_contado)
                    })
                else:
                    # UPSERT: ON CONFLICT(sku) DO UPDATE
                    cur.execute("""
                    UPDATE conteo_fisico 
                    SET stock_fisico_contado = ?, fecha_conteo = ?, auditor = ?
                    WHERE sku = ?;
                    """, (stock_contado, fecha_norm, usuario, sku))
                    filas_actualizadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': sku, 'estado': 'ACTUALIZADA',
                        'motivo': 'Conteo físico actualizado (UPSERT)',
                        'detalle': f"Stock físico actualizado de {int(fila_ant[0]) if float(fila_ant[0]).is_integer() else fila_ant[0]} a {int(stock_contado) if stock_contado.is_integer() else stock_contado} unidades.",
                        'valor_original': str(int(stock_contado) if stock_contado.is_integer() else stock_contado)
                    })
            else:
                # INSERT nuevo
                cur.execute("""
                INSERT INTO conteo_fisico (sku, stock_fisico_contado, fecha_conteo, auditor)
                VALUES (?, ?, ?, ?);
                """, (sku, stock_contado, fecha_norm, usuario))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'INSERTADA',
                    'motivo': 'Conforme',
                    'detalle': f"Conteo físico asentado en {int(stock_contado) if stock_contado.is_integer() else stock_contado} unidades.",
                    'valor_original': str(int(stock_contado) if stock_contado.is_integer() else stock_contado)
                })

        conn.commit()
        cur.execute("SELECT count(*) FROM conteo_fisico;")
        conteo_posterior = cur.fetchone()[0]

    # -------------------------------------------------------------
    # TABLA: maestro_materiales
    # -------------------------------------------------------------
    elif tipo_documento == 'maestro_materiales':
        cur.execute("SELECT count(*) FROM maestro_materiales;")
        conteo_previo = cur.fetchone()[0]
        
        for idx, row in df_raw.iterrows():
            num_fila = idx + 1
            sku = str(row.get('sku', '')).strip().upper() if pd.notna(row.get('sku')) else ''
            desc = str(row.get('descripcion', '')).strip()
            cat_raw = row.get('categoria', 'General')
            cat = normalizar_texto_categoria(cat_raw)
            uni_raw = row.get('unidad', 'unidad')
            uni = normalizar_texto_unidad(uni_raw)
            costo_raw = row.get('costo_unitario', 0.0)
            lt_raw = row.get('lead_time_declarado_dias', 7)
            
            if not sku:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': f"Fila {num_fila}", 'estado': 'RECHAZADA',
                    'motivo': 'Campo obligatorio nulo (SKU)', 'detalle': "El código SKU es obligatorio y no puede estar vacío.",
                    'valor_original': ''
                })
                continue
                
            try:
                costo = abs(_parsear_numero(costo_raw, 'costo'))
                lt = abs(_parsear_numero(lt_raw, 'lead time', entero=True)) if pd.notna(lt_raw) else 7
            except Exception as e:
                filas_rechazadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'RECHAZADA',
                    'motivo': 'Costo o Lead Time inválido', 'detalle': str(e),
                    'valor_original': f"Costo: {costo_raw}, LT: {lt_raw}"
                })
                continue
                
            # Idempotencia intra-archivo
            if sku in hashes_vistos_en_archivo:
                filas_omitidas_duplicadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'OMITIDA_DUPLICADA',
                    'motivo': 'Material duplicado en el mismo lote CSV',
                    'detalle': f"El SKU {sku} se repite en este lote.", 'valor_original': sku
                })
                continue
            registro_material = {
                'sku': sku,
                'descripcion': desc,
                'categoria': cat,
                'unidad': uni,
                'costo_unitario': costo,
                'lead_time_declarado_dias': lt
            }
            for campo in ('proveedor', 'stock_min', 'stock_max'):
                if campo in df_raw.columns:
                    valor = row.get(campo)
                    if pd.notna(valor):
                        if campo in ('stock_min', 'stock_max'):
                            try:
                                valor = _parsear_numero(valor, campo, entero=True)
                            except (TypeError, ValueError) as e:
                                filas_rechazadas += 1
                                trazabilidad_filas.append({
                                    'fila': num_fila, 'identificador': sku,
                                    'estado': 'RECHAZADA',
                                    'motivo': f'{campo} inválido',
                                    'detalle': str(e), 'valor_original': str(row.get(campo))
                                })
                                registro_material = None
                                break
                        else:
                            valor = str(valor).strip()
                    else:
                        valor = None
                    registro_material[campo] = valor
            if registro_material is None:
                continue
            hashes_vistos_en_archivo.add(sku)
            registros_supabase.append(registro_material)

            cur.execute("""
            SELECT costo_unitario, descripcion, categoria, unidad, lead_time_declarado_dias
            FROM maestro_materiales
            WHERE sku = ?;
            """, (sku,))
            fila_ant = cur.fetchone()
            
            if fila_ant is not None:
                if (
                    fila_ant[0] == costo
                    and fila_ant[1] == desc
                    and fila_ant[2] == cat
                    and fila_ant[3] == uni
                    and fila_ant[4] == lt
                ):
                    filas_omitidas_duplicadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': sku, 'estado': 'OMITIDA_EXISTENTE',
                        'motivo': 'Registro idéntico ya existente en Maestro (Idempotencia)',
                        'detalle': f"Material {sku} sin cambios en costo ni atributos.",
                        'valor_original': f"${costo:,.2f}"
                    })
                else:
                    cur.execute("""
                    UPDATE maestro_materiales 
                    SET descripcion = ?, categoria = ?, unidad = ?, costo_unitario = ?, lead_time_declarado_dias = ?
                    WHERE sku = ?;
                    """, (desc, cat, uni, costo, lt, sku))
                    filas_actualizadas += 1
                    trazabilidad_filas.append({
                        'fila': num_fila, 'identificador': sku, 'estado': 'ACTUALIZADA',
                        'motivo': 'Actualización de atributos (UPSERT)',
                        'detalle': f"Material actualizado: costo ${costo:,.2f}, categoría {cat}.",
                        'valor_original': f"${costo:,.2f}"
                    })
            else:
                cur.execute("""
                INSERT INTO maestro_materiales (sku, descripcion, categoria, unidad, costo_unitario, lead_time_declarado_dias)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (sku, desc, cat, uni, costo, lt))
                filas_insertadas += 1
                trazabilidad_filas.append({
                    'fila': num_fila, 'identificador': sku, 'estado': 'INSERTADA',
                    'motivo': 'Conforme',
                    'detalle': f"Nuevo material {sku} insertado en catálogo maestro.",
                    'valor_original': f"${costo:,.2f}"
                })
        conn.commit()
        cur.execute("SELECT count(*) FROM maestro_materiales;")
        conteo_posterior = cur.fetchone()[0]

    else:
        filas_insertadas = filas_leidas

    # Sincronización idempotente con Supabase (UPSERT)
    sincronizacion_sb = {'status': 'skipped', 'msg': 'Sin filas válidas para sincronizar', 'filas_sincronizadas': 0}
    if registros_supabase:
        try:
            from nucleo.datos import supabase_upsert
            tabla_sb_map = {
                'movimientos_inventario': ('movimientos_inventario', 'documento'),
                'ordenes_compra': ('ordenes_compra', 'orden_compra'),
                'conteo_fisico': ('conteo_fisico', 'sku'),
                'maestro_materiales': ('maestro_materiales', 'sku')
            }
            if tipo_documento in tabla_sb_map:
                tabla_sb, clave_conflicto = tabla_sb_map[tipo_documento]
                sincronizacion_sb = supabase_upsert(
                    table_name=tabla_sb,
                    payload=registros_supabase,
                    on_conflict_col=clave_conflicto,
                    do_update=True
                )
            else:
                sincronizacion_sb = {
                    'status': 'error',
                    'msg': f'No hay sincronización Supabase configurada para {tipo_documento}',
                    'filas_sincronizadas': 0,
                    'filas_pendientes': len(registros_supabase)
                }
        except Exception as e_sb:
            sincronizacion_sb = {
                'status': 'error',
                'msg': str(e_sb),
                'filas_sincronizadas': 0,
                'filas_pendientes': len(registros_supabase)
            }

    # Categorización cuantitativa del Estado de la Carga (Requisito 3.1)
    filas_modificadas = filas_insertadas + filas_actualizadas
    if filas_rechazadas == 0:
        estado_carga = 'Exitoso'
    elif filas_modificadas > 0 or filas_omitidas_duplicadas > 0:
        estado_carga = 'Parcial'
    else:
        estado_carga = 'Rechazado'

    # Construcción de resumen ejecutivo para la alta dirección / auditoría
    primer_rechazo = next((f for f in trazabilidad_filas if f['estado'] == 'RECHAZADA'), None)
    if primer_rechazo and (filas_modificadas + filas_omitidas_duplicadas) > 0:
        resumen_ejecutivo = f"No fue posible procesar la fila {primer_rechazo['fila']} debido a un {primer_rechazo['motivo'].lower()}. El resto de los datos se procesó correctamente."
    elif filas_rechazadas > 0 and (filas_modificadas + filas_omitidas_duplicadas) == 0:
        resumen_ejecutivo = f"Se rechazaron {filas_rechazadas} fila(s) del lote debido a inconsistencias estructurales o de formato."
    else:
        resumen_ejecutivo = f"{filas_leidas} registros procesados con éxito ({filas_modificadas} modificados, {filas_omitidas_duplicadas} omitidos por idempotencia)."

    if sincronizacion_sb.get('status') == 'error':
        resumen_ejecutivo += f" No se sincronizó completamente con Supabase: {sincronizacion_sb.get('msg', 'error desconocido')}."
        if filas_rechazadas == 0:
            estado_carga = 'Parcial'

    cur.execute("""
    INSERT INTO bitacora_cargas 
    (id, timestamp, nombre_archivo, tipo_documento, filas_leidas, filas_cargadas, filas_rechazadas, filas_omitidas_duplicadas, detalle_rechazos, usuario, hash_archivo_sha256)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        id_carga, timestamp_carga, os.path.basename(nombre_archivo), tipo_documento,
        filas_leidas, filas_modificadas, filas_rechazadas, filas_omitidas_duplicadas,
        resumen_ejecutivo, usuario, hash_archivo_sha256
    ))
    conn.commit()
    conn.close()

    return {
        'status': 'completado',
        'id_carga': id_carga,
        'timestamp': timestamp_carga,
        'nombre_archivo': os.path.basename(nombre_archivo),
        'tipo_documento': tipo_documento,
        'hash_archivo_sha256': hash_archivo_sha256,
        'hash_archivo_md5': hash_archivo_md5,
        'estado_carga': estado_carga,
        'total_registros_procesados': filas_leidas,
        'filas_leidas': filas_leidas,
        'filas_insertadas': filas_insertadas,
        'filas_actualizadas': filas_actualizadas,
        'filas_insertadas_o_actualizadas': filas_modificadas,
        'filas_cargadas': filas_modificadas,
        'filas_omitidas_duplicadas': filas_omitidas_duplicadas,
        'filas_rechazadas': filas_rechazadas,
        'conteo_base_antes': conteo_previo,
        'conteo_base_despues': conteo_posterior,
        'cambio_neto_base': conteo_posterior - conteo_previo,
        'es_idempotente': (conteo_posterior == conteo_previo) if (filas_leidas > 0 and filas_modificadas == 0 and filas_rechazadas == 0) else True,
        'sincronizacion_supabase': sincronizacion_sb,
        'resumen_ejecutivo': resumen_ejecutivo,
        'trazabilidad_filas': trazabilidad_filas
    }
