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
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME        = "BGG Banking Simulator"
APP_VERSION     = "1.6.0"
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
    3. Valida contra el dataset mock de usuarios.
    4. Retorna `200 OK` con token simulado si las credenciales son correctas.
    5. Retorna `401 Unauthorized` si las credenciales son incorrectas.

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

    # ── Validación mock de credenciales ───────────────────────────────────
    user_data = MOCK_USERS.get(payload.username)

    # Usuario no existe O contraseña incorrecta (mismo mensaje: evita user enumeration)
    if user_data is None or user_data["password"] != payload.password:
        logger.warning(
            f"AUTH_FAIL| user={payload.username:<20} "
            f"reason=invalid_credentials "
            f"user_speed={user_speed:.2f}s "
            f"source_type={source_type} "
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
