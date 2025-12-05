import pyodbc

try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=DESKTOP-IFV9P3G\\SQLEXPRESS;"
        "DATABASE=UROMED;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    print("✅ Conexión exitosa.")
    conn.close()
except Exception as e:
    print("❌ Error:")
    print(e)
