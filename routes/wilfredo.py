from fastapi import APIRouter, UploadFile, File
from ia.audio_analisis import analyze_audio
from google import genai
import os

router = APIRouter()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@router.post("/wilfredo")
async def wilfredo(prompt: str):

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return {
        "feedback": response.text
    }