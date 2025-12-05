import pyodbc

def conectar():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=DESKTOP-IFV9P3G\\SQLEXPRESS;"
            "DATABASE=UROMED;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        print("✅ Conexión exitosa a SQL Server.")
        return conn
    except pyodbc.Error as e:
        print("❌ Error al conectar con SQL Server:")
        print(e)
        return None

# Prueba opcional: solo se ejecuta si corrés este archivo directamente
if __name__ == "__main__":
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 5 * FROM expedientes")
            filas = cursor.fetchall()

            if filas:
                print("📋 Expedientes encontrados:")
                for fila in filas:
                    print(fila)
            else:
                print("⚠️ La tabla 'expedientes' está vacía.")
        except Exception as e:
            print("❌ Error al ejecutar la consulta:")
            print(e)
        finally:
            conn.close()
            print("🔒 Conexión cerrada correctamente.")
