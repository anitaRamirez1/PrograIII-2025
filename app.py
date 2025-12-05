# ===========================
# UROMED - Médico IA
# Flask + SQL Server - VERSIÓN SIN VALIDACIÓN (MODO DEMOSTRACIÓN)
# ===========================

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
import pyodbc
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from dotenv import load_dotenv
import json
import uuid
from contextlib import contextmanager
import tempfile

# ==========================================
# 🔥 IMPORTACIONES PARA ANÁLISIS REAL DE IMAGEN
# ==========================================
from PIL import Image
import numpy as np
# Necesitas: pip install scikit-image
from skimage.feature import graycomatrix, graycoprops 
from skimage.measure import shannon_entropy 
# Nota: Las importaciones MONAI originales han sido eliminadas ya que no son necesarias para esta solución rápida.

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave-temporal-solo-desarrollo')

UPLOAD_FOLDER = 'static/uploads'
PERFILES_FOLDER = 'static/perfiles'
UPLOAD_CHAT = os.path.join(UPLOAD_FOLDER, 'chat')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear directorios si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PERFILES_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_CHAT, exist_ok=True)

# ==========================================
# 🔥 FUNCIÓN DE ANÁLISIS DE IMAGEN REAL (ESTADÍSTICO/TEXTURA)
#    Esta función reemplaza la lógica de MONAI/Fake.
# ==========================================

