class modelo_adaptativo:
# Clase que representa un modelo adaptativo simple
# Sirve para actualizar métricas del usuario usando un promedio exponencial

    def __init__(self, alpha=0.8):# Constructor del modelo
        self.alpha = alpha        # alpha controla cuánto peso tienen los datos anteriores vs los nuevos
    def update(self, profile, precision, consistency, error): # Método que actualiza las métricas del perfil del usuario
        profile.precision_avg = (
            self.alpha * profile.precision_avg + (1 - self.alpha) * precision # Actualiza el promedio de precisión combina valor anterior + nuevo valor medido
        )
        profile.consistency_avg = (  # Actualiza el promedio de consistencia mantiene estabilidad histórica del desempeño
            self.alpha * profile.consistency_avg + (1 - self.alpha) * consistency
        )
        profile.error_avg = ( 
            self.alpha * profile.error_avg + (1 - self.alpha) * error #Actualiza el promedio de error permite seguir la evolución del usuario en fallos o desviaciones
        )
        profile.sessions += 1
        return profile # Regresa el perfil actualizado
