import crud_academico

db = crud_academico.crud()

class crud_usuario:
    def consultar(self, buscar):
        if buscar.strip() == "":
            sql = "SELECT * FROM usuarios"
            return db.consultar(sql)
        else:
            if buscar.startswith("idUsuario="):
                id_usuario = buscar.split("=")[1]
                sql = "SELECT * FROM usuarios WHERE idUsuario = %s"
                return db.consultar(sql, (id_usuario,))
            else:
                sql = "SELECT * FROM usuarios WHERE nombre LIKE %s"
                return db.consultar(sql, ("%" + buscar + "%",))

    def administrar(self, datos):
        if datos['accion'] == "nuevo":
            sql = """
                INSERT INTO usuarios (usuario, clave, nombre, direccion, telefono)
                VALUES (%s, %s, %s, %s, %s)
            """
            valores = (datos['usuario'], datos['clave'], datos['nombre'],
                       datos['direccion'], datos['telefono'])
        elif datos['accion'] == "modificar":
            # Si la clave está vacía, no la actualizamos
            if not datos['clave']:
                sql = """
                    UPDATE usuarios SET usuario=%s, nombre=%s,
                    direccion=%s, telefono=%s WHERE idUsuario=%s
                """
                valores = (datos['usuario'], datos['nombre'],
                           datos['direccion'], datos['telefono'], datos['idUsuario'])
            else:
                sql = """
                    UPDATE usuarios SET usuario=%s, clave=%s, nombre=%s,
                    direccion=%s, telefono=%s WHERE idUsuario=%s
                """
                valores = (datos['usuario'], datos['clave'], datos['nombre'],
                           datos['direccion'], datos['telefono'], datos['idUsuario'])
        elif datos['accion'] == "eliminar":
            sql = "DELETE FROM usuarios WHERE idUsuario=%s"
            valores = (datos['idUsuario'],)
        else:
            return "Acción no válida"
        return db.ejecutar(sql, valores)

    def login(self, usuario, clave):
        sql = "SELECT * FROM usuarios WHERE usuario=%s AND clave=%s"
        resultado = db.consultar(sql, (usuario, clave))
        return resultado[0] if resultado else None
