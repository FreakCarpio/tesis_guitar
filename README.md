# 🎸 FretMind Backend (Python + FastAPI)

Backend del sistema de aprendizaje de guitarra acústica asistido por IA (Wilfredo).
Expone una API REST que es consumida por la aplicación móvil desarrollada en Kotlin.

---

## 🧠 Descripción

Este backend implementa:

* Motor inteligente tipo **“Wilfredo”** (sin uso de APIs externas)
* Análisis de práctica musical (ritmo, precisión, BPM)
* Afinador (detección de nota)
* Detección de acordes
* API REST lista para integración con apps móviles

---

## ⚙️ Tecnologías

* Python 3.10+
* FastAPI
* Uvicorn
* Pydantic

---

## 📁 Estructura del proyecto

```
Tesis_app/
│
├── main.py
├── routes/
│   ├── wilfredo_routes.py
│   ├── tuner.py
│
├── services/
│   ├── wilfredo_service.py
│
├── audio/
│   ├── metricas_extractor.py
│
├── venv/ (NO subir a git)
├── requirements.txt
```

---

## 🚀 Instalación (OBLIGATORIO)

### 1. Clonar repositorio

```
git clone <URL_DEL_REPO>
cd Tesis_app
```

---

### 2. Crear entorno virtual

```
python -m venv venv
```

---

### 3. Activar entorno

En Windows:

```
venv\Scripts\activate
```

En Mac/Linux:

```
source venv/bin/activate
```

---

### 4. Instalar dependencias

```
pip install -r requirements.txt
```

---

## ▶️ Ejecutar el servidor

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 Probar API

Abrir en navegador:

```
http://localhost:8000/docs
```

Interfaz interactiva de FastAPI para probar endpoints.

---

## 📡 Endpoints principales

### 🎤 Chat Wilfredo

POST `/wilfredo/chat`

```
{
  "mensaje": "hola",
  "nivel": "principiante"
}
```

---

### 📊 Análisis de práctica

POST `/wilfredo/analyze`

```
{
  "precision": 80,
  "ritmo": 70,
  "bpm": 120
}
```

---

### 🎵 Afinador

POST `/tuner/pitch`

```
{
  "frecuencia": 440.0
}
```

---

### 🎸 Detección de acordes

POST `/tuner/chord`

```
{
  "notas": ["A", "C#", "E"]
}
```

---

## ⚠️ Problemas comunes

### ❌ No abre `/docs`

* Verificar que uvicorn esté corriendo
* Revisar errores en consola
* Confirmar puerto 8000 libre

---

### ❌ Error de imports

* Asegúrate de activar el entorno virtual
* Verifica que instalaste dependencias

---

### ❌ “En mi máquina sí funciona”

Solución:

* Siempre usar entorno virtual
* Nunca subir `venv/`
* Usar `requirements.txt` actualizado:

```
pip freeze > requirements.txt
```

---

## 🔗 Integración con App Móvil (Kotlin)

Este backend está diseñado para ser consumido vía HTTP:

* Base URL:

```
http://<IP_LOCAL>:8000
```

Ejemplo:

```
http://192.168.0.185:8000
```

* Consumo recomendado:

  * Retrofit (Android)
  * o requests HTTP directos

---

## 🧠 Notas de desarrollo

* No se utilizan APIs externas (OpenAI, Gemini, etc.)
* El sistema simula inteligencia mediante reglas estructuradas
* Preparado para futura integración de modelos ML reales

---

## 📌 Estado actual

✔ Backend funcional
✔ API REST estable
✔ Listo para conexión con app móvil
⏳ En evolución (mejoras en análisis y feedback)

---

## 👨‍💻 Autor

Proyecto de tesis – Ingeniería en Sistemas
Sistema de aprendizaje musical asistido por IA
