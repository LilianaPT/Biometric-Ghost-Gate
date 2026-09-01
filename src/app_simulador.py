"""
╔══════════════════════════════════════════════════════════════════╗
║         BIOMETRIC GHOST GATE (BGG) — AQ Tech                    ║
║         Banking Login Simulator — Backend API                    ║
║         Módulo : src/app_simulador.py                            ║
║         Autor  : AQ Tech Engineering Team                        ║
╚══════════════════════════════════════════════════════════════════╝

Propósito:
    Simulador de backend bancario para entrenamiento de modelos de IA
    (análisis de latencia) y monitoreo de tráfico vía eBPF en Kernel Linux.
"""

import asyncio
import logging
import os
import random
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME        = "BGG Banking Simulator"
APP_VERSION     = "1.9.0"
APP_DESCRIPTION = "Sandbox de simulación de login bancario — Proyecto Biometric Ghost Gate"

LOG_DIR         = "logs/active"
LOG_FILE        = os.path.join(LOG_DIR, "bgg_operativo.log")

# Rango de latencia simulada (segundos) para análisis de IA
LATENCY_MIN_SEC = 0.1
LATENCY_MAX_SEC = 1.5

# ── user_speed: tiempo simulado que tarda un usuario en rellenar el formulario
# Escenario B (Sandbox): valor aleatorio que simula comportamiento humano real.
# Escenario A (Producción futura): vendrá del payload del frontend.
# Rango típico humano: 2s (usuario experto) a 15s (usuario lento/distraído)
USER_SPEED_MIN_SEC = 2.0
USER_SPEED_MAX_SEC = 15.0

# ─────────────────────────────────────────────────────────────────────────────
# API DE IA (Angela) — Servicio externo de detección de bots
# ─────────────────────────────────────────────────────────────────────────────

# URL del servicio de Angela (api.py, endpoint POST /api/v1/predict).
# Puede sobreescribirse con la variable de entorno AI_API_URL sin tocar
# código — útil porque el servicio de Angela puede correr en otro puerto
# de la misma VM, o en otra máquina/túnel de ngrok por separado.
AI_API_URL = os.environ.get("AI_API_URL", "http://localhost:9000/api/v1/predict")

# Tiempo máximo de espera a la API de Angela antes de seguir sin bloquear
# el login del usuario — nunca debe tumbar el banco por un servicio externo lento
AI_API_TIMEOUT_SECONDS = 6.0  # más holgado: la 1a llamada puede disparar el entrenamiento automático de Angela

# Umbral de confianza para considerar una petición como sospechosa, usado
# solo si la respuesta de Angela trae un score/probabilidad numérico en
# lugar de un booleano directo (ver interpret_ai_result más abajo).
AI_SUSPICION_THRESHOLD = 0.75

# Duración del cierre automático de sesión — tanto para el intento humano
# legítimo como para el bot, sobre la misma cuenta. Se levanta solo, sin
# que nadie tenga que desbloquear nada.
AUTO_CLOSE_SECONDS = 5 * 60  # 5 minutos

# Webhook opcional para avisar a los administradores en Discord cuando se
# detecta un bot (Configuración → Integraciones → Webhooks en el canal).
# Si no se configura, el aviso solo queda en el log y en /api/v1/alerts.
ADMIN_DISCORD_WEBHOOK = os.environ.get("ADMIN_DISCORD_WEBHOOK", "")

# ─────────────────────────────────────────────────────────────────────────────
# DATOS MOCK — Credenciales bancarias simuladas
# En un entorno real estos vendrían de un HSM / base de datos cifrada.
# ─────────────────────────────────────────────────────────────────────────────

