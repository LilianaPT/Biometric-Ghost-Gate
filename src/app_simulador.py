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
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME        = "BGG Banking Simulator"
APP_VERSION     = "1.1.0"
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

    **Usuarios de prueba disponibles:**
    | Username       | Password              | Tipo     |
    |----------------|-----------------------|----------|
    | `cliente_001`  | `Banco$ecure#2024`    | PREMIUM  |
    | `cliente_002`  | `P@ssw0rd_BGG`        | STANDARD |
    | `admin_bgg`    | `BGG_AdmIn!2024`      | ADMIN    |
    """
    # ── Simular latencia de red (crucial para el dataset de IA) ───────────
    delay_aplicado = await simulate_network_latency()

    # ── Simular velocidad del usuario rellenando el formulario (Escenario B)
    user_speed = simulate_user_speed()

    logger.info(
        f"AUTH     | user={payload.username:<20} "
        f"network_delay={delay_aplicado:.4f}s "
        f"user_speed={user_speed:.2f}s"
    )

    # ── Validación mock de credenciales ───────────────────────────────────
    user_data = MOCK_USERS.get(payload.username)

    # Usuario no existe O contraseña incorrecta (mismo mensaje: evita user enumeration)
    if user_data is None or user_data["password"] != payload.password:
        logger.warning(
            f"AUTH_FAIL| user={payload.username:<20} "
            f"reason=invalid_credentials "
            f"user_speed={user_speed:.2f}s"
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
        f"user_speed={user_speed:.2f}s"
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
