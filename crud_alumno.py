import crud_academico

db = crud_academico.crud()

class crud_alumno:
    def consultar(self, buscar):
        return db.consultar("SELECT * FROM alumnos WHERE nombre like '%"+ buscar +"%'")
    
def administrar(self, datos):
    accion = datos.get('accion')
    if accion == "nuevo":
        sql = """
            INSERT INTO alumnos (codigo, nombre, direccion, telefono, email)
            VALUES (%s, %s, %s, %s, %s)
        """
        valores = (datos.get('codigo'), datos.get('nombre'), datos.get('direccion'), datos.get('telefono'), datos.get('email'))
    elif accion == "modificar":
        if 'idAlumno' not in datos:
            raise ValueError("Falta el campo 'idAlumno' para modificar")
        sql = """
            UPDATE alumnos SET codigo=%s, nombre=%s, direccion=%s, telefono=%s, email=%s
            WHERE idAlumno=%s
        """
        valores = (datos.get('codigo'), datos.get('nombre'), datos.get('direccion'), datos.get('telefono'), datos.get('email'), datos.get('idAlumno'))
    elif accion == "eliminar":
        print("Datos recibidos para eliminar:", datos)  # Debug
        id_alumno = datos.get('idAlumno') or datos.get('id_alumno')
        if not id_alumno:
            return {'msg': "error", 'error': "Falta el campo 'idAlumno' para eliminar"}
        sql = "DELETE FROM alumnos WHERE idAlumno=%s"
        valores = (id_alumno,)
        try:
            resultado = db.ejecutar(sql, valores)
            if resultado == 0:
                return {'msg': "error", 'error': "No se encontró el alumno para eliminar"}
            return {'msg': "ok"}
        except Exception as e:
            return {'msg': "error", 'error': f"Error al eliminar: {str(e)}"}
    else:
        raise ValueError("Acción no válida")
    if accion != "eliminar":
        return db.ejecutar(sql, valores)