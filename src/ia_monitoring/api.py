"""
API REST de Inferencia BGG — FastAPI
Expone el motor EngineIABGG para recibir peticiones del simulador bancario.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from zone2.model_isolation import EngineIABGG

app = FastAPI(title="API Biometric Ghost Gate (BGG)")
engine = EngineIABGG()

# Esquema de datos que enviará el simulador bancario
class TelemetriaInput(BaseModel):
    status_code: int = 200
    latency: float
    user_speed: float

@app.post("/api/v1/predict")
def evaluar_peticion(data: TelemetriaInput):
    # Llama a tu función existente en model_isolation.py
    resultado = engine.evaluar_transaccion(
        status_code=data.status_code,
        latency=data.latency,
        user_speed=data.user_speed
    )
    return resultado