MOCK_USERS: dict[str, dict[str, Any]] = {
    "cliente_001": {
        "password"    : "Banco$ecure#2024",
        "full_name"   : "Ana García López",
        "account_type": "PREMIUM",
        "account_id"  : "MX-4821-0001",
    },
    "cliente_002": {
        "password"    : "P@ssw0rd_BGG",
        "full_name"   : "Carlos Mendoza Ruiz",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0002",
    },
    "admin_bgg": {
        "password"    : "BGG_AdmIn!2024",
        "full_name"   : "AQ Tech Admin",
        "account_type": "ADMIN",
        "account_id"  : "MX-0000-ADMIN",
    },
    "cliente_003": {
        "password"    : "Sof1a#Segura25",
        "full_name"   : "Sofía Ramírez Torres",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0003",
    },
    "cliente_004": {
        "password"    : "Javi3r$Bank99",
        "full_name"   : "Javier Ortega Salas",
        "account_type": "PREMIUM",
        "account_id"  : "MX-4821-0004",
    },
    "cliente_005": {
        "password"    : "Luc1a_Clave#7",
        "full_name"   : "Lucía Fernández Vega",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0005",
    },
    "cliente_006": {
        "password"    : "Dani3l#Pass456",
        "full_name"   : "Daniel Herrera Cruz",
        "account_type": "PREMIUM",
        "account_id"  : "MX-4821-0006",
    },
    "cliente_007": {
        "password"    : "Valen#Banco88",
        "full_name"   : "Valentina Castro Rojas",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0007",
    },
    "cliente_008": {
        "password"    : "Mig3l$Segur0!",
        "full_name"   : "Miguel Ángel Domínguez",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0008",
    },
    "cliente_009": {
        "password"    : "Camil4#Vault22",
        "full_name"   : "Camila Jiménez Paredes",
        "account_type": "PREMIUM",
        "account_id"  : "MX-4821-0009",
    },
    "cliente_010": {
        "password"    : "Rod0lfo$Key33",
        "full_name"   : "Rodolfo Aguilar Peña",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0010",
    },
    "cliente_011": {
        "password"    : "Isa4b3l#Pin09",
        "full_name"   : "Isabel Navarro Solís",
        "account_type": "STANDARD",
        "account_id"  : "MX-4821-0011",
    },
    "cliente_012": {
        "password"    : "Emili0$Token71",
        "full_name"   : "Emilio Ríos Bautista",
        "account_type": "PREMIUM",
        "account_id"  : "MX-4821-0012",
    },
    "soporte_bgg": {
        "password"    : "Soport3#BGG2024",
        "full_name"   : "AQ Tech Soporte",
        "account_type": "SUPPORT",
        "account_id"  : "MX-0000-SOPORTE",
    },
    "auditor_bgg": {
        "password"    : "Audit0r$Ghost1",
        "full_name"   : "AQ Tech Auditoría",
        "account_type": "AUDITOR",
        "account_id"  : "MX-0000-AUDITOR",
    },
}

