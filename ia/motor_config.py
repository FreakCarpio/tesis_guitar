"""
Motor Config - Constantes pedagógicas del sistema adaptativo (P1).

TODAS las constantes que gobiernan el comportamiento del sistema de
habilidades y del motor adaptativo v1 viven aquí, en un solo lugar:
- facilita calibrarlas sin tocar la lógica
- hace el motor auditable y defendible (cada decisión usa valores conocidos)

El motor es determinístico y explicable: sin IA generativa.
"""

# ==========================================================================
# HABILIDADES - actualización tras cada práctica
# ==========================================================================

# Peso de cada métrica en el rendimiento de una sesión (suman 1.0).
PESO_PRECISION = 0.6
PESO_CONSISTENCIA = 0.4

# Delta de progreso base por práctica aprobada (a dificultad media y
# rendimiento perfecto): ~7 sesiones buenas por nivel.
DELTA_BASE_APROBADO = 0.15

# Delta cuando NO se aprueba: siempre se avanza algo (motivación), pero poco.
DELTA_BASE_FALLIDO = 0.05

# Las habilidades secundarias del ejercicio reciben esta fracción del delta.
FRACCION_SECUNDARIA = 0.5

# Delta plano de las habilidades transversales (precision / consistencia),
# multiplicado por la métrica correspondiente de la sesión.
DELTA_TRANSVERSAL = 0.05

# Factor por dificultad del ejercicio (1..5): más difícil = más progreso.
def factor_dificultad(dificultad: int) -> float:
    return 0.5 + 0.25 * (max(1, min(5, dificultad)) - 1)   # 0.5 .. 1.5

# Nivel máximo de una habilidad.
NIVEL_MAX = 10

# ==========================================================================
# CONFIANZA - cuánta evidencia real hay del nivel de una habilidad
# ==========================================================================

# Confianza inicial de una habilidad sembrada desde el onboarding
# (nivel declarado, no demostrado).
CONFIANZA_INICIAL_SEMILLA = 0.2

# Incremento de confianza por práctica de esa habilidad.
CONFIANZA_POR_PRACTICA = 0.1

# Decaimiento de confianza por día sin practicar la habilidad.
# Se aplica de forma lazy (calculado al leer, persistido solo al practicar).
DECAIMIENTO_CONFIANZA_DIA = 0.05

# ==========================================================================
# MOTOR ADAPTATIVO v1 - reglas de decisión
# ==========================================================================

# Meta diaria de práctica (minutos). Debe coincidir con META_DIARIA_MIN
# de la app Android.
META_DIARIA_MIN = 15

# Recomendar descanso cuando se practicó >= este múltiplo de la meta diaria.
FACTOR_DESCANSO = 2.0

# Umbrales de rendimiento (promedio de últimos N intentos de la habilidad).
N_INTENTOS_TENDENCIA = 3
UMBRAL_SUBIR_DIFICULTAD = 0.85
UMBRAL_BAJAR_DIFICULTAD = 0.5
CONFIANZA_MIN_PARA_SUBIR = 0.6

# Pesos del puntaje de selección de habilidad débil (regla 6).
W_NIVEL_BAJO = 0.35        # (10 - nivel) / 10
W_CONFIANZA_BAJA = 0.25    # 1 - confianza
W_DIAS_SIN_PRACTICA = 0.2  # min(dias / 7, 1)  -> repetición espaciada
W_PASO_ACTUAL = 0.2        # 1 si la habilidad pertenece al paso actual del camino

# Días para saturar la señal de "días sin práctica".
DIAS_SATURACION_ESPACIADO = 7

# Racha: felicitar en múltiplos de esta cantidad de días.
RACHA_HITO_DIAS = 7
