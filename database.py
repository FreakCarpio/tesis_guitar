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
# Se lee EXCLUSIVAMENTE de la variable de entorno MONGODB_URI (Railway / .env).
# Sin valor por defecto: nunca se commitea una credencial en el repositorio.
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError(
        "Falta la variable de entorno MONGODB_URI. "
        "Configúrala en Railway (Variables) o en un archivo .env local."
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

# Colecciones P1 - Sistema adaptativo
habilidades = db["habilidades"]              # estado actual de las 12 habilidades por usuario
habilidad_eventos = db["habilidad_eventos"]  # historial append-only de cambios de habilidad
camino_usuario = db["camino_usuario"]        # posición del usuario en el camino de aprendizaje
recomendaciones = db["recomendaciones"]      # log auditable de decisiones del motor adaptativo

# Motor Cognitivo - memoria conversacional de RIFF (últimos turnos por
# usuario; la usa el proveedor conversacional).
conversaciones = db["conversaciones"]

# Motor Cognitivo - planes diarios/semanales del Recommendation Engine.
# Estables por clave (usuario+fecha / usuario+semana) para no cambiar el
# plan cada vez que se consulta.
planes = db["planes"]

# Motor Cognitivo - hitos detectados por Progress Intelligence
# (logros, evolución, estancamiento, recaídas). Deduplicados por `clave`.
hitos = db["hitos"]

# Motor Cognitivo - perfil dinámico del estudiante (Learning Profile).
# Se reconstruye tras cada práctica (hook best-effort en /practica) y es la
# memoria de largo plazo que alimentan y consultan los módulos cognitivos.
perfil_aprendizaje = db["perfil_aprendizaje"]

# Práctica guiada - registro completo de cada intento de ejercicio
# (ExerciseAttempt: tiempos, pasos ejecutados, puntuación, estrellas,
# precisión/consistencia). Base del futuro motor adaptativo.
intentos_ejercicio = db["intentos_ejercicio"]

# Colecciones Song Detail - proxy de proveedores externos + biblioteca
cancion_cache = db["cancion_cache"]          # detalle compuesto Songsterr+iTunes (TTL en lectura)
busqueda_cache = db["busqueda_cache"]        # resultados de búsqueda Songsterr (TTL en lectura)
biblioteca_usuario = db["biblioteca_usuario"]  # canciones guardadas/favoritas por usuario
letra_cache = db["letra_cache"]              # letras LRCLIB por canción (TTL en lectura)
acordes_cache = db["acordes_cache"]          # hoja de acordes reales Songsterr (TTL en lectura)
