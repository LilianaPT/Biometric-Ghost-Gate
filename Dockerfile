# ══════════════════════════════════════════════════════════════════════════════
# BIOMETRIC GHOST GATE (BGG) — AQ Tech
# Dockerfile — Banking Login Simulator
# ══════════════════════════════════════════════════════════════════════════════
#
# Estrategia: Multi-stage build para imagen final mínima y segura.
#   Stage 1 (builder): instala dependencias en un venv aislado.
#   Stage 2 (runtime): copia solo el venv y el código fuente.
#
# Imagen base: python:3.12-slim  (~50 MB vs ~1 GB de la imagen full)
# ══════════════════════════════════════════════════════════════════════════════

# ── STAGE 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Evitar archivos .pyc y buffering de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copiar solo requirements para aprovechar caché de capas Docker
COPY requirements.txt .

# Crear virtualenv aislado e instalar dependencias
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip --quiet && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── STAGE 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Metadata de la imagen
LABEL maintainer="AQ Tech Engineering <engineering@aqtech.io>" \
      project="Biometric Ghost Gate" \
      module="bgg-banking-simulator" \
      version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Añadir el venv al PATH para no requerir activación explícita
    PATH="/opt/venv/bin:$PATH"

# Usuario no-root para seguridad (principio de mínimo privilegio)
RUN groupadd --gid 1001 bgg && \
    useradd  --uid 1001 --gid bgg --no-create-home --shell /sbin/nologin bgg

WORKDIR /app

# Copiar venv desde el stage builder
COPY --from=builder /opt/venv /opt/venv

# Copiar código fuente
COPY src/ ./src/
COPY frontend/ ./frontend/

# Crear estructura de logs con permisos para el usuario bgg
RUN mkdir -p logs/active && \
    chown -R bgg:bgg /app

# Cambiar al usuario sin privilegios
USER bgg

# Puerto expuesto (documentación; el mapeo real va en docker-compose)
EXPOSE 8000

# Health check integrado — Docker lo usa para marcar el contenedor como healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Comando de arranque con uvicorn (workers=1 para sandbox; ajustar en producción)
CMD ["uvicorn", "src.app_simulador:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "warning", \
     "--no-access-log"]
