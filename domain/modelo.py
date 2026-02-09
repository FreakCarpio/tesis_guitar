from dataclasses import dataclass
# Importamos el decorador dataclass desde el módulo dataclasses
# Esto nos permite crear clases de datos automáticamente sin escribir
# constructores manuales (__init__), facilitando el manejo de estructuras simples

# @dataclass convierte esta clase en una estructura de datos
# útil para almacenar información del usuario dentro del sistema
# por ejemplo métricas de desempeño musical o resultados del análisis

@dataclass
class UserProfile:
    precision_avg: float = 0.0  
    # Aquí estoy guardando el promedio de precisión del usuario.
    # Esto puede venir de análisis de señales (FFT/STFT) o evaluación de notas.
    # Sirve para medir qué tan exacto es el usuario al tocar o cantar.
    consistencia_avg: float = 0.0  
    # Aquí almaceno el promedio de consistencia del usuario.
    # Esto ayuda a saber si mantiene estabilidad en ritmo, frecuencia
    # o ejecución a lo largo del tiempo.
    error_avg: float = 0.0
    # Aquí guardo el promedio de error detectado.
    # Puede representar desviación de frecuencia, timing incorrecto,
    # o diferencias respecto a la referencia musical esperada.