# Cuentas destino válidas para simular transferencias (mock)
# Incluye las cuentas de todos los usuarios de MOCK_USERS + 3 cuentas externas
MOCK_DESTINATION_ACCOUNTS: set[str] = {
    user["account_id"] for user in MOCK_USERS.values()
} | {
    "MX-9012-3344", "MX-9012-3355", "MX-9012-3366",  # externas (no login)
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """
    Inicializa el sistema de logging con salida dual:
    - Archivo  : logs/active/bgg_operativo.log  (para Housekeeping y eBPF)
    - Consola  : stdout  (para Docker logs / monitoreo en vivo)

    Formato de línea de log:
        TIMESTAMP_UTC | LEVEL    | MENSAJE
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_format = "%(asctime)s UTC | %(levelname)-8s | %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"

    logger = logging.getLogger("bgg_simulador")
    logger.setLevel(logging.INFO)

    # ── Handler: archivo rotativo ──────────────────────────────────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # ── Handler: consola ──────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # Usar UTC explícitamente en todos los registros
    logging.Formatter.converter = time.gmtime

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()

# ─────────────────────────────────────────────────────────────────────────────
# CLIENTE HTTP HACIA LA API DE IA DE ANGELA (servicio externo, api.py)
# ─────────────────────────────────────────────────────────────────────────────

ai_api_status = "sin_verificar"   # sin_verificar | activo | inalcanzable


def interpret_ai_result(resultado: dict) -> dict:
    """
    Interpreta la respuesta real de engine.evaluar_transaccion()
    (confirmada en model_isolation.py — Isolation Forest de Angela):

        {
          "resultado": "ANOMALIA_DETECTADA_BLOQUEAR" | "APROBADO_CON_ALTA_LATENCIA" | "ACCESO_NORMAL_VALIDADO",
          "bloquear": bool,          <- señal principal, ya viene decidida
          "codigo_http": int,
          "mensaje": str,            <- texto humano, útil para el aviso
          "anomaly_score": float,    <- score crudo de Isolation Forest
        }

    Se queda con "bloquear" como fuente de verdad (así Angela puede seguir
    ajustando sus reglas internas — ej. el umbral de user_speed < 0.15s —
    sin que este backend tenga que cambiar). Si algún día el formato
    cambia o el campo no viene, no se actúa (nunca cierra sesiones por
    un parseo equivocado).
    """
    if not isinstance(resultado, dict) or "bloquear" not in resultado:
        return {"is_bot": False, "score": None, "mensaje": None, "raw": resultado, "reconocido": False}

    return {
        "is_bot":  bool(resultado["bloquear"]),
        "score":   resultado.get("anomaly_score"),
        "mensaje": resultado.get("mensaje"),
        "raw":     resultado,
        "reconocido": True,
    }


async def assess_request(user_speed: float, network_delay: float, has_geolocation: bool) -> dict:
    """
    Llama a la API externa de Angela (POST /api/v1/predict) para clasificar
    el intento actual. Si el servicio no responde a tiempo o falla, el login
    sigue su curso normal sin bloquear nada — nunca se tumba el banco por
    un servicio de IA externo caído.

    IMPORTANTE — conversión de unidades: el modelo de Angela se entrenó con
    latencia en MILISEGUNDOS (su regla "latency > 1000.0" solo tiene sentido
    en ms) mientras que nuestro network_delay interno está en SEGUNDOS
    (0.1–1.5s). Hay que convertir antes de mandarlo o sus reglas nunca se
    activan correctamente.
    """
    global ai_api_status

    payload = {
        "status_code": 200,
        "latency": round(network_delay * 1000, 2),   # segundos → milisegundos
        "user_speed": user_speed,                     # ya está en segundos, igual que ella lo espera
    }

    try:
        async with httpx.AsyncClient(timeout=AI_API_TIMEOUT_SECONDS) as client:
            response = await client.post(AI_API_URL, json=payload)
            response.raise_for_status()
            resultado = response.json()
        ai_api_status = "activo"
        return interpret_ai_result(resultado)
    except Exception as e:
        ai_api_status = "inalcanzable"
        logger.warning(f"AI_API   | No se pudo contactar la API de Angela ({AI_API_URL}): {e}")
        return {"is_bot": False, "score": None, "mensaje": None, "raw": None, "reconocido": False}


# ─────────────────────────────────────────────────────────────────────────────
# CIERRE AUTOMÁTICO DE SESIÓN (5 min) + AVISO A ADMINISTRADORES
# ─────────────────────────────────────────────────────────────────────────────
# Ya no hay bloqueo indefinido ni decisión humana para desbloquear: al
# detectar un bot, la cuenta se cierra sola por 5 minutos (afecta tanto al
# intento humano legítimo como al del bot, porque ambos comparten la misma
# cuenta) y se manda un aviso. Pasado el tiempo, se reabre sin que nadie
# tenga que hacer nada.

closed_accounts: dict[str, float] = {}   # {account_id: se_reabre_en (epoch)}
pending_alerts: list[dict] = []           # historial de avisos ya enviados


def is_account_closed(account_id: str) -> bool:
    reabre_en = closed_accounts.get(account_id)
    if reabre_en is None:
        return False
    if time.time() >= reabre_en:
        del closed_accounts[account_id]
        return False
    return True


async def notify_admins(alerta: dict):
    """
    Aviso a los administradores. Siempre queda en el log y en
    /api/v1/alerts; si configuran ADMIN_DISCORD_WEBHOOK también se manda
    un mensaje al canal de Discord del equipo.
    """
    logger.warning(
        f"AI_ALERT | ¡BOT DETECTADO! account={alerta['account_id']:<15} "
        f"user={alerta['username']:<20} anomaly_score={alerta['score']} "
        f"mensaje_ia=\"{alerta['mensaje']}\" "
        f"sesión cerrada {AUTO_CLOSE_SECONDS // 60} min — aviso enviado a administradores"
    )

    if not ADMIN_DISCORD_WEBHOOK:
        return

    mensaje = (
        f"🚨 **Bot detectado en BGG**\n"
        f"Cuenta: `{alerta['account_id']}` (usuario: `{alerta['username']}`)\n"
        f"{alerta['mensaje'] or 'Anomalía detectada por el modelo de Angela'}\n"
        f"Anomaly score: `{alerta['score']}`\n"
        f"Sesión cerrada por {AUTO_CLOSE_SECONDS // 60} minutos (se reabre sola).\n"
        f"Hora: {alerta['timestamp']}"
    )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(ADMIN_DISCORD_WEBHOOK, json={"content": mensaje})
    except Exception as e:
        logger.warning(f"AI_ALERT | No se pudo enviar el aviso a Discord: {e}")


async def close_session_and_notify(account_id: str, username: str, score, mensaje: str | None = None) -> dict:
    """
    Ejecuta el cierre automático de 5 minutos y dispara el aviso a
    administradores. Retorna la alerta generada.
    """
    reabre_en = time.time() + AUTO_CLOSE_SECONDS
    closed_accounts[account_id] = reabre_en

    alerta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "username": username,
        "score": score,
        "mensaje": mensaje,
        "reabre_en": datetime.fromtimestamp(reabre_en, tz=timezone.utc).isoformat(),
    }
    pending_alerts.append(alerta)
    await notify_admins(alerta)
    return alerta

# ─────────────────────────────────────────────────────────────────────────────
# CICLO DE VIDA DE LA APLICACIÓN (Lifespan)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de startup y shutdown del servidor."""
    logger.info("=" * 70)
    logger.info(f"STARTUP  | {APP_NAME} v{APP_VERSION} iniciando...")
    logger.info(f"STARTUP  | Log operativo: {os.path.abspath(LOG_FILE)}")
    logger.info(f"STARTUP  | Latencia simulada : {LATENCY_MIN_SEC}s – {LATENCY_MAX_SEC}s")
    logger.info(f"STARTUP  | User speed (mock) : {USER_SPEED_MIN_SEC}s – {USER_SPEED_MAX_SEC}s [Escenario B]")
    logger.info(f"STARTUP  | Frontend Web        : http://0.0.0.0:8000/app/  (compartir vía ngrok como <URL>/app/)")
    logger.info(f"STARTUP  | API de IA (Angela) configurada en: {AI_API_URL}")
    logger.info("=" * 70)
    yield
    logger.info("=" * 70)
    logger.info(f"SHUTDOWN | {APP_NAME} detenido correctamente.")
    logger.info("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# INSTANCIA FASTAPI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = APP_NAME,
    description = APP_DESCRIPTION,
    version     = APP_VERSION,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS — Necesario para que el Frontend Web (App de Simulación) y el Bot
# Simulator puedan llamar a este backend desde el navegador / otra máquina.
# Abierto en el Sandbox; restringir a orígenes específicos en producción.
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = False,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND WEB — Sirve frontend/index.html directamente desde el backend.
# Así el equipo entra con un solo link (el mismo de ngrok) sin necesidad
# de descargar ni clonar el repositorio: <URL_BACKEND>/app/
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_DIR = "frontend"

if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logging.getLogger("bgg_simulador").warning(
        f"STARTUP  | Carpeta '{FRONTEND_DIR}/' no encontrada — /app no estará disponible."
    )

# ─────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE — Registro de peticiones (REQUEST LOGGER)
# ─────────────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def request_logger_middleware(request: Request, call_next):
    """
    Intercepta TODAS las peticiones HTTP y registra en bgg_operativo.log:
        METHOD | ENDPOINT | STATUS_CODE | LATENCY_MS
    El campo user_speed se loggea dentro del endpoint de login.
    """
    ts_inicio = time.monotonic()

    response = await call_next(request)

    latencia_ms = (time.monotonic() - ts_inicio) * 1000
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    logger.info(
        f"REQUEST  | method={request.method:<6} "
        f"endpoint={request.url.path:<35} "
        f"status={response.status_code} "
        f"latency={latencia_ms:>8.2f}ms"
    )

    return response


# ─────────────────────────────────────────────────────────────────────────────
# MODELOS PYDANTIC
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Payload de solicitud de autenticación bancaria."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Nombre de usuario del cliente bancario",
        examples=["cliente_001"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Contraseña del cliente bancario",
        examples=["Banco$ecure#2024"],
    )
    user_speed: float | None = Field(
        default=None,
        ge=0,
        le=300,
        description=(
            "Tiempo real (segundos) medido en el navegador desde que se "
            "mostró el formulario hasta que se envió. Escenario A. "
            "Si se omite, el backend lo simula (Escenario B — bots/pruebas)."
        ),
        examples=[4.87],
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitud capturada por el navegador (geolocalización del cliente). Opcional.",
        examples=[19.4326],
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitud capturada por el navegador (geolocalización del cliente). Opcional.",
        examples=[-99.1332],
    )


class TransactionRequest(BaseModel):
    """Payload de solicitud de transferencia bancaria simulada."""
    account_id: str = Field(
        ...,
        description="Cuenta origen (obtenida al hacer login)",
        examples=["MX-4821-0001"],
    )
    destination_account: str = Field(
        ...,
        description="Cuenta destino de la transferencia",
        examples=["MX-9012-3344"],
    )
    amount: float = Field(
        ...,
        gt=0,
        le=1_000_000,
        description="Monto a transferir (MXN)",
        examples=[1500.00],
    )
    user_speed: float | None = Field(
        default=None,
        ge=0,
        le=300,
        description="Tiempo real (segundos) que tardó en llenar el formulario de transacción.",
        examples=[6.12],
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitud capturada por el navegador (geolocalización del cliente). Opcional.",
        examples=[19.4326],
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitud capturada por el navegador (geolocalización del cliente). Opcional.",
        examples=[-99.1332],
    )


class LoginSuccessResponse(BaseModel):
    """Respuesta exitosa tras autenticación."""
    status      : str
    message     : str
    token       : str
    account_id  : str
    account_type: str
    full_name   : str
    issued_at   : str


class LoginFailResponse(BaseModel):
    """Respuesta ante credenciales inválidas."""
    status : str
    message: str
    code   : str


class TransactionSuccessResponse(BaseModel):
    """Respuesta exitosa tras una transferencia simulada."""
    status              : str
    message             : str
    transaction_id      : str
    account_id          : str
    destination_account : str
    amount              : float
    processed_at        : str


class TransactionFailResponse(BaseModel):
    """Respuesta ante una transferencia inválida."""
    status : str
    message: str
    code   : str


class AccountActivityItem(BaseModel):
    """Un evento individual en el historial de actividad de una cuenta."""
    timestamp   : str
    event       : str            # AUTH_OK | AUTH_FAIL | TXN_OK | TXN_FAIL
    detail      : str            # descripción legible del evento
    source_type : str            # human | simulated
    user_speed  : float | None = None
    latitude    : float | None = None
    longitude   : float | None = None


class AccountActivityResponse(BaseModel):
    """Historial de actividad reciente de una cuenta bancaria."""
    account_id : str
    count      : int
    activity   : list[AccountActivityItem]


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""
    status     : str
    service    : str
    version    : str
    timestamp  : str
    environment: str


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def generate_mock_token(username: str) -> str:
    """
    Genera un token simulado (no es JWT real, es mock para sandbox).
    Formato: BGG-<HEX_TIMESTAMP>-<HEX_RANDOM>-<USERNAME_HASH>
    """
    ts_hex   = format(int(time.time()), "x").upper()
    rnd_hex  = format(random.randint(0x100000, 0xFFFFFF), "x").upper()
    usr_hash = format(hash(username) & 0xFFFF, "04x").upper()
    return f"BGG-{ts_hex}-{rnd_hex}-{usr_hash}"


def generate_mock_transaction_id() -> str:
    """
    Genera un ID de transacción simulado.
    Formato: TXN-<HEX_TIMESTAMP>-<HEX_RANDOM>
    """
    ts_hex  = format(int(time.time()), "x").upper()
    rnd_hex = format(random.randint(0x100000, 0xFFFFFF), "x").upper()
    return f"TXN-{ts_hex}-{rnd_hex}"


async def simulate_network_latency() -> float:
    """
    Introduce un retraso aleatorio para simular condiciones reales de red.
    Rango: LATENCY_MIN_SEC – LATENCY_MAX_SEC segundos.
    Retorna el tiempo de delay aplicado (para logging interno).
    """
    delay = random.uniform(LATENCY_MIN_SEC, LATENCY_MAX_SEC)
    await asyncio.sleep(delay)
    return delay


def simulate_user_speed() -> float:
    """
    Simula el tiempo que un usuario humano tarda en rellenar el formulario
    de login antes de presionar el botón (Escenario B — Sandbox).

    Distribución: uniforme entre USER_SPEED_MIN_SEC y USER_SPEED_MAX_SEC.

    Escenario A (producción futura): este valor vendrá del payload del
    frontend como campo 'user_speed' y se eliminará esta función.

    Retorna el tiempo simulado en segundos (float con 2 decimales).
    """
    return round(random.uniform(USER_SPEED_MIN_SEC, USER_SPEED_MAX_SEC), 2)


def format_geo_log(latitude: float | None, longitude: float | None) -> str:
    """
    Formatea la geolocalización (si viene del navegador) para agregarla
    al final de la línea de log. Si no viene (bots, navegadores sin
    permiso de ubicación, etc.), no agrega nada — el campo es opcional.
    """
    if latitude is None or longitude is None:
        return ""
    return f"geo_lat={latitude:.5f} geo_lon={longitude:.5f}"


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/",
    response_model=HealthResponse,
    summary="Healthcheck del sistema",
    tags=["Sistema"],
)
async def healthcheck():
    """
    ## Endpoint de salud del servidor BGG Simulator.

    Retorna el estado operativo del servicio, útil para:
    - Orquestadores (Docker / Kubernetes)
    - Monitoreo externo (Prometheus, Grafana)
    - Scripts de Housekeeping del equipo de Seguridad
    """
    return HealthResponse(
        status      = "operational",
        service     = APP_NAME,
        version     = APP_VERSION,
        timestamp   = datetime.now(timezone.utc).isoformat(),
        environment = "sandbox",
    )


@app.post(
    "/api/v1/auth/login",
    summary="Simulación de Login Bancario",
    tags=["Autenticación"],
    responses={
        200: {"description": "Autenticación exitosa", "model": LoginSuccessResponse},
        401: {"description": "Credenciales inválidas",  "model": LoginFailResponse},
        422: {"description": "Payload malformado"},
    },
)
async def banking_login(payload: LoginRequest):
    """
    ## Simulador de autenticación bancaria.

    **Flujo:**
    1. Recibe `username` y `password` en el body JSON.
    2. Introduce un **delay aleatorio** (0.1 – 1.5 s) para simular latencia de red.
    3. Si la cuenta tiene un cierre automático activo (bot detectado hace
       poco), rechaza con `423 Locked` — afecta tanto al intento humano
       legítimo como al del bot, ya que comparten la misma cuenta.
    4. La API de Angela (servicio externo) clasifica el intento en tiempo
       real. Si detecta un bot, cierra la sesión de la cuenta por 5 minutos
       (se reabre sola, sin intervención humana) y avisa a los administradores.
    5. Valida contra el dataset mock de usuarios.
    6. Retorna `200 OK` con token simulado si las credenciales son correctas.
    7. Retorna `401 Unauthorized` si las credenciales son incorrectas.

    **Usuarios de prueba disponibles (15 en total):**
    Ver tabla completa en README.md → sección "Usuarios Mock".
    Ejemplos: `cliente_001` / `Banco$ecure#2024` · `admin_bgg` / `BGG_AdmIn!2024`
    """
    # ── Simular latencia de red (crucial para el dataset de IA) ───────────
    delay_aplicado = await simulate_network_latency()

    # ── user_speed: Escenario A (real, del navegador) o Escenario B (simulado)
    if payload.user_speed is not None:
        user_speed  = payload.user_speed
        source_type = "human"       # vino del Frontend Web con medición real
    else:
        user_speed  = simulate_user_speed()
        source_type = "simulated"   # vino de un bot/script sin medir tiempo real

    logger.info(
        f"AUTH     | user={payload.username:<20} "
        f"network_delay={delay_aplicado:.4f}s "
        f"user_speed={user_speed:.2f}s "
        f"source_type={source_type} "
        f"{format_geo_log(payload.latitude, payload.longitude)}"
    )

    user_data = MOCK_USERS.get(payload.username)

    # ── Cierre automático activo — rechaza incluso con contraseña correcta ──
    if user_data is not None and is_account_closed(user_data["account_id"]):
        logger.warning(
            f"AUTH_CLOSED| user={payload.username:<20} account={user_data['account_id']} "
            f"reason=auto_close_active"
        )
        raise HTTPException(
            status_code=423,
            detail={
                "status": "error",
                "message": "Sesión cerrada temporalmente por seguridad. Vuelve a intentar en unos minutos.",
                "code": "AI_SESSION_AUTO_CLOSED",
            },
        )

    # ── Clasificación en tiempo real con la API de Angela ───────────────
    has_geo = payload.latitude is not None and payload.longitude is not None
    ai_result = await assess_request(user_speed, delay_aplicado, has_geo)

    logger.info(
        f"AI_PREDICT | user={payload.username:<20} "
        f"is_bot={ai_result['is_bot']} score={ai_result['score']} "
        f"mensaje_ia=\"{ai_result['mensaje']}\" "
        f"formato_reconocido={ai_result['reconocido']}"
    )

    if ai_result["is_bot"] and user_data is not None:
        await close_session_and_notify(
            account_id = user_data["account_id"],
            username   = payload.username,
            score      = ai_result["score"],
            mensaje    = ai_result["mensaje"],
        )
        raise HTTPException(
            status_code=423,
            detail={
                "status": "error",
                "message": f"Bot detectado. Sesión cerrada por {AUTO_CLOSE_SECONDS // 60} minutos y se avisó a los administradores.",
                "code": "AI_BOT_DETECTED",
                "score": ai_result["score"],
            },
        )

    # ── Validación mock de credenciales ───────────────────────────────────
    # Usuario no existe O contraseña incorrecta (mismo mensaje: evita user enumeration)
    if user_data is None or user_data["password"] != payload.password:
        logger.warning(
            f"AUTH_FAIL| user={payload.username:<20} "
            f"reason=invalid_credentials "
            f"user_speed={user_speed:.2f}s "
            f"source_type={source_type} "
            f"ai_score={ai_result['score']} "
            f"{format_geo_log(payload.latitude, payload.longitude)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LoginFailResponse(
                status  = "error",
                message = "Credenciales inválidas. Verifique usuario y contraseña.",
                code    = "AUTH_INVALID_CREDENTIALS",
            ).model_dump(),
        )

    # ── Autenticación exitosa ─────────────────────────────────────────────
    token     = generate_mock_token(payload.username)
    issued_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"AUTH_OK  | user={payload.username:<20} "
        f"account={user_data['account_id']} "
        f"type={user_data['account_type']} "
        f"user_speed={user_speed:.2f}s "
        f"source_type={source_type} "
        f"ai_score={ai_result['score']} "
        f"{format_geo_log(payload.latitude, payload.longitude)}"
    )

    return LoginSuccessResponse(
        status       = "success",
        message      = "Autenticación bancaria exitosa.",
        token        = token,
        account_id   = user_data["account_id"],
        account_type = user_data["account_type"],
        full_name    = user_data["full_name"],
        issued_at    = issued_at,
    )


