from fastapi import FastAPI
from domain.modelo import UserProfile
from ia.modelo_adaptativo import modelo_adaptativo

app = FastAPI()
model = modelo_adaptativo()
profiles = {}

@app.post("/practica")
def practice(data: dict):
    user_id = data["user_id"]

    if user_id not in profiles:
        profiles[user_id] = UserProfile()

    profiles[user_id] = model.update(
        profiles[user_id],
        data["precision"],
        data["consistencia"],
        data["error"]
    )

    return profiles[user_id]
