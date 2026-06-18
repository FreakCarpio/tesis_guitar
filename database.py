from pymongo import MongoClient
client = MongoClient(
    "mongodb+srv://crimsonblood069_db_user:w9K2c3XRUwzDwy1H@cluster0.iokiaz5.mongodb.net/?appName=Cluster0"
)
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