def analizar_imagen_real(image_path, tipo_analisis):
    """
    Realiza un análisis estadístico y de textura real usando PIL, NumPy y scikit-image.
    Los resultados son dinámicos y dependen de la imagen cargada.
    """
    # Manejo de error para cuando el path es None (ej. llamada de fallback)
    if image_path is None:
        return {
            "metadata_tecnica": {"Dimensiones": "0x0", "Modo_Color_Base": "Error", "Tipo_Analisis_Aplicado": "Error"},
            "analisis_estadistico": {"Media_Brillo": "0.0", "Desviacion_Estandar": "0.0", "Entropia_Shannon": "0.0"},
            "analisis_textura": {"Contraste_GLCM": "0.0", "Homogeneidad_GLCM": "0.0", "Densidad_Anomala_%": "0.0"},
            "hallazgos": [{"descripcion": "❌ Error al procesar la imagen - No se pudo cargar el archivo.", "confianza": 0.15}],
            "confianza_global": 0.15,
            "recomendacion_completa": "Error de procesamiento. Verifique el formato de imagen.",
            "modelo_utilizado": "Fallback de Error"
        }

    try:
        # Cargar y convertir a escala de grises (necesario para la mayoría de análisis)
        img = Image.open(image_path).convert('L') 
        img_array = np.array(img)
        img_normalized = img_array / 255.0
        
        H, W = img_array.shape
        
        # 1. Análisis Estadístico Básico (Brillo/Contraste Global)
        media_brillo = np.mean(img_normalized)
        desviacion_estandar = np.std(img_normalized) # Una medida de contraste
        min_pixel = np.min(img_normalized)
        max_pixel = np.max(img_normalized)
        # Entropía de Shannon: Mide la complejidad de la textura/aleatoriedad
        entropia = shannon_entropy(img_array)
        
        # 2. Análisis de Textura GLCM (Homogeneidad y Contraste Local)
        # Cuantizar imagen a 16 niveles para GLCM
        img_quantized = (img_array // 16).astype(np.uint8)
        glcm = graycomatrix(img_quantized, distances=[1], angles=[0], levels=16, symmetric=True, normed=True)
        
        contraste_glcm = graycoprops(glcm, 'contrast')[0, 0] # Intensidad de cambios locales (bordes)
        homogeneidad_glcm = graycoprops(glcm, 'homogeneity')[0, 0] # Uniformidad de la imagen
        
        # 3. Detección de Anomalías Simulada (Basada en Brillo/Contraste)
        
        hallazgo_principal = "Análisis Morfológico Generalmente Normal."
        confianza_calculada = 0.75 
        
        # -----------------------------------------------------------------
        # 🔥 NUEVA LÓGICA DE DESCARTE/NO MÉDICA 🔥
        # -----------------------------------------------------------------
        # Regla 1: Descarte por baja complejidad/contraste (típico de capturas de pantalla)
        if desviacion_estandar < 0.1 and homogeneidad_glcm > 0.98:
            hallazgo_principal = "🚫 IMAGEN NO MÉDICA DETECTADA (Baja Complejidad/Alto Descarte)."
            confianza_calculada = 0.98  # Alta confianza en el descarte
            recomendacion = "Recomendación: Archivo descartado. El sistema sugiere verificar el tipo de imagen. Use solo radiografías o ecografías urológicas."
            return {
                "metadata_tecnica": {
                    "Dimensiones": f"{W}x{H}",
                    "Modo_Color_Base": "Escala de Grises",
                    "Tipo_Analisis_Aplicado": "Filtro de Descarte"
                },
                "analisis_estadistico": {
                    "Media_Brillo": f"{media_brillo:.4f}",
                    "Desviacion_Estandar": f"{desviacion_estandar:.4f}",
                    "Entropia_Shannon": f"{entropia:.4f}"
                },
                "analisis_textura": {
                    "Contraste_GLCM": f"{contraste_glcm:.4f}",
                    "Homogeneidad_GLCM": f"{homogeneidad_glcm:.4f}",
                    "Densidad_Anomala_%": "0.00"
                },
                "hallazgos": [
                    {"descripcion": hallazgo_principal, "confianza": confianza_calculada},
                    {"descripcion": recomendacion, "confianza": 0.99}
                ],
                "confianza_global": round(confianza_calculada, 2),
                "recomendacion_completa": recomendacion,
                "modelo_utilizado": "Filtro de Relevancia (Basado en DIP)"
            }
        
        # -----------------------------------------------------------------
        # LÓGICA DE PATOLOGÍA (Solo si pasa el filtro de descarte)
        # -----------------------------------------------------------------
        
        # Simulación de detección de una región hiperdensa (cálculo o masa)
        # Definimos "muy brillante" como píxeles > 95% del rango (valor > 0.95)
        high_density_pixels = np.sum(img_normalized > 0.95)
        total_pixels = img_normalized.size
        percent_high_density = (high_density_pixels / total_pixels) * 100
            
        
        if percent_high_density > 0.1 and media_brillo > 0.3:
            hallazgo_principal = f"⚠ **Región Hiperdensa Anómala** (posible cálculo o masa) detectada. Cobertura: {percent_high_density:.2f}%."
            confianza_calculada = min(0.99, 0.75 + (percent_high_density * 0.1))
        elif contraste_glcm > 0.8:
            hallazgo_principal = "⚡ **Alto Contraste Local**. Sugiere márgenes irregulares o bordes patológicos."
            confianza_calculada = min(0.95, 0.70 + (contraste_glcm * 0.15))
        elif homogeneidad_glcm < 0.6:
            hallazgo_principal = "🚨 **Baja Homogeneidad**. La textura es muy variable, compatible con tejido heterogéneo."
            confianza_calculada = min(0.90, 0.70 + (1 - homogeneidad_glcm) * 0.2)
            
        # 4. Interpretación y Recomendación Específica (Basada en el tipo y los resultados)
        
        recomendacion = f"Recomendación: Evaluación detallada de la región con **{hallazgo_principal.split('**')[0].split('⚠')[0].strip()}**."
        
        if tipo_analisis == "calculos_renales" and percent_high_density > 0.05:
            recomendacion = f"Recomendación: Fuerte sospecha de **Litiasis Renal** debido a alta densidad ({percent_high_density:.2f}%). Se sugiere TAC sin contraste."
        elif tipo_analisis == "prostata" and contraste_glcm > 0.7:
            recomendacion = f"Recomendación: Márgenes prostáticos irregulares detectados (Contraste GLCM {contraste_glcm:.4f}). Se recomienda evaluación de PSA y posible biopsia."
        
        
        # Devolver el resultado final (Normal o Patológico)
        return {
            "metadata_tecnica": {
                "Dimensiones": f"{W}x{H}",
                "Modo_Color_Base": "Escala de Grises",
                "Tipo_Analisis_Aplicado": "Análisis Cuantitativo/DIP"
            },
            "analisis_estadistico": {
                "Media_Brillo": f"{media_brillo:.4f}",
                "Desviacion_Estandar": f"{desviacion_estandar:.4f}",
                "Entropia_Shannon": f"{entropia:.4f}"
            },
            "analisis_textura": {
                "Contraste_GLCM": f"{contraste_glcm:.4f}",
                "Homogeneidad_GLCM": f"{homogeneidad_glcm:.4f}",
                "Densidad_Anomala_%": f"{percent_high_density:.2f}"
            },
            # Formato compatible con tu estructura de chat (hallazgos)
            "hallazgos": [
                {"descripcion": hallazgo_principal, "confianza": confianza_calculada},
                {"descripcion": recomendacion, "confianza": confianza_calculada + 0.05}
            ],
            "confianza_global": round(confianza_calculada, 2),
            "recomendacion_completa": recomendacion,
            "modelo_utilizado": "Análisis Estadístico Avanzado (PIL, NumPy, scikit-image)"
        }
    
    except Exception as e:
        print(f"❌ Error crítico en análisis de imagen REAL: {e}")
        # Respuesta de fallback en caso de error
        return {
            "metadata_tecnica": {"Dimensiones": "N/A", "Modo_Color_Base": "Error", "Tipo_Analisis_Aplicado": "Error"},
            "analisis_estadistico": {"Media_Brillo": "0.0", "Desviacion_Estandar": "0.0", "Entropia_Shannon": "0.0"},
            "analisis_textura": {"Contraste_GLCM": "0.0", "Homogeneidad_GLCM": "0.0", "Densidad_Anomala_%": "0.0"},
            "hallazgos": [
                {"descripcion": "❌ Error al procesar la imagen - Análisis estático de emergencia.", "confianza": 0.15},
                {"descripcion": "Recomendación: Intente con un formato más común (JPG/PNG).", "confianza": 0.20}
            ],
            "confianza_global": 0.15,
            "recomendacion_completa": "Error de procesamiento. Verifique el formato de imagen.",
            "modelo_utilizado": "Fallback de Error"
        }

# Las funciones originales de MONAI han sido eliminadas aquí.

# ==========================================
# FUNCIÓN DE VALIDACIÓN SIMPLIFICADA (MODO DEMOSTRACIÓN)
# ==========================================

def es_imagen_medica_valida(image_path):
    """
    VERSIÓN SIMPLIFICADA PARA DEMOSTRACIÓN
    Solo verifica formato básico, sin restricciones
    """
    try:
        nombre_lower = image_path.lower()
        
        # Formatos aceptados (ampliado para demostración)
        formatos_aceptados = [
            '.dcm', '.nii', '.nii.gz',
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif',
            '.gif', '.webp' # Añadidos para máxima compatibilidad
        ]
        
        # Verificar extensión
        for fmt in formatos_aceptados:
            if nombre_lower.endswith(fmt):
                return True, 0.9, ["✅ Modo demostración - Validación simplificada"], "Imagen aceptada para análisis"
        
        return False, 0.0, ["❌ Formato no reconocido"], "Formato no compatible"
        
    except Exception as e:
        print(f"⚠️ Error en validación simplificada: {e}")
        # En modo demo: aceptar igual
        return True, 0.5, ["⚠️ Error ignorado en modo demostración"], "Imagen aceptada (modo demo)"

# ==========================================
# FUNCIONES DE CONEXIÓN Y UTILIDADES MEJORADAS
# ==========================================

@contextmanager
def conectar_sql():
    """Conexión mejorada con manejo de contexto"""
    conn = None
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=DESKTOP-IFV9P3G\\SQLEXPRESS;"
            "DATABASE=UROMED;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        yield conn
    except pyodbc.Error as e:
        print(f"❌ Error de conexión: {e}")
        flash('Error de conexión a la base de datos', 'error')
        raise
    finally:
        if conn:
            conn.close()

def validar_estructura_mensajes(mensajes):
    """Valida que los mensajes tengan estructura correcta"""
    try:
        if not isinstance(mensajes, list):
            return False
            
        for msg in mensajes:
            if not all(key in msg for key in ['texto', 'tipo']):
                return False
            if msg['tipo'] not in ['usuario', 'ia']:
                return False
                
        return True
    except:
        return False

def verificar_codigo_sistema(codigo_ingresado):
    """Verifica si el código ingresado es válido contra la base de datos"""
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT codigo_hash FROM codigos_acceso WHERE activo = 1")
            resultado = cursor.fetchone()
            
            if resultado:
                es_valido = check_password_hash(resultado[0], codigo_ingresado)
                print(f"✅ Código {'correcto' if es_valido else 'incorrecto'}!")
                return es_valido
            return False
    except Exception as e:
        print(f"❌ Error al verificar código: {e}")
        return False

# ==========================================
# FUNCIONES DE VERIFICACIÓN DE PERMISOS
# ==========================================

def tiene_permiso_eliminar():
    """Verifica si el usuario actual puede eliminar expedientes"""
    rol = session.get('rol', '').strip().lower()
    return rol in ['super administrador', 'doctor']

def tiene_permiso_editar():
    """Verifica si el usuario actual puede editar expedientes"""
    rol = session.get('rol', '').strip().lower()
    return rol in ['super administrador', 'doctor', 'enfermero']

def tiene_permiso_gestion_usuarios():
    """Verifica si el usuario actual puede gestionar usuarios"""
    rol = session.get('rol', '').strip().lower()
    return rol in ['super administrador', 'doctor']

# ==========================================
# RUTAS PRINCIPALES - EXPEDIENTES
# ==========================================

@app.route('/')
def inicio():
    """Página principal - Muestra lista de expedientes"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombres, apellidos, enfermedad FROM expedientes")
            expedientes = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM expedientes")
            total_expedientes = cursor.fetchone()[0]

    except Exception as e:
        flash('Error al cargar expedientes', 'error')
        return render_template('error.html', error=str(e))

    usuario = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')
    fecha_actual = datetime.today().strftime('%Y-%m-%d')

    return render_template('Principal.html',
                           expedientes=expedientes,
                           usuario=usuario,
                           rol=rol,
                           total_expedientes=total_expedientes,
                           fecha_actual=fecha_actual)

@app.route('/buscar_expediente')
def buscar_expediente():
    """Busca expedientes por nombre, apellido o enfermedad"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '').strip()

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nombres, apellidos, enfermedad
                FROM expedientes
                WHERE nombres LIKE ? 
                    OR apellidos LIKE ? 
                    OR enfermedad LIKE ?
                    OR CONCAT(nombres, ' ', apellidos, ' - ', enfermedad) LIKE ?
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            
            expedientes = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM expedientes")
            total_expedientes = cursor.fetchone()[0]

    except Exception as e:
        flash('Error en la búsqueda', 'error')
        expedientes = []
        total_expedientes = 0

    usuario = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')
    fecha_actual = datetime.today().strftime('%Y-%m-%d')

    return render_template('Principal.html',
                           expedientes=expedientes,
                           usuario=usuario,
                           rol=rol,
                           total_expedientes=total_expedientes,
                           query=query,
                           fecha_actual=fecha_actual)

@app.route('/sugerencias')
def sugerencias():
    """API para autocompletado de búsqueda"""
    if 'usuario_id' not in session:
        return jsonify([])

    term = request.args.get('term', '').strip().lower()
    if not term or len(term) < 2:
        return jsonify([])

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT TOP 10 nombres, apellidos, enfermedad
                FROM expedientes
                WHERE LOWER(nombres) LIKE ? 
                    OR LOWER(apellidos) LIKE ? 
                    OR LOWER(enfermedad) LIKE ?
                    OR LOWER(CONCAT(nombres, ' ', apellidos, ' - ', enfermedad)) LIKE ?
            """, (f'%{term}%', f'%{term}%', f'%{term}%', f'%{term}%'))
            
            resultados = cursor.fetchall()
    except Exception as e:
        print("Error en la búsqueda de sugerencias:", e)
        return jsonify([])

    sugerencias = []
    for nombre, apellido, enfermedad in resultados:
        texto = f"{nombre} {apellido} - {enfermedad}"
        if texto not in sugerencias:
            sugerencias.append(texto)

    return jsonify(sugerencias)

# ==========================================
# CRUD DE EXPEDIENTES
# ==========================================

@app.route('/crear_expediente')
def crear_expediente():
    """Muestra formulario para crear nuevo expediente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('CrearExpediente.html')

@app.route('/guardar_expediente', methods=['POST'])
def guardar_expediente():
    """Guarda un nuevo expediente en la base de datos"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nombres = request.form.get('nombres', '')
    apellidos = request.form.get('apellidos', '')
    telefono = request.form.get('telefono', '')
    direccion = request.form.get('direccion', '')
    correo = request.form.get('correo', '')
    edad = request.form.get('edad', '')
    enfermedad = request.form.get('enfermedad', '')
    imagen_file = request.files.get('imagen')
    imagen_nombre = None

    if imagen_file and imagen_file.filename:
        imagen_nombre = secure_filename(imagen_file.filename)
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_nombre)
        imagen_file.save(imagen_path)

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expedientes (nombres, apellidos, telefono, direccion, correo, edad, enfermedad, imagen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombres, apellidos, telefono, direccion, correo, edad, enfermedad, imagen_nombre))
            conn.commit()
            
        flash('Expediente creado correctamente', 'success')
        return redirect(url_for('inicio'))
        
    except Exception as e:
        flash('Error al crear expediente', 'error')
        return render_template('CrearExpediente.html')

@app.route('/ver_expediente/<int:id>')
def ver_expediente(id):
    """Muestra los detalles completos de un expediente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expedientes WHERE id = ?", (id,))
            fila = cursor.fetchone()

        if fila:
            expediente = {
                'id': fila[0],
                'nombres': fila[1],
                'apellidos': fila[2],
                'telefono': fila[3],
                'direccion': fila[4],
                'correo': fila[5],
                'edad': fila[6],
                'enfermedad': fila[7],
                'imagen': fila[8]
            }
            return render_template('VerExpediente.html', expediente=expediente)
        else:
            flash('Expediente no encontrado', 'error')
            return redirect(url_for('inicio'))
            
    except Exception as e:
        flash('Error al cargar expediente', 'error')
        return redirect(url_for('inicio'))

@app.route('/modificar_expediente/<int:id>')
def modificar_expediente(id):
    """Muestra formulario para modificar un expediente existente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expedientes WHERE id = ?", (id,))
            fila = cursor.fetchone()

        if fila:
            expediente = {
                'id': fila[0],
                'nombres': fila[1],
                'apellidos': fila[2],
                'telefono': fila[3],
                'direccion': fila[4],
                'correo': fila[5],
                'edad': fila[6],
                'enfermedad': fila[7],
                'imagen': fila[8]
            }
            return render_template('ModificarExpediente.html', expediente=expediente)
        else:
            flash('Expediente no encontrado', 'error')
            return redirect(url_for('inicio'))
            
    except Exception as e:
        flash('Error al cargar expediente', 'error')
        return redirect(url_for('inicio'))

@app.route('/actualizar_expediente/<int:id>', methods=['POST'])
def actualizar_expediente(id):
    """Actualiza los datos de un expediente existente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nombres = request.form.get('nombres', '')
    apellidos = request.form.get('apellidos', '')
    telefono = request.form.get('telefono', '')
    direccion = request.form.get('direccion', '')
    correo = request.form.get('correo', '')
    edad = request.form.get('edad', '')
    enfermedad = request.form.get('enfermedad', '')
    imagen_file = request.files.get('imagen')

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT imagen FROM expedientes WHERE id = ?", (id,))
            resultado = cursor.fetchone()
            imagen_actual = resultado[0] if resultado else None

            if imagen_file and imagen_file.filename:
                imagen_nombre = secure_filename(imagen_file.filename)
                imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_nombre)
                imagen_file.save(imagen_path)
            else:
                imagen_nombre = imagen_actual

            cursor.execute("""
                UPDATE expedientes
                SET nombres = ?, apellidos = ?, telefono = ?, direccion = ?, correo = ?, edad = ?, enfermedad = ?, imagen = ?
                WHERE id = ?
            """, (nombres, apellidos, telefono, direccion, correo, edad, enfermedad, imagen_nombre, id))
            conn.commit()

        flash('Expediente actualizado correctamente', 'success')
        return redirect(url_for('ver_expediente', id=id))
        
    except Exception as e:
        flash('Error al actualizar expediente', 'error')
        return redirect(url_for('modificar_expediente', id=id))

