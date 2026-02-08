import random
from domain.modelo import UserProfile
from ia.modelo_adaptativo import modelo_adaptativo

model = modelo_adaptativo()
profile = UserProfile()

for sesion in range(10):
    precision = random.uniform(0.6, 0.9)
    consistencia = random.uniform(0.5, 0.85)
    error = random.uniform(0.1, 0.3)

    profile = model.update(profile, precision, consistencia, error)
    print(f"Sesión {sesion + 1}: {profile}")
