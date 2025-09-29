import crud_academico

db = crud_academico.crud()

class crud_docente:
    def consultar(self, buscar):
        return db.consultar("SELECT * FROM docentes WHERE nombre like '%"+ buscar +"%'")

    def administrar(self, datos):
        if datos['accion']=="nuevo":
            sql = """
                INSERT INTO docentes (codigo, nombre, direccion, telefono, email, dui, escalafon)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores = (datos['codigo'], datos['nombre'], datos['direccion'], datos['telefono'], datos['email'], datos['dui'], datos['escalafon'])
        if datos['accion']=="modificar":
            sql = """
                UPDATE docente SET codigo=%s, nombre=%s, direccion=%s, telefono=%s, email=%s, dui=%s, escalafon=%s
                WHERE idDocente=%s
            """
            valores = (datos['codigo'], datos['nombre'], datos['direccion'], datos['telefono'], datos['email'], datos['dui'], datos['escalafon'], datos['idDocente'])
        if datos['accion']=="eliminar":
            sql = "DELETE FROM docente WHERE idDocente=%s"
            valores = (datos['idDocente'],)
        return db.ejecutar(sql, valores)