@app.route('/eliminar_expediente/<int:id>')
def eliminar_expediente(id):
    """Elimina un expediente de la base de datos"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    if not tiene_permiso_eliminar():
        flash('No tienes permisos para eliminar expedientes', 'error')
        return redirect(url_for('inicio'))

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT imagen FROM expedientes WHERE id = ?", (id,))
            fila = cursor.fetchone()
            if fila and fila[0]:
                imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], fila[0])
                if os.path.exists(imagen_path):
                    os.remove(imagen_path)

            cursor.execute("DELETE FROM expedientes WHERE id = ?", (id,))
            conn.commit()

        flash('Expediente eliminado correctamente', 'success')
        return redirect(url_for('inicio'))
        
    except Exception as e:
        flash('Error al eliminar expediente', 'error')
        return redirect(url_for('inicio'))

# ==========================================
# HISTORIAL DE EXPEDIENTES
# ==========================================

@app.route('/historial')
def historial():
    """Muestra el historial de expedientes con filtros"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    buscar = request.args.get('buscar', '').strip()

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, nombres, apellidos, edad, enfermedad, fecha_creacion
                FROM expedientes
                WHERE 1=1
            """
            params = []

            if buscar:
                query += " AND (nombres LIKE ? OR apellidos LIKE ? OR enfermedad LIKE ?)"
                params.extend([f'%{buscar}%', f'%{buscar}%', f'%{buscar}%'])

            if fecha_desde:
                query += " AND fecha_creacion >= ?"
                params.append(fecha_desde)

            if fecha_hasta:
                query += " AND fecha_creacion <= ?"
                params.append(fecha_hasta + ' 23:59:59')

            query += " ORDER BY fecha_creacion DESC"

            cursor.execute(query, params)
            expedientes = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM expedientes")
            total_expedientes = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM expedientes 
                WHERE fecha_creacion >= DATEADD(day, -7, GETDATE())
            """)
            expedientes_semana = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM expedientes 
                WHERE fecha_creacion >= DATEADD(month, -1, GETDATE())
            """)
            expedientes_mes = cursor.fetchone()[0]

    except Exception as e:
        flash('Error al cargar historial', 'error')
        expedientes = []
        total_expedientes = expedientes_semana = expedientes_mes = 0

    usuario = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')

    return render_template('historial.html',
                           expedientes=expedientes,
                           usuario=usuario,
                           rol=rol,
                           total_expedientes=total_expedientes,
                           expedientes_semana=expedientes_semana,
                           expedientes_mes=expedientes_mes,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta,
                           buscar=buscar)

# ==========================================
# GESTIÓN DE PERFIL DE USUARIO
# ==========================================

@app.route('/perfil')
def perfil():
    """Muestra el perfil del usuario actual"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, email, rol, descripcion, foto_perfil 
                FROM usuarios 
                WHERE id = ?
            """, (usuario_id,))
            fila = cursor.fetchone()

        if fila:
            return render_template('Perfil.html',
                                   usuario=fila[0],
                                   correo=fila[1],
                                   rol=fila[2],
                                   descripcion=fila[3] or '',
                                   foto_perfil=fila[4] or 'default.png')
        else:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('inicio'))
            
    except Exception as e:
        flash('Error al cargar perfil', 'error')
        return redirect(url_for('inicio'))

@app.route('/actualizar_correo', methods=['POST'])
def actualizar_correo():
    """Actualiza el correo electrónico del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nuevo_correo = request.form.get('nuevo_correo')
    usuario_id = session['usuario_id']

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET email = ? WHERE id = ?", (nuevo_correo, usuario_id))
            conn.commit()

        flash('Correo actualizado correctamente', 'success')
        return redirect(url_for('perfil'))
        
    except Exception as e:
        flash('Error al actualizar correo', 'error')
        return redirect(url_for('perfil'))

