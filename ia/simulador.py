import random # Importamos random para simular datos de sesiones (valores ficticios de desempeño)
from domain.modelo import UserProfile #Importamos el modelo de datos del usuario aquí se guardan las métricas promedio del perfil
from ia.modelo_adaptativo import modelo_adaptativo #Importamos el modelo adaptativo este se encarga de actualizar los promedios del usuario

model = modelo_adaptativo() # Creamos una instancia del modelo adaptativo
profile = UserProfile() # Creamos un perfil inicial del usuario con valores en cero

for sesion in range(10): # Simulamos 10 sesiones de práctica del usuario
    precision = random.uniform(0.6, 0.9) # Generamos datos simulados de precisión representan resultados obtenidos después del análisis musical
    consistencia = random.uniform(0.5, 0.85) #Generamos datos simulados de consistencia reflejan estabilidad del usuario en la ejecución
    error = random.uniform(0.1, 0.3) #Generamos datos simulados de error indican desviaciones o fallos en la ejecución

    profile = model.update(profile, precision, consistencia, error) #Actualizamos el perfil usando el modelo adaptativo
    print(f"Sesión {sesion + 1}: {profile}") #Mostramos los resultados del perfil después de cada sesión
