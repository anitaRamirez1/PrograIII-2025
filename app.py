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

load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura_uromed_2025'

UPLOAD_FOLDER = 'static/uploads'
PERFILES_FOLDER = 'static/perfiles'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear directorios si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PERFILES_FOLDER, exist_ok=True)

# ==========================================
# FUNCIONES DE CONEXIÓN Y UTILIDADES
# ==========================================

def conectar_sql():
    """Conecta con la base de datos SQL Server"""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=DESKTOP-IFV9P3G\\SQLEXPRESS;"
            "DATABASE=UROMED;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        return conn
    except pyodbc.Error as e:
        print(f"❌ Error de conexión: {e}")
        return None

def verificar_codigo_sistema(codigo_ingresado):
    """Verifica si el código ingresado es válido contra la base de datos"""
    conn = conectar_sql()
    if not conn:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT codigo_hash FROM codigos_acceso WHERE activo = 1")
        resultado = cursor.fetchone()
        
        if resultado:
            # SOLUCIÓN CORRECTA: Usar check_password_hash para comparar el hash
            es_valido = check_password_hash(resultado[0], codigo_ingresado)
            if es_valido:
                print(f"✅ Código correcto!")
            else:
                print(f"❌ Código incorrecto")
            return es_valido
        return False
    except pyodbc.Error as e:
        print(f"❌ Error al verificar código: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# RUTAS PRINCIPALES - EXPEDIENTES
# ==========================================

@app.route('/')
def inicio():
    """Página principal - Muestra lista de expedientes"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = conectar_sql()
    if not conn:
        return "Error de conexión a la base de datos", 500
        
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombres, apellidos, enfermedad FROM expedientes")
    expedientes = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM expedientes")
    total_expedientes = cursor.fetchone()[0]

    conn.close()

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

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
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

    conn.close()

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
        conn = conectar_sql()
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
        conn.close()
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

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expedientes (nombres, apellidos, telefono, direccion, correo, edad, enfermedad, imagen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nombres, apellidos, telefono, direccion, correo, edad, enfermedad, imagen_nombre))
    conn.commit()
    conn.close()

    return redirect(url_for('inicio'))

@app.route('/ver_expediente/<int:id>')
def ver_expediente(id):
    """Muestra los detalles completos de un expediente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expedientes WHERE id = ?", (id,))
    fila = cursor.fetchone()
    conn.close()

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
        return "Expediente no encontrado", 404

@app.route('/modificar_expediente/<int:id>')
def modificar_expediente(id):
    """Muestra formulario para modificar un expediente existente"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expedientes WHERE id = ?", (id,))
    fila = cursor.fetchone()
    conn.close()

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
        return "Expediente no encontrado", 404

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

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
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
    conn.close()

    return redirect(url_for('ver_expediente', id=id))

@app.route('/eliminar_expediente/<int:id>')
def eliminar_expediente(id):
    """Elimina un expediente de la base de datos"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()

    cursor.execute("SELECT imagen FROM expedientes WHERE id = ?", (id,))
    fila = cursor.fetchone()
    if fila and fila[0]:
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], fila[0])
        if os.path.exists(imagen_path):
            os.remove(imagen_path)

    cursor.execute("DELETE FROM expedientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

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

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
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

    conn.close()

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
    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, email, rol, descripcion, foto_perfil 
        FROM usuarios 
        WHERE id = ?
    """, (usuario_id,))
    fila = cursor.fetchone()
    conn.close()

    if fila:
        return render_template('Perfil.html',
                               usuario=fila[0],
                               correo=fila[1],
                               rol=fila[2],
                               descripcion=fila[3] or '',
                               foto_perfil=fila[4] or 'default.png')
    else:
        return "Usuario no encontrado", 404

@app.route('/actualizar_correo', methods=['POST'])
def actualizar_correo():
    """Actualiza el correo electrónico del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nuevo_correo = request.form.get('nuevo_correo')
    usuario_id = session['usuario_id']

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET email = ? WHERE id = ?", (nuevo_correo, usuario_id))
    conn.commit()
    conn.close()

    return redirect(url_for('perfil'))

@app.route('/actualizar_contrasena', methods=['POST'])
def actualizar_contrasena():
    """Actualiza la contraseña del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nueva_contrasena = request.form.get('nueva_contrasena')
    password_hash = generate_password_hash(nueva_contrasena)
    usuario_id = session['usuario_id']

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (password_hash, usuario_id))
    conn.commit()
    conn.close()

    return redirect(url_for('perfil'))

@app.route('/actualizar_descripcion', methods=['POST'])
def actualizar_descripcion():
    """Actualiza la descripción/recordatorio del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nueva_descripcion = request.form.get('nueva_descripcion')
    usuario_id = session['usuario_id']

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET descripcion = ? WHERE id = ?", (nueva_descripcion, usuario_id))
    conn.commit()
    conn.close()

    return redirect(url_for('perfil'))

@app.route('/subir_foto', methods=['POST'])
def subir_foto():
    """Sube una nueva foto de perfil del usuario"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    archivo = request.files.get('foto')
    if archivo and archivo.filename != '':
        nombre_seguro = secure_filename(archivo.filename)
        ruta_guardado = os.path.join('static/perfiles', nombre_seguro)
        archivo.save(ruta_guardado)

        usuario_id = session['usuario_id']
        conn = conectar_sql()
        if not conn:
            return "Error de conexión", 500
            
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET foto_perfil = ? WHERE id = ?", (nombre_seguro, usuario_id))
        conn.commit()
        conn.close()

    return redirect(url_for('perfil'))

# ==========================================
# 🎯 GESTIÓN DE USUARIOS - SUPER ADMINISTRADOR
# ==========================================

@app.route('/gestion_usuarios')
def gestion_usuarios():
    """Gestión de usuarios - Solo para Super Administrador"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Verificar que sea Super Administrador
    if session.get('rol') != 'Super Administrador':
        return redirect(url_for('inicio'))
    
    conn = conectar_sql()
    if not conn:
        return "Error de conexión a la base de datos", 500
        
    cursor = conn.cursor()
    
    # Obtener todos los usuarios
    cursor.execute("""
        SELECT id, username, email, rol, activo, fecha_creacion, descripcion, foto_perfil
        FROM usuarios 
        ORDER BY fecha_creacion DESC
    """)
    usuarios = cursor.fetchall()
    
    conn.close()

    return render_template('gestion_usuarios.html', 
                         usuarios=usuarios,
                         usuario=session.get('username'),
                         rol=session.get('rol'))

@app.route('/activar_usuario/<int:usuario_id>')
def activar_usuario(usuario_id):
    """Activa un usuario deshabilitado"""
    if 'usuario_id' not in session or session.get('rol') != 'Super Administrador':
        return redirect(url_for('login'))
    
    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET activo = 1 WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()
    
    flash('Usuario activado correctamente', 'success')
    return redirect(url_for('gestion_usuarios'))

@app.route('/desactivar_usuario/<int:usuario_id>')
def desactivar_usuario(usuario_id):
    """Desactiva un usuario (eliminación lógica)"""
    if 'usuario_id' not in session or session.get('rol') != 'Super Administrador':
        return redirect(url_for('login'))
    
    # Prevenir que el Super Admin se desactive a sí mismo
    if usuario_id == session.get('usuario_id'):
        flash('No puedes desactivar tu propia cuenta', 'error')
        return redirect(url_for('gestion_usuarios'))
    
    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()
    
    flash('Usuario desactivado correctamente', 'success')
    return redirect(url_for('gestion_usuarios'))

@app.route('/eliminar_usuario/<int:usuario_id>')
def eliminar_usuario(usuario_id):
    """Elimina permanentemente un usuario"""
    if 'usuario_id' not in session or session.get('rol') != 'Super Administrador':
        return redirect(url_for('login'))
    
    # Prevenir eliminaciones críticas
    if usuario_id == session.get('usuario_id'):
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('gestion_usuarios'))
    
    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    
    # Verificar que no sea Super Administrador
    cursor.execute("SELECT rol FROM usuarios WHERE id = ?", (usuario_id,))
    usuario = cursor.fetchone()
    
    if usuario and usuario[0] == 'Super Administrador':
        flash('No se pueden eliminar Super Administradores', 'error')
        return redirect(url_for('gestion_usuarios'))
    
    # Eliminar usuario
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()
    
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('gestion_usuarios'))