@app.post(
    "/api/v1/transactions/transfer",
    summary="Simulación de Transferencia Bancaria",
    tags=["Transacciones"],
    responses={
        200: {"description": "Transferencia exitosa", "model": TransactionSuccessResponse},
        400: {"description": "Transferencia inválida",  "model": TransactionFailResponse},
        422: {"description": "Payload malformado"},
    },
)
async def bank_transfer(payload: TransactionRequest):
    """
    ## Simulador de transferencia bancaria (post-login).

    Igual que el login, mide `user_speed` (Escenario A si viene del
    Frontend Web con medición real, Escenario B/simulado si no).

    También pasa por la misma clasificación de IA que el login: si la
    cuenta está cerrada temporalmente, o si la API de Angela marca esta
    transferencia como sospechosa, se rechaza con `423` y se dispara el
    mismo cierre de 5 minutos + aviso a administradores.

    **Cuentas destino válidas (mock):**
    `MX-4821-0001`, `MX-4821-0002`, `MX-0000-ADMIN`,
    `MX-9012-3344`, `MX-9012-3355`, `MX-9012-3366`
    """
    delay_aplicado = await simulate_network_latency()

    if payload.user_speed is not None:
        user_speed  = payload.user_speed
        source_type = "human"
    else:
        user_speed  = simulate_user_speed()
        source_type = "simulated"

    logger.info(
        f"TXN      | account={payload.account_id:<15} "
        f"destination={payload.destination_account:<15} "
        f"amount={payload.amount:>10.2f} "
        f"network_delay={delay_aplicado:.4f}s "
        f"user_speed={user_speed:.2f}s "
        f"source_type={source_type} "
        f"{format_geo_log(payload.latitude, payload.longitude)}"
    )

    # ── Cierre automático activo — rechaza incluso si los datos son válidos ──
    if is_account_closed(payload.account_id):
        logger.warning(
            f"TXN_CLOSED| account={payload.account_id:<15} reason=auto_close_active"
        )
        raise HTTPException(
            status_code=423,
            detail={
                "status": "error",
                "message": "Sesión cerrada temporalmente por seguridad. Vuelve a intentar en unos minutos.",
                "code": "AI_SESSION_AUTO_CLOSED",
            },
        )

    # ── Clasificación en tiempo real con la API de Angela ───────────────
    has_geo = payload.latitude is not None and payload.longitude is not None
    ai_result = await assess_request(user_speed, delay_aplicado, has_geo)

    logger.info(
        f"AI_PREDICT | account={payload.account_id:<15} "
        f"is_bot={ai_result['is_bot']} score={ai_result['score']} "
        f"mensaje_ia=\"{ai_result['mensaje']}\" "
        f"formato_reconocido={ai_result['reconocido']}"
    )

    if ai_result["is_bot"]:
        await close_session_and_notify(
            account_id = payload.account_id,
            username   = payload.account_id,   # las transferencias no traen username, se usa la cuenta
            score      = ai_result["score"],
            mensaje    = ai_result["mensaje"],
        )
        raise HTTPException(
            status_code=423,
            detail={
                "status": "error",
                "message": f"Bot detectado. Sesión cerrada por {AUTO_CLOSE_SECONDS // 60} minutos y se avisó a los administradores.",
                "code": "AI_BOT_DETECTED",
                "score": ai_result["score"],
            },
        )

    # ── Validación mock de cuenta destino ──────────────────────────────────
    if payload.destination_account not in MOCK_DESTINATION_ACCOUNTS:
        logger.warning(
            f"TXN_FAIL | account={payload.account_id:<15} "
            f"reason=invalid_destination "
            f"user_speed={user_speed:.2f}s "
            f"source_type={source_type} "
            f"{format_geo_log(payload.latitude, payload.longitude)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=TransactionFailResponse(
                status  = "error",
                message = "Cuenta destino inválida.",
                code    = "TXN_INVALID_DESTINATION",
            ).model_dump(),
        )

    transaction_id = generate_mock_transaction_id()
    processed_at   = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"TXN_OK   | account={payload.account_id:<15} "
        f"destination={payload.destination_account:<15} "
        f"amount={payload.amount:>10.2f} "
        f"user_speed={user_speed:.2f}s "
        f"source_type={source_type} "
        f"{format_geo_log(payload.latitude, payload.longitude)}"
    )

    return TransactionSuccessResponse(
        status              = "success",
        message             = "Transferencia procesada exitosamente.",
        transaction_id      = transaction_id,
        account_id          = payload.account_id,
        destination_account = payload.destination_account,
        amount              = payload.amount,
        processed_at        = processed_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PARSEO DEL LOG — Utilidad para reconstruir actividad por cuenta
# ─────────────────────────────────────────────────────────────────────────────

# Ejemplo de línea real generada por el logger:
# 2026-08-07T16:52:00 UTC | INFO     | AUTH_OK  | user=cliente_001 account=MX-4821-0001 type=PREMIUM user_speed=7.43s source_type=human
LOG_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\S+) UTC \| \S+\s*\| (?P<event>AUTH_OK|AUTH_FAIL|TXN_OK|TXN_FAIL)\s*\|\s*(?P<rest>.+)$"
)