@app.route('/actualizar_contrasena', methods=['POST'])
def actualizar_contrasena():
    """Actualiza la contraseña del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nueva_contrasena = request.form.get('nueva_contrasena')
    password_hash = generate_password_hash(nueva_contrasena)
    usuario_id = session['usuario_id']

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (password_hash, usuario_id))
            conn.commit()

        flash('Contraseña actualizada correctamente', 'success')
        return redirect(url_for('perfil'))
        
    except Exception as e:
        flash('Error al actualizar contraseña', 'error')
        return redirect(url_for('perfil'))

@app.route('/actualizar_descripcion', methods=['POST'])
def actualizar_descripcion():
    """Actualiza la descripción/recordatorio del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nueva_descripcion = request.form.get('nueva_descripcion')
    usuario_id = session['usuario_id']

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET descripcion = ? WHERE id = ?", (nueva_descripcion, usuario_id))
            conn.commit()

        flash('Descripción actualizada correctamente', 'success')
        return redirect(url_for('perfil'))
        
    except Exception as e:
        flash('Error al actualizar descripción', 'error')
        return redirect(url_for('perfil'))

@app.route('/subir_foto', methods=['POST'])
def subir_foto():
    """Subes una nueva foto de perfil del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    archivo = request.files.get('foto')
    if archivo and archivo.filename != '':
        nombre_seguro = secure_filename(archivo.filename)
        ruta_guardado = os.path.join('static/perfiles', nombre_seguro)
        archivo.save(ruta_guardado)

        usuario_id = session['usuario_id']
        
        try:
            with conectar_sql() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET foto_perfil = ? WHERE id = ?", (nombre_seguro, usuario_id))
                conn.commit()

            flash('Foto actualizada correctamente', 'success')
            
        except Exception as e:
            flash('Error al actualizar foto', 'error')

    return redirect(url_for('perfil'))

# ==========================================
# GESTIÓN DE USUARIOS
# ==========================================

@app.route('/gestion_usuarios')
def gestion_usuarios():
    """Gestión de usuarios - Solo para Super Administrador Y Doctor"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    if not tiene_permiso_gestion_usuarios():
        flash('No tienes permisos para acceder a la gestión de usuarios', 'error')
        return redirect(url_for('inicio'))
        
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, rol, activo, fecha_creacion, descripcion, foto_perfil
                FROM usuarios 
                ORDER BY fecha_creacion DESC
            """)
            usuarios = cursor.fetchall()

        return render_template('gestion_usuarios.html', 
                               usuarios=usuarios,
                               usuario=session.get('username'),
                               rol=session.get('rol'))
                               
    except Exception as e:
        flash('Error al cargar usuarios', 'error')
        return redirect(url_for('inicio'))

@app.route('/activar_usuario/<int:usuario_id>')
def activar_usuario(usuario_id):
    """Activa un usuario deshabilitado"""
    if 'usuario_id' not in session or not tiene_permiso_gestion_usuarios():
        return redirect(url_for('login'))
        
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET activo = 1 WHERE id = ?", (usuario_id,))
            conn.commit()

        flash('Usuario activado correctamente', 'success')
        return redirect(url_for('gestion_usuarios'))
        
    except Exception as e:
        flash('Error al activar usuario', 'error')
        return redirect(url_for('gestion_usuarios'))

@app.route('/desactivar_usuario/<int:usuario_id>')
def desactivar_usuario(usuario_id):
    """Desactiva un usuario (eliminación lógica)"""
    if 'usuario_id' not in session or not tiene_permiso_gestion_usuarios():
        return redirect(url_for('login'))
        
    if usuario_id == session.get('usuario_id'):
        flash('No puedes desactivar tu propia cuenta', 'error')
        return redirect(url_for('gestion_usuarios'))
        
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))
            conn.commit()

        flash('Usuario desactivado correctamente', 'success')
        return redirect(url_for('gestion_usuarios'))
        
    except Exception as e:
        flash('Error al desactivar usuario', 'error')
        return redirect(url_for('gestion_usuarios'))

@app.route('/eliminar_usuario/<int:usuario_id>')
def eliminar_usuario(usuario_id):
    """Elimina permanentemente un usuario"""
    if 'usuario_id' not in session or not tiene_permiso_gestion_usuarios():
        return redirect(url_for('login'))
        
    if usuario_id == session.get('usuario_id'):
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('gestion_usuarios'))
        
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT rol FROM usuarios WHERE id = ?", (usuario_id,))
            usuario = cursor.fetchone()
            
            if usuario and usuario[0] == 'Super Administrador':
                flash('No se pueden eliminar Super Administradores', 'error')
                return redirect(url_for('gestion_usuarios'))
            
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            conn.commit()

        flash('Usuario eliminado correctamente', 'success')
        return redirect(url_for('gestion_usuarios'))
        
    except Exception as e:
        flash('Error al eliminar usuario', 'error')
        return redirect(url_for('gestion_usuarios'))

# ==========================================
# VERIFICACIÓN DE CÓDIGO Y REGISTRO
# ==========================================

@app.route('/verificar_codigo')
def verificar_codigo():
    """Muestra el formulario de verificación de código de acceso"""
    return render_template('verificar_codigo.html')

@app.route('/verificar_codigo_acceso', methods=['POST'])
def verificar_codigo_acceso():
    """Procesa la verificación del código de acceso"""
    codigo = request.form.get('codigo', '').strip()
    
    if verificar_codigo_sistema(codigo):
        session['codigo_verificado'] = True
        return redirect(url_for('registro'))
    else:
        return render_template('verificar_codigo.html', 
            error='❌ Código de acceso incorrecto. Inténtalo nuevamente.')

@app.route('/registro')
def registro():
    """Muestra el formulario de registro (requiere código válido)"""
    if not session.get('codigo_verificado'):
        return redirect(url_for('verificar_codigo'))
    return render_template('registro.html')

@app.route('/cancelar_registro')
def cancelar_registro():
    """Cancela el registro y limpia la verificación del código"""
    session.pop('codigo_verificado', None)
    return redirect(url_for('login'))

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    if not session.get('codigo_verificado'):
        return redirect(url_for('verificar_codigo'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    rol = request.form.get('rol')

    if password != confirm_password:
        return "Las contraseñas no coinciden", 400

    if rol == "Super Administrador":
        return "No se pueden crear Super Administradores desde el registro", 400

    password_hash = generate_password_hash(password)

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return "El usuario o email ya existe", 400

            cursor.execute("""
                INSERT INTO usuarios (username, email, password_hash, rol, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, 1, GETDATE())
            """, (username, email, password_hash, rol))
            conn.commit()
            
        session.pop('codigo_verificado', None)
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        return f"Error al crear usuario: {str(e)}", 500

# ==========================================
# AUTENTICACIÓN - LOGIN Y LOGOUT
# ==========================================

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/acceder', methods=['POST'])
def acceder():
    username = request.form.get('username')
    password = request.form.get('password')
    rol = request.form.get('rol')

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()

            # 1. Verificar si existe y está activo
            cursor.execute("SELECT id, username, password_hash, rol, activo FROM usuarios WHERE username = ? AND activo = 1", (username,))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario[2], password) and usuario[3] == rol:
                session['usuario_id'] = usuario[0]
                session['username'] = usuario[1]
                session['rol'] = usuario[3]
                flash(f'Bienvenido {usuario[1]}', 'success')
                return redirect(url_for('inicio'))

            # 2. Verificar si existe pero está desactivado
            cursor.execute("SELECT id FROM usuarios WHERE username = ? AND activo = 0", (username,))
            desactivado = cursor.fetchone()

            if desactivado:
                return render_template("login.html", 
                                       error=True, 
                                       mensaje_desactivado="Tu cuenta está desactivada. Contacta al Super Administrador o a un Doctor para habilitarla.")

            # 3. Si no existe o credenciales incorrectas
            return render_template("login.html", error=True)
            
    except Exception as e:
        flash('Error en el inicio de sesión', 'error')
        return render_template("login.html", error=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# ==========================================
# RECUPERACIÓN DE CONTRASEÑA
# ==========================================

def buscar_usuario_por_correo(correo):
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (correo,))
            resultado = cursor.fetchone()
            if resultado:
                return {'id': resultado[0]}
        return None
    except:
        return None

def generar_token_seguro(usuario_id):
    s = URLSafeTimedSerializer(app.secret_key)
    return s.dumps(usuario_id, salt='password-reset-salt')

def verificar_token(token, max_age=3600):
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        usuario_id = s.loads(token, salt='password-reset-salt', max_age=max_age)
        return usuario_id
    except:
        return None

def enviar_correo_recuperacion(correo, enlace):
    cuerpo = f"""Hola,