# ==========================================
# ✨ VERIFICACIÓN DE CÓDIGO Y REGISTRO
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
        # Código correcto - guardar en sesión y redirigir a registro
        session['codigo_verificado'] = True
        return redirect(url_for('registro'))
    else:
        # Código incorrecto
        return render_template('verificar_codigo.html', 
            error='❌ Código de acceso incorrecto. Inténtalo nuevamente.')

@app.route('/registro')
def registro():
    """Muestra el formulario de registro (requiere código válido)"""
    # Verificar que el código haya sido validado
    if not session.get('codigo_verificado'):
        return redirect(url_for('verificar_codigo'))
    return render_template('registro.html')

@app.route('/cancelar_registro')
def cancelar_registro():
    """Cancela el registro y limpia la verificación del código"""
    # Limpiar la verificación de código
    session.pop('codigo_verificado', None)
    # Redirigir al login
    return redirect(url_for('login'))

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    """Crea un nuevo usuario en la base de datos"""
    # Verificar que el código haya sido validado
    if not session.get('codigo_verificado'):
        return redirect(url_for('verificar_codigo'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    rol = request.form.get('rol')

    if password != confirm_password:
        return "Las contraseñas no coinciden", 400

    # Prevenir creación de Super Administradores desde el registro
    if rol == "Super Administrador":
        return "No se pueden crear Super Administradores desde el registro", 400

    password_hash = generate_password_hash(password)

    conn = conectar_sql()
    if not conn:
        return "Error de conexión", 500
        
    cursor = conn.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email))
    if cursor.fetchone():
        conn.close()
        return "El usuario o email ya existe", 400

    cursor.execute("""
        INSERT INTO usuarios (username, email, password_hash, rol, activo, fecha_creacion)
        VALUES (?, ?, ?, ?, 1, GETDATE())
    """, (username, email, password_hash, rol))
    conn.commit()
    conn.close()

    # Limpiar la verificación de código después de crear usuario
    session.pop('codigo_verificado', None)
    
    return redirect(url_for('login'))