def parse_account_activity(account_id: str, limit: int = 20) -> list[AccountActivityItem]:
    """
    Lee bgg_operativo.log de atrás hacia adelante y devuelve los eventos
    (login y transacciones) donde la cuenta indicada participó, ya sea
    como cuenta propia (account=) o como destino de una transferencia
    (destination=).
    """
    if not os.path.exists(LOG_FILE):
        return []

    resultados: list[AccountActivityItem] = []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    for linea in reversed(lineas):
        if len(resultados) >= limit:
            break

        match = LOG_LINE_PATTERN.match(linea.strip())
        if not match:
            continue

        event = match.group("event")
        rest  = match.group("rest")

        # Solo nos interesan líneas donde aparezca esta cuenta,
        # ya sea como cuenta propia o como destino de una transferencia.
        if f"account={account_id}" not in rest and f"destination={account_id}" not in rest:
            continue

        source_type_match = re.search(r"source_type=(\S+)", rest)
        user_speed_match  = re.search(r"user_speed=([\d.]+)s", rest)
        amount_match      = re.search(r"amount=\s*([\d.]+)", rest)
        destination_match = re.search(r"destination=(\S+)", rest)
        geo_lat_match     = re.search(r"geo_lat=(-?[\d.]+)", rest)
        geo_lon_match     = re.search(r"geo_lon=(-?[\d.]+)", rest)

        source_type = source_type_match.group(1) if source_type_match else "unknown"
        user_speed  = float(user_speed_match.group(1)) if user_speed_match else None
        latitude    = float(geo_lat_match.group(1)) if geo_lat_match else None
        longitude   = float(geo_lon_match.group(1)) if geo_lon_match else None

        # Descripción legible según el tipo de evento
        if event == "AUTH_OK":
            detail = "Inicio de sesión exitoso"
        elif event == "AUTH_FAIL":
            detail = "Intento de inicio de sesión fallido"
        elif event == "TXN_OK":
            monto = amount_match.group(1) if amount_match else "?"
            dest  = destination_match.group(1) if destination_match else "?"
            detail = f"Transferencia enviada: ${monto} → {dest}"
        else:  # TXN_FAIL
            detail = "Transferencia rechazada"

        resultados.append(AccountActivityItem(
            timestamp   = match.group("timestamp"),
            event       = event,
            detail      = detail,
            source_type = source_type,
            user_speed  = user_speed,
            latitude    = latitude,
            longitude   = longitude,
        ))

    return resultados