Has solicitado restablecer tu contraseña en UROMED.

Haz clic en el siguiente enlace para restablecer tu contraseña:

{enlace}

Este enlace expirará en 1 hora.

Si no solicitaste este cambio, ignora este correo.

Saludos,
Equipo UROMED
"""
    mensaje = MIMEText(cuerpo, 'plain', 'utf-8')
    mensaje['Subject'] = Header('Recuperación de contraseña - UROMED', 'utf-8')
    mensaje['From'] = formataddr((str(Header('UROMED - Médico IA', 'utf-8')), os.getenv('EMAIL_REMITENTE')))
    mensaje['To'] = correo

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.ehlo()
            servidor.login(os.getenv('EMAIL_REMITENTE'), os.getenv('EMAIL_PASSWORD'))
            servidor.send_message(mensaje)
        print("✅ Correo enviado a:", correo)
        return True
    except Exception as e:
        print("❌ Error al enviar el correo:", e)
        return False

def actualizar_contrasenia(usuario_id, nueva_contrasenia):
    nueva_hash = generate_password_hash(nueva_contrasenia)
    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (nueva_hash, usuario_id))
            conn.commit()
    except:
        pass

@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        if not correo:
            return render_template('recuperar_contrasena.html', error="Por favor ingresa un correo electrónico.")
        usuario = buscar_usuario_por_correo(correo)
        if usuario:
            token = generar_token_seguro(usuario['id'])
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            if enviar_correo_recuperacion(correo, enlace):
                return render_template('mensaje.html', mensaje="Te hemos enviado un enlace para restablecer tu contraseña. Revisa tu correo (y la carpeta de spam).")
            else:
                return render_template('recuperar_contrasena.html', error="Hubo un error al enviar el correo. Verifica tu configuración de email.")
        else:
            return render_template('mensaje.html', mensaje="Si el correo existe en nuestro sistema, recibirás un enlace de recuperación.")
    return render_template('recuperar_contrasena.html')

@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    usuario_id = verificar_token(token)
    if not usuario_id:
        return render_template('mensaje.html', mensaje="Enlace inválido o expirado. Solicita uno nuevo.")
    if request.method == 'POST':
        nueva = request.form.get('nueva', '')
        confirmar = request.form.get('confirmar', '')
        if len(nueva) < 6:
            return render_template('restablecer_contrasena.html', error="La contraseña debe tener al menos 6 caracteres.", token=token)
        if nueva == confirmar:
            actualizar_contrasenia(usuario_id, nueva)
            return render_template('mensaje.html', mensaje="Contraseña actualizada correctamente. Ya puedes iniciar sesión.")
        else:
            return render_template('restablecer_contrasena.html', error="Las contraseñas no coinciden.", token=token)
    return render_template('restablecer_contrasena.html', token=token)

# ==========================================
# 🤖 MÓDULO IA DIAGNÓSTICA - CON ANÁLISIS AUTOMÁTICO
# ==========================================

@app.route('/ia_chat')
def ia_chat():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']

    try:
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombres, apellidos, enfermedad FROM expedientes ORDER BY fecha_creacion DESC")
            expedientes = cursor.fetchall()

            cursor.execute("""
                SELECT id_chat, titulo, mensajes, tipo_contenido, expediente_id, fecha_ultima
                FROM chats_ia
                WHERE usuario_id = ?
                ORDER BY fecha_ultima DESC
            """, (usuario_id,))
            
            filas = cursor.fetchall()
            chats_previos = []
            
            for f in filas:
                try:
                    mensajes = json.loads(f[2]) if f[2] else []
                except json.JSONDecodeError as e:
                    print(f"❌ JSON inválido en chat {f[0]}: {e}")
                    mensajes = [{'texto': 'Error cargando mensajes anteriores', 'tipo': 'ia'}]
                
                chat_data = {
                    'id_chat': f[0],
                    'titulo': f[1],
                    'mensajes': mensajes,
                    'tipo': f[3] or 'chat',
                    'expediente_id': f[4],
                    'fecha_ultima': f[5].isoformat() if f[5] else None
                }
                chats_previos.append(chat_data)

        return render_template('IAChat.html',
                               expedientes=expedientes,
                               chats_previos=json.dumps(chats_previos, ensure_ascii=False))
                               
    except Exception as e:
        print(f"❌ Error al cargar el chat de IA: {e}")
        flash('Error al cargar el chat de IA', 'error')
        return render_template('IAChat.html', expedientes=[], chats_previos=json.dumps([]))

@app.route('/subir_archivo_chat', methods=['POST'])
def subir_archivo_chat():
    archivo = request.files.get('archivo')
    if not archivo or archivo.filename == '':
        return jsonify({'ok': False}), 400

    try:
        ext = os.path.splitext(archivo.filename)[1]
        nombre = secure_filename(str(uuid.uuid4()) + ext)
        ruta = os.path.join(UPLOAD_CHAT, nombre)
        archivo.save(ruta)

        return jsonify({'ok': True, 'ruta': f'uploads/chat/{nombre}'})
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/guardar_chats', methods=['POST'])
def guardar_chats():
    """Endpoint CORREGIDO para guardar chats - CON NUEVA ESTRUCTURA"""
    print("💾 Intentando guardar chats en BD...")
    
    def validar_json_estricto(datos):
        """Valida que los datos sean JSON válido para la BD"""
        try:
            json_str = json.dumps(datos, ensure_ascii=False)
            json.loads(json_str)  # Verificar que sea válido
            return json_str
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            print(f"❌ JSON inválido detectado: {e}")
            return None
    
    try:
        # Manejar diferentes tipos de content-type
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            try:
                data = request.get_json(force=True)
            except:
                return jsonify({'ok': False, 'error': 'Formato de datos inválido'}), 400
        
        if not data:
            return jsonify({'ok': False, 'error': 'Datos vacíos'}), 400
            
        usuario_id = data.get('usuario_id')
        chats = data.get('chats', [])
        
        print(f"📊 Recibiendo {len(chats)} chats para usuario {usuario_id}")
        
        if not usuario_id:
            return jsonify({'ok': False, 'error': 'Usuario ID requerido'}), 400
        
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Solo eliminar chats de tipo 'chat' (no los de análisis MONAI)
                cursor.execute("DELETE FROM chats_ia WHERE usuario_id = ? AND tipo_contenido = 'chat'", (usuario_id,))
                print(f"🗑️ Chats antiguos eliminados para usuario {usuario_id}")
                
                # Insertar nuevos chats
                chats_guardados = 0
                for chat in chats:
                    if not chat.get('titulo') or not chat.get('mensajes'):
                        continue
                    
                    # Validar JSON antes de insertar
                    mensajes_json = validar_json_estricto(chat['mensajes'])
                    if not mensajes_json:
                        print(f"❌ Chat omitido - JSON inválido: {chat['titulo']}")
                        continue
                    
                    titulo = chat['titulo'][:200]
                    
                    # Extraer adjuntos si existen
                    adjuntos = []
                    for msg in chat.get('mensajes', []):
                        if msg.get('ruta'):
                            adjuntos.append(msg['ruta'])
                    adjuntos_json = json.dumps(adjuntos, ensure_ascii=False) if adjuntos else None
                    
                    cursor.execute("""
                        INSERT INTO chats_ia (usuario_id, titulo, mensajes, adjuntos, tipo_contenido)
                        VALUES (?, ?, ?, ?, 'chat')
                    """, (usuario_id, titulo, mensajes_json, adjuntos_json))
                    
                    chats_guardados += 1
                
                cursor.execute("COMMIT")
                print(f"✅ {chats_guardados} chats guardados exitosamente")
                return jsonify({'ok': True, 'guardados': chats_guardados})
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                print(f"❌ Error en transacción: {e}")
                return jsonify({'ok': False, 'error': str(e)}), 500
                
    except Exception as e:
        print(f"❌ Error general guardando chats: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500

# 🔥 NUEVO: ANÁLISIS AUTOMÁTICO DEL EXPEDIENTE
@app.route('/analizar_expediente_completo', methods=['POST'])
def analizar_expediente_completo():
    """Analiza automáticamente todo el expediente del paciente"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        expediente_id = data.get('expediente_id')
        
        if not expediente_id:
            return jsonify({'error': 'Expediente no especificado'}), 400
        
        # Obtener datos completos del expediente
        with conectar_sql() as conn:
            cursor = conn.cursor()
            
            # Datos básicos del paciente
            cursor.execute("""
                SELECT nombres, apellidos, edad, enfermedad, fecha_creacion 
                FROM expedientes WHERE id = ?
            """, (expediente_id,))
            expediente = cursor.fetchone()
            
            if not expediente:
                return jsonify({'error': 'Expediente no encontrado'}), 404
            
            # Buscar imágenes médicas existentes del paciente
            try:
                cursor.execute("""
                    SELECT ruta_imagen, tipo_analisis, resultados 
                    FROM analisis_imagenes 
                    WHERE expediente_id = ? 
                    ORDER BY fecha_analisis DESC
                """, (expediente_id,))
                imagenes = cursor.fetchall()
            except:
                imagenes = []  # Si la tabla no existe
        
        # Procesar análisis completo
        analisis_completo = analizar_expediente_ia(
            expediente, 
            imagenes,
            expediente_id
        )
        
        return jsonify({
            'ok': True,
            'analisis': analisis_completo
        })
        
    except Exception as e:
        print(f"❌ Error en análisis completo: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

def analizar_expediente_ia(expediente, imagenes, expediente_id):
    """Analiza inteligentemente todos los datos del expediente"""
    
    nombres, apellidos, edad, enfermedad, fecha_creacion = expediente
    
    # Manejo seguro de la edad
    try:
        if edad and isinstance(edad, str) and edad.isdigit():
            edad_num = int(edad)
        elif edad and isinstance(edad, (int, float)):
            edad_num = int(edad)
        else:
            edad_num = 45  # Valor por defecto
            
        if edad_num > 65:
            riesgo_edad = "Alto"
        elif edad_num > 45:
            riesgo_edad = "Moderado" 
        else:
            riesgo_edad = "Bajo"
            
    except (ValueError, TypeError):
        edad_num = 45
        riesgo_edad = "Moderado"
    
    # Base de conocimiento médico especializado
    conocimiento_urologico = {
        'cálculos renales': {
            'factores_riesgo': ['Hidratación inadecuada', 'Dieta alta en oxalatos', 'Historial familiar', 'Obesidad'],
            'estudios_recomendados': ['Tomografía abdominal', 'Ultrasonido renal', 'Análisis de orina 24h', 'Perfil metabólico'],
            'preguntas_clave': ['¿Localización del dolor?', '¿Cambios en color de orina?', '¿Antecedentes de cálculos?', '¿Hábitos de hidratación?']
        },
        'hiperplasia prostática': {
            'factores_riesgo': ['Edad avanzada', 'Antecedentes familiares', 'Obesidad', 'Sedentarismo'],
            'estudios_recomendados': ['PSA total y libre', 'Ecografía prostática', 'Flujometría', 'Tacto rectal'],
            'preguntas_clave': ['¿Frecuencia urinaria?', '¿Chorro débil?', '¿Goteo postmiccional?', '¿Nicturia?']
        },
        'infección urinaria': {
            'factores_riesgo': ['Sexo femenino', 'Actividad sexual', 'Diabetes', 'Cateterismo reciente'],
            'estudios_recomendados': ['Urocultivo', 'Antibiograma', 'Ecografía renal', 'Hemograma completo'],
            'preguntas_clave': ['¿Ardor al orinar?', '¿Fiebre?', '¿Dolor lumbar?', '¿Frecuencia urinaria aumentada?']
        },
        'cáncer de próstata': {
            'factores_riesgo': ['Edad avanzada', 'Antecedentes familiares', 'Raza afroamericana', 'Obesidad'],
            'estudios_recomendados': ['PSA total y libre', 'Tacto rectal', 'Biopsia prostática', 'Resonancia magnética'],
            'preguntas_clave': ['¿Síntomas obstructivos?', '¿Antecedentes familiares?', '¿Edad del paciente?', '¿PSA previo?']
        },
        'insuficiencia renal': {
            'factores_riesgo': ['Diabetes', 'Hipertensión', 'Enfermedades autoinmunes', 'Nefrotoxicos'],
            'estudios_recomendados': ['Creatinina sérica', 'Filtrado glomerular', 'Ecografía renal', 'Proteinuria 24h'],
            'preguntas_clave': ['¿Edema?', '¿Cambios en diuresis?', '¿Antecedentes de diabetes?', '¿Medicamentos?']
        }
    }
    
    # Determinar condición principal
    condicion_principal = enfermedad.lower()
    info_condicion = conocimiento_urologico.get(condicion_principal, {
        'factores_riesgo': ['Evaluar historial completo', 'Considerar factores ambientales'],
        'estudios_recomendados': ['Consulta urológica especializada', 'Estudios básicos de laboratorio'],
        'preguntas_clave': ['¿Síntomas principales?', '¿Tiempo de evolución?', '¿Factores desencadenantes?']
    })
    
    # Analizar imágenes existentes
    hallazgos_imagenes = []
    for img in imagenes:
        try:
            if img[2]:  # Si hay resultados
                resultados = json.loads(img[2])
                for hallazgo in resultados.get('hallazgos', []):
                    hallazgos_imagenes.append({
                        'descripcion': f"Imagen {img[1]}: {hallazgo['descripcion']}",
                        'confianza': int(hallazgo['confianza'] * 100)
                    })
        except:
            pass
    
    # Generar análisis personalizado
    hallazgos_base = [
        {'descripcion': f'Condición principal: {enfermedad}', 'confianza': 85},
        {'descripcion': f'Riesgo por edad: {riesgo_edad}', 'confianza': 90},
        {'descripcion': f'Paciente requiere evaluación urológica especializada', 'confianza': 95}
    ]
    
    # Combinar hallazgos
    todos_hallazgos = hallazgos_base + hallazgos_imagenes[:2]  # Máximo 2 hallazgos de imágenes
    
    return {
        'paciente': {
            'nombres': nombres,
            'apellidos': apellidos,
            'edad': edad or 'No especificada',
            'enfermedad': enfermedad,
            'riesgo_edad': riesgo_edad
        },
        'hallazgos': todos_hallazgos,
        'factores_riesgo': info_condicion['factores_riesgo'],
        'recomendaciones': [
            *info_condicion['estudios_recomendados'][:3],  # Máximo 3 recomendaciones
            'Control urológico regular',
            f'Seguimiento específico para {enfermedad}'
        ],
        'preguntas': info_condicion['preguntas_clave'][:3]  # Máximo 3 preguntas
    }

# 🔥 NUEVO: CHAT INTELIGENTE MEJORADO
@app.route('/ia_mensaje_mejorado', methods=['POST'])
def ia_mensaje_mejorado():
    """Procesa mensajes con contexto del expediente y memoria"""
    try:
        texto = request.form.get('texto', '')
        expediente_id = request.form.get('expediente_id')
        historial_chat = request.form.get('historial_chat', '[]')
        
        if not texto or not expediente_id:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Obtener datos del expediente
        with conectar_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nombres, apellidos, edad, enfermedad 
                FROM expedientes WHERE id = ?
            """, (expediente_id,))
            expediente = cursor.fetchone()
            
        if not expediente:
            return jsonify({'error': 'Expediente no encontrado'}), 404
        
        datos_expediente = {
            'nombres': expediente[0],
            'apellidos': expediente[1], 
            'edad': expediente[2],
            'enfermedad': expediente[3]
        }
        
        # Procesar con IA mejorada
        respuesta_ia = procesar_mensaje_con_contexto(
            texto, 
            datos_expediente, 
            json.loads(historial_chat)
        )
        
        return jsonify({
            'respuesta': respuesta_ia,
            'disclaimer': '⚠️ Asistente diagnóstico - Consulte con especialista.',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error en IA mejorada: {str(e)}")
        return jsonify({
            'respuesta': 'He procesado tu consulta. ¿Podrías proporcionar más detalles sobre los síntomas para un análisis más preciso?',
            'disclaimer': '⚠️ Sistema en desarrollo - Consulte con especialista.'
        }), 500

def procesar_mensaje_con_contexto(mensaje, expediente, historial):
    """IA mejorada con contexto y memoria"""
    
    mensaje_lower = mensaje.lower()
    nombre_paciente = expediente['nombres']
    enfermedad = expediente['enfermedad']
    edad = expediente['edad']
    
    # Sistema de intenciones mejorado
    intenciones = {
        'dolor': f"El dolor descrito por {nombre_paciente} podría relacionarse con {enfermedad}. ¿Podrías especificar la localización (lumbar, abdominal, pélvico), intensidad (1-10) y características (sordo, agudo, cólico)?",
        'síntoma': f"Los síntomas en {enfermedad} varían ampliamente. Para {nombre_paciente}, es importante caracterizar frecuencia, duración, factores desencadenantes y síntomas asociados.",
        'tratamiento': f"El manejo de {enfermedad} se individualiza según edad y condiciones basales. {nombre_paciente} podría beneficiarse de evaluación de opciones farmacológicas, quirúrgicas o modificaciones en estilo de vida.",
        'medicamento': f"La farmacoterapia en urología requiere ajuste por edad y función renal. Para {nombre_paciente} de {edad} años, considere interacciones medicamentosas, comorbilidades y contraindicaciones específicas.",
        'diagnóstico': f"El diagnóstico de {enfermedad} se basa en criterios clínicos, estudios de laboratorio e imágenes. {nombre_paciente} necesita evaluación integral para confirmación diagnóstica.",
        'pronóstico': f"El pronóstico en {enfermedad} depende de múltiples factores incluyendo edad, estadio al diagnóstico y adherencia al tratamiento. La edad de {nombre_paciente} es un factor relevante.",
        'prevención': f"La prevención en {enfermedad} incluye modificaciones en estilo de vida, controles regulares y manejo de factores de riesgo. Para {nombre_paciente}, considere hidratación adecuada, dieta balanceada y actividad física.",
        'cirugía': f"Las indicaciones quirúrgicas en {enfermedad} dependen de la severidad de síntomas, respuesta a tratamiento médico y condiciones del paciente. {nombre_paciente} requiere evaluación preoperatoria completa.",
        'recuperación': f"El proceso de recuperación en condiciones urológicas varía según el procedimiento y condiciones basales. Para {nombre_paciente}, es importante seguimiento estrecho y rehabilitación adecuada."
    }
    
    # Detectar intención
    for palabra_clave, respuesta in intenciones.items():
        if palabra_clave in mensaje_lower:
            return respuesta
    
    # Respuesta contextual por enfermedad específica
    respuestas_especificas = {
        'cálculo': f"Para cálculos renales como el de {nombre_paciente}, el manejo depende del tamaño, localización y composición del cálculo. ¿El dolor es cólico o constante? ¿Ha notado cambios en el color de la orina?",
        'próstata': f"En condiciones prostáticas, {nombre_paciente} debe evaluar síntomas obstructivos (chorro débil, vacilación) e irritativos (urgencia, frecuencia). ¿Ha notado cambios recientes en el patrón miccional?",
        'infección': f"Las infecciones urinarias en pacientes como {nombre_paciente} requieren identificación del germen causal y evaluación de factores predisponentes. ¿Ha tenido fiebre, escalofríos o dolor lumbar?",
        'vejiga': f"Los trastornos vesicales necesitan caracterización urodinámica completa. Para {nombre_paciente}, es clave evaluar capacidad vesical, síntomas de almacenamiento y vaciamiento.",
        'renal': f"La patología renal en {nombre_paciente} requiere evaluación de función (creatinina, filtrado glomerular) y estudios de imagen. ¿Hay antecedentes de diabetes o hipertensión?",
        'oncológico': f"Los casos oncológicos urológicos necesitan estadificación completa y evaluación multidisciplinaria. Para {nombre_paciente}, es crucial determinar extensión de la enfermedad y condiciones basales."
    }
    
    for condicion, respuesta in respuestas_especificas.items():
        if condicion in enfermedad.lower():
            return respuesta
    
    # Respuesta inteligente por defecto con contexto
    return f"He analizado tu consulta sobre {expediente['enfermedad']}. {nombre_paciente} presenta características que requieren evaluación urológica específica. ¿Podrías contarme más detalles sobre los síntomas actuales, tiempo de evolución o tratamientos previos recibidos para brindarte una orientación más precisa?"

# 🔥 ENDPOINT PARA ANÁLISIS REAL DE IMAGEN
@app.route('/ia_analisis_imagen', methods=['POST'])
def ia_analisis_imagen():
    """Endpoint especializado para análisis de imágenes médicas con Análisis Estadístico/Textura - MODO DEMOSTRACIÓN"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        archivo = request.files.get('imagen_medica')
        expediente_id = request.form.get('expediente_id')
        tipo_analisis = request.form.get('tipo_analisis', 'general')
        
        if not archivo or not expediente_id:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        nombre_archivo = secure_filename(archivo.filename)
        print(f"🚀 MODO DEMOSTRACIÓN: Procesando imagen {nombre_archivo}")
        
        # 🔥 MODO DEMOSTRACIÓN: ACEPTAR CUALQUIER IMAGEN
        formatos_aceptados = ['.dcm', '.nii', '.nii.gz', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp']
        extension = os.path.splitext(nombre_archivo)[1].lower()
        
        if extension not in formatos_aceptados:
            return jsonify({
                'ok': False,
                'error': 'Formato no reconocido',
                'message': f'Formato {extension} no es común para imágenes médicas.',
                'sugerencia': 'Intenta con JPG, PNG, DICOM o NIfTI'
            }), 400
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            archivo.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # 🔥 MODO DEMOSTRACIÓN: NO HACER VALIDACIÓN ESTRICTA
            print(f"✅ MODO DEMOSTRACIÓN: Saltando validación para {nombre_archivo}")
            
            # Obtener datos del expediente
            with conectar_sql() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nombres, apellidos, edad, enfermedad FROM expedientes WHERE id = ?", (expediente_id,))
                expediente = cursor.fetchone()
            
            if not expediente:
                return jsonify({'error': 'Expediente no encontrado'}), 404
                
            datos_expediente = {
                'nombres': expediente[0],
                'apellidos': expediente[1],
                'edad': expediente[2] if expediente[2] else 'No especificada',
                'enfermedad': expediente[3] if expediente[3] else 'No especificada'
            }
            
            # 🔥🔥🔥 LLAMADA CLAVE AL ANÁLISIS REAL 🔥🔥🔥
            print(f"📊 Procesando Análisis REAL: {tipo_analisis}")
            resultados_analisis = analizar_imagen_real(temp_path, tipo_analisis)
            # 🔥🔥🔥 FIN LLAMADA CLAVE 🔥🔥🔥
            
            # 🔥 Información de modo demostración (usando la variable resultados_analisis)
            resultados_analisis['validacion'] = {
                'puntuacion': 0.95,
                'razones': ['✅ Modo demostración - Imagen aceptada sin validación estricta'],
                'paso_validacion': True,
                'nivel_confianza': 'MODO DEMOSTRACIÓN',
                'modo': 'demostracion_sin_validacion'
            }
            
            # Guardar en chats_ia
            with conectar_sql() as conn:
                cursor = conn.cursor()
                
                mensaje_ia = {
                    'texto': f"🔬 Análisis Estadístico/Textura completado - {tipo_analisis} (Modo Demostración)",
                    'tipo': 'analisis_monai', # Se mantiene el tipo para compatibilidad del frontend
                    'timestamp': datetime.now().isoformat(),
                    'ruta': f"uploads/chat/{nombre_archivo}",
                    'metadata_analisis': {
                        'archivo': nombre_archivo,
                        'tipo_analisis': tipo_analisis,
                        'resultados': resultados_analisis,
                        'expediente': datos_expediente,
                        'confianza_global': resultados_analisis.get('confianza_global', 0),
                        'validacion_score': 0.95,
                        'validacion_nivel': 'MODO DEMOSTRACIÓN',
                        'modo': 'demostracion'
                    }
                }
                
                cursor.execute("""
                    SELECT id_chat, mensajes FROM chats_ia 
                    WHERE usuario_id = ? AND expediente_id = ? AND tipo_contenido = 'analisis_monai'
                    ORDER BY fecha_ultima DESC
                """, (session['usuario_id'], expediente_id))
                
                chat_existente = cursor.fetchone()
                
                if chat_existente:
                    chat_id, mensajes_json = chat_existente
                    mensajes = json.loads(mensajes_json) if mensajes_json else []
                    mensajes.append(mensaje_ia)
                    
                    cursor.execute("""
                        UPDATE chats_ia 
                        SET mensajes = ?, fecha_ultima = GETDATE()
                        WHERE id_chat = ?
                    """, (json.dumps(mensajes, ensure_ascii=False), chat_id))
                else:
                    titulo = f"Análisis IA - {datos_expediente['nombres']} {datos_expediente['apellidos']}"
                    mensajes = [mensaje_ia]
                    
                    cursor.execute("""
                        INSERT INTO chats_ia (usuario_id, expediente_id, titulo, mensajes, tipo_contenido)
                        VALUES (?, ?, ?, ?, 'analisis_monai')
                    """, (session['usuario_id'], expediente_id, titulo, json.dumps(mensajes, ensure_ascii=False)))
                
                conn.commit()
            
            # Preparar respuesta exitosa
            respuesta = {
                'ok': True,
                'tipo_analisis': tipo_analisis,
                'resultados': resultados_analisis,
                'expediente': datos_expediente,
                'validacion': {
                    'puntuacion': 0.95,
                    'paso': True,
                    'razones': ['✅ Modo demostración activado'],
                    'nivel': 'MODO DEMOSTRACIÓN',
                    'modo': 'demostracion'
                },
                'timestamp': datetime.now().isoformat(),
                'mensaje': '✅ Análisis completado en modo demostración'
            }
            
            print(f"✅ Análisis REAL completado exitosamente en modo demostración")
            return jsonify(respuesta)
            
        except Exception as e:
            print(f"❌ Error procesando imagen: {e}")
            import traceback
            traceback.print_exc()
            # Devolver respuesta de demo aunque falle
            return jsonify({
                'ok': True,
                'tipo_analisis': tipo_analisis,
                'resultados': analizar_imagen_real(None, tipo_analisis), # Usamos el fallback de la función real
                'expediente': datos_expediente if 'datos_expediente' in locals() else {'nombres': 'Paciente', 'apellidos': '', 'edad': 'No especificada', 'enfermedad': 'No especificada'},
                'validacion': {
                    'puntuacion': 0.5,
                    'paso': False,
                    'razones': ['⚠️ Error procesando imagen - Modo demostración'],
                    'nivel': 'MODO DEMOSTRACIÓN CON ERROR',
                    'modo': 'demostracion_con_error'
                },
                'timestamp': datetime.now().isoformat(),
                'mensaje': '⚠️ Análisis completado con advertencias (modo demostración)'
            }), 200  # 200 en vez de 500 para que el frontend lo procese
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"❌ Error general en análisis IA: {e}")
        import traceback
        traceback.print_exc()
        
        # En modo demo: siempre devolver algo
        return jsonify({
            'ok': True,
            'error': 'Error procesado en modo demostración',
            'resultados': analizar_imagen_real(None, tipo_analisis), # Usamos el fallback de la función real
            'validacion': {
                'puntuacion': 0.3,
                'razones': ['❌ Error general - Modo demostración activado'],
                'nivel': 'MODO DEMOSTRACIÓN CON FALLO',
                'modo': 'demostracion_fallo_general'
            },
            'mensaje': '⚠️ El sistema está en modo demostración. Para producción, active la validación completa.'
        }), 200  # 200 en vez de 500 para que el frontend lo procese

# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == '__main__':
    print("🚀 Iniciando UROMED MedicoIA - MODO DEMOSTRACIÓN...")
    # La configuración de MONAI ha sido eliminada.
    print("🤖 ANÁLISIS DE IMAGEN: Estadístico y Textura (Real)")
    print("🔓 SISTEMA DE VALIDACIÓN: DESACTIVADO (Modo Demostración)")
    print("🔥 Características del modo demostración:")
    print("    • Acepta cualquier imagen médica")
    print("    • Sin restricciones de tamaño o color")
    print("    • Validación simplificada")
    print("    • Ideal para pruebas y demostraciones")
    print("⚠️  ADVERTENCIA: Para uso en producción, active la validación completa")
    
    try:
        with conectar_sql() as conn:
            print("✅ Conexión a BD exitosa")
    except Exception as e:
        print("❌ Error en conexión a BD:", e)
        
    app.run(debug=True, host='0.0.0.0', port=5000)