# ==========================================
# AUTENTICACIÓN - LOGIN Y LOGOUT
# ==========================================

@app.route('/login')
def login():
    """Muestra el formulario de inicio de sesión"""
    return render_template('login.html')

@app.route('/acceder', methods=['POST'])
def acceder():
    """Procesa el inicio de sesión del usuario"""
    username = request.form.get('username')
    password = request.form.get('password')
    rol = request.form.get('rol')

    conn = conectar_sql()
    if not conn:
        return render_template("login.html", error=True)
        
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, rol FROM usuarios WHERE username = ?", (username,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario and check_password_hash(usuario[2], password) and usuario[3] == rol:
        session['usuario_id'] = usuario[0]
        session['username'] = usuario[1]
        session['rol'] = usuario[3]
        return redirect(url_for('inicio'))
    else:
        return render_template("login.html", error=True)

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario"""
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# RECUPERACIÓN DE CONTRASEÑA
# ==========================================

def buscar_usuario_por_correo(correo):
    """Busca un usuario por su correo electrónico"""
    conn = conectar_sql()
    if not conn:
        return None
        
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (correo,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return {'id': resultado[0]}
    return None

def generar_token_seguro(usuario_id):
    """Genera un token seguro para recuperación de contraseña"""
    s = URLSafeTimedSerializer(app.secret_key)
    return s.dumps(usuario_id, salt='password-reset-salt')

def verificar_token(token, max_age=3600):
    """Verifica si un token de recuperación es válido"""
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        usuario_id = s.loads(token, salt='password-reset-salt', max_age=max_age)
        return usuario_id
    except:
        return None

def enviar_correo_recuperacion(correo, enlace):
    """Envía un correo con el enlace de recuperación de contraseña"""
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
    """Actualiza la contraseña de un usuario"""
    nueva_hash = generate_password_hash(nueva_contrasenia)
    conn = conectar_sql()
    if not conn:
        return
        
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (nueva_hash, usuario_id))
    conn.commit()
    conn.close()

@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    """Solicita la recuperación de contraseña"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        
        if not correo:
            return render_template('recuperar_contrasena.html', 
                error="Por favor ingresa un correo electrónico.")
        
        usuario = buscar_usuario_por_correo(correo)
        if usuario:
            token = generar_token_seguro(usuario['id'])
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            
            if enviar_correo_recuperacion(correo, enlace):
                return render_template('mensaje.html', 
                    mensaje="Te hemos enviado un enlace para restablecer tu contraseña. Revisa tu correo (y la carpeta de spam).")
            else:
                return render_template('recuperar_contrasena.html',
                    error="Hubo un error al enviar el correo. Verifica tu configuración de email.")
        else:
            return render_template('mensaje.html', 
                mensaje="Si el correo existe en nuestro sistema, recibirás un enlace de recuperación.")
    
    return render_template('recuperar_contrasena.html')

@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    """Restablece la contraseña usando el token"""
    usuario_id = verificar_token(token)
    if not usuario_id:
        return render_template('mensaje.html', 
            mensaje="Enlace inválido o expirado. Solicita uno nuevo.")

    if request.method == 'POST':
        nueva = request.form.get('nueva', '')
        confirmar = request.form.get('confirmar', '')
        
        if len(nueva) < 6:
            return render_template('restablecer_contrasena.html', 
                error="La contraseña debe tener al menos 6 caracteres.", token=token)
        
        if nueva == confirmar:
            actualizar_contrasenia(usuario_id, nueva)
            return render_template('mensaje.html', 
                mensaje="Contraseña actualizada correctamente. Ya puedes iniciar sesión.")
        else:
            return render_template('restablecer_contrasena.html', 
                error="Las contraseñas no coinciden.", token=token)
    
    return render_template('restablecer_contrasena.html', token=token)


# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == '__main__':
    print("🚀 Iniciando UROMED MedicoIA...")
    print("📧 Configuración de email cargada:", "✅" if os.getenv('EMAIL_REMITENTE') else "❌")
    print("🗄️ Conectando a base de datos...")
    
    # Probar conexión
    conn = conectar_sql()
    if conn:
        print("✅ Conexión a BD exitosa")
        conn.close()
    else:
        print("❌ Error en conexión a BD")
    
    app.run(debug=True, host='0.0.0.0', port=5000)