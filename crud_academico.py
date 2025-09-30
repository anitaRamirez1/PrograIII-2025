import mysql.connector
from mysql.connector import Error

class crud:
    def __init__(self):
        print("Conectando a la base de datos...")
        self.conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='db_academica'
        )
        if self.conexion.is_connected():
            print("Conexion exitosa a la base de datos")
        else:
            print("Error al conectar a la base de datos")
        
    def consultar(self, sql):
        cursor = self.conexion.cursor(dictionary=True)
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    
    def ejecutar(self, sql, datos):
        try:
            cursor = self.conexion.cursor()
            print("Ejecutando SQL:", sql)          # Debug: muestra la consulta
            print("Con datos:", datos)              # Debug: muestra los valores
            cursor.execute(sql, datos)
            self.conexion.commit()
            cursor.close()
            return "ok"
        except Error as e:
            print("Error en la consulta:", e)      # Debug: muestra el error
            return str(e)