@app.get(
    "/api/v1/accounts/{account_id}/activity",
    response_model=AccountActivityResponse,
    summary="Historial de actividad de una cuenta",
    tags=["Cuentas"],
)
async def account_activity(account_id: str, limit: int = 20):
    """
    ## Historial de actividad reciente de una cuenta bancaria.

    Lee `bgg_operativo.log` y devuelve los últimos eventos (logins y
    transferencias, exitosos o fallidos) donde la cuenta indicada
    participó — ya sea como titular o como cuenta destino.

    Cada evento incluye `source_type` (`human` o `simulated`), así el
    Frontend puede mostrar si una transacción vino de una persona real
    o de un script/bot — justo lo que se necesita para ver, al iniciar
    sesión, si el bot usó esta misma cuenta anteriormente.

    **Parámetros:**
    - `account_id`: cuenta a consultar (ej. `MX-4821-0001`)
    - `limit`: máximo de eventos a devolver (default 20)
    """
    eventos = parse_account_activity(account_id, limit=limit)
    return AccountActivityResponse(
        account_id = account_id,
        count      = len(eventos),
        activity   = eventos,
    )


@app.get(
    "/api/v1/ai/status",
    summary="Estado de la API de IA (Angela)",
    tags=["IA"],
)
async def ai_status():
    """
    Confirma si la API de Angela (servicio externo, api.py) respondió
    correctamente la última vez que se le llamó. Útil para verificar la
    conexión sin tener que hacer un login completo.
    """
    return {
        "ai_api_status": ai_api_status,
        "ai_api_url": AI_API_URL,
        "umbral_sospecha_si_score_numerico": AI_SUSPICION_THRESHOLD,
        "duracion_cierre_automatico_seg": AUTO_CLOSE_SECONDS,
        "cuentas_cerradas_activas": len(closed_accounts),
        "aviso_discord_configurado": bool(ADMIN_DISCORD_WEBHOOK),
    }


@app.get(
    "/api/v1/alerts",
    summary="Historial de avisos a administradores",
    tags=["IA"],
)
async def get_alerts(limit: int = 50):
    """
    Lista los bots detectados hasta ahora. Cada uno ya generó su cierre
    automático de 5 minutos y su aviso — esta lista es solo el historial,
    no requiere ninguna acción para que la cuenta se reabra.
    """
    return {
        "count": len(pending_alerts),
        "alerts": list(reversed(pending_alerts))[:limit],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "app_simulador:app",
        host       = "0.0.0.0",
        port       = 8000,
        log_level  = "warning",   # uvicorn mínimo; el logging propio maneja el detalle
        access_log = False,       # desactivado: nuestro middleware lo reemplaza
    )
