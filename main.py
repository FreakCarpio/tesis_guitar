from fastapi import FastAPI # Importamos FastAPI para crear la API REST del sistema # Importamos FastAPI para crear la API REST del sistema
from domain.modelo import UserProfile # Importamos el perfil del usuario donde se guardan métricas promedio
from ia.modelo_adaptativo import modelo_adaptativo # Importamos el perfil del usuario donde se guardan métricas promedio

app = FastAPI() # Creamos la aplicación FastAPI
model = modelo_adaptativo() #Instancia del modelo adaptativo se usará para actualizar métricas después de cada práctica
profiles = {} # Diccionario en memoria para almacenar perfiles de usuarios clave = user_id, valor = UserProfile

@app.post("/practica") # Endpoint POST para registrar una sesión de práctica
def practice(data: dict):  
    user_id = data["user_id"]# Obtenemos el identificador del usuario desde el JSON recibido

    if user_id not in profiles: # Si el usuario no existe aún, creamos un perfil nuevo
        profiles[user_id] = UserProfile()

    profiles[user_id] = model.update( # Actualizamos el perfil usando el modelo adaptativo # los valores vienen del análisis musical previo (ej. FFT/STFT)
        profiles[user_id],
        data["precision"],
        data["consistencia"],
        data["error"]
    )

    return profiles[user_id] # Regresamos el perfil actualizado como respuesta de la API
