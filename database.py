import os
from pymongo import MongoClient

# Carga variables de entorno desde .env (si python-dotenv está instalado).
# Es opcional: si no está, se usa os.getenv con el fallback de abajo.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# URI de conexión a MongoDB Atlas.
# Se lee de la variable de entorno MONGODB_URI; el valor por defecto mantiene
# el entorno actual funcionando si no hay .env configurado.
# IMPORTANTE: la credencial que estuvo commiteada debe rotarse en Atlas.
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://crimsonblood069_db_user:w9K2c3XRUwzDwy1H@cluster0.iokiaz5.mongodb.net/?appName=Cluster0"
)

client = MongoClient(MONGODB_URI)
db = client["Guitarra_app"]

# Colecciones
usuarios = db["usuarios"]
sesiones = db["sesiones"]
progreso = db["progreso"]
estadisticas = db["estadisticas"]
historial = db["historial"]
configuraciones = db["configuraciones"]
calibracion = db["calibracion"]
ejercicios_desbloqueados = db["ejercicios_desbloqueados"]
