# 🛡️ Biometric Ghost Gate (BGG)
**Sandbox de Ciberseguridad e IA para Entornos Bancarios y Fintech**

> **AQ Tech** · Proyecto interno · Sandbox / Entrenamiento de IA / Detección de Bots

---

## 🚀 Visión General

Biometric Ghost Gate (BGG) es un proyecto de ciberseguridad que busca crear una
"Bóveda Invisible" entre las aplicaciones de usuario y los servidores bancarios,
combinando infraestructura oculta, detección de comportamiento por IA, y
anonimización irreversible de datos biométricos.

Este repositorio contiene el **sandbox funcional** del proyecto: un simulador
bancario real (login + transferencias) que captura comportamiento humano y de
bots, y que ya está conectado en tiempo real a un modelo de detección de
anomalías.

> 📄 El estado detallado de cada fase del proyecto (qué está construido, qué
> está en desarrollo y qué es visión a futuro) vive en el documento
> `Project_Roadmap.docx` del equipo — este README se enfoca en cómo correr y
> usar lo que ya existe en código.

---

## 👥 Equipo AQ Tech

* **Liliana Pantoja** — Lead Developer & Arquitectura. Backend, infraestructura del sandbox y orquestación general del proyecto.
* **Karla Evelyn Morales Vega** — Ingeniería de Kernel & Redes. Despliegue en VM, monitoreo de tráfico y base para la futura interceptación eBPF.
* **Angela Joselin Olivares Camargo** — IA & Monitoreo Predictivo. Modelo de detección de anomalías (Isolation Forest) y su API de inferencia.
* **Mar Martinez** — Marketing & Estrategia de Marca. Identidad de AQ Tech y posicionamiento de BGG en el sector Fintech.
* **Avigayl Gonzalez** — Legal & Compliance. Cumplimiento con LFPDPPP y estándares regulatorios de la CNBV.

---

## 📂 Estructura del Repositorio

```
bgg/
├── src/
│   └── app_simulador.py       ← Backend FastAPI (login, transferencias, IA, alertas)
├── frontend/
│   └── index.html             ← App web (login + transferencias), servida en /app/
├── logs/
│   └── active/
│       └── bgg_operativo.log  ← Generado en runtime (montado como volumen)
├── Dockerfile                 ← Multi-stage, imagen slim
├── docker-compose.yml         ← Orquestación + volumen + variables de entorno
├── requirements.txt           ← Dependencias pinned
└── README.md
```

> El modelo de IA de Angela (`api.py` + `model_isolation.py`) vive en un
> **repositorio o proceso separado** — este backend se conecta a él por HTTP,
> no lo incluye directamente. Ver sección [Integración con IA](#-integración-con-ia-detección-de-bots).

---

## ⚡ Inicio Rápido

```bash
# 1. Clonar / copiar el proyecto en la VM Linux
cd /opt/bgg   # o el path que prefiera el equipo

# 2. Crear la carpeta de logs en el host (el bind mount la requiere)
mkdir -p logs/active

# 3. (Opcional) Configurar variables de entorno — ver tabla más abajo
export AI_API_URL="http://localhost:9000/api/v1/predict"
export ADMIN_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."

# 4. Construir y levantar el contenedor en background
docker compose up -d --build

# 5. Verificar estado
docker compose ps
docker compose logs -f
```

---

## 🌐 Frontend Web

La forma más simple de usar el sandbox es a través del navegador — no requiere
descargar ni instalar nada. El propio backend sirve la app:

```
http://<IP_DE_LA_VM>:8000/app/
```

Ahí cualquier persona del equipo puede iniciar sesión con cualquiera de los 15
usuarios mock, hacer transferencias, y ver el historial de actividad de una
cuenta (incluyendo si el origen de cada evento fue humano o bot).

---

## 🔌 Endpoints

| Método | Ruta                                    | Descripción                                    |
|--------|------------------------------------------|-------------------------------------------------|
| GET    | `/`                                      | Healthcheck del sistema                         |
| GET    | `/app/`                                  | Frontend Web (login + transferencias)           |
| POST   | `/api/v1/auth/login`                     | Simulación de autenticación bancaria            |
| POST   | `/api/v1/transactions/transfer`          | Simulación de transferencia bancaria            |
| GET    | `/api/v1/accounts/{account_id}/activity` | Historial de actividad de una cuenta            |
| GET    | `/api/v1/ai/status`                      | Estado de la conexión con la API de IA (Angela) |
| GET    | `/api/v1/alerts`                         | Historial de bots detectados y avisados         |
| GET    | `/docs`                                  | Swagger UI interactivo                          |
| GET    | `/redoc`                                 | Documentación ReDoc                             |

### Ejemplo: Login exitoso

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "cliente_001", "password": "Banco$ecure#2024"}' | jq
```

### Ejemplo: Login fallido (401)

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "cliente_001", "password": "wrong_password"}' | jq
```

### Ejemplo: Transferencia

```bash
curl -s -X POST http://localhost:8000/api/v1/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"account_id": "MX-4821-0001", "destination_account": "MX-9012-3344", "amount": 1500.00}' | jq
```

### Ejemplo: Historial de actividad de una cuenta

```bash
curl -s http://localhost:8000/api/v1/accounts/MX-4821-0001/activity | jq
```

### Ejemplo: Estado de la IA y alertas

```bash
curl -s http://localhost:8000/api/v1/ai/status | jq
curl -s http://localhost:8000/api/v1/alerts | jq
```

---

## 👤 Usuarios Mock

| Username       | Password              | Tipo     | Account ID       |
|----------------|------------------------|----------|-------------------|
| `cliente_001`  | `Banco$ecure#2024`     | PREMIUM  | MX-4821-0001      |
| `cliente_002`  | `P@ssw0rd_BGG`         | STANDARD | MX-4821-0002      |
| `cliente_003`  | `Sof1a#Segura25`       | STANDARD | MX-4821-0003      |
| `cliente_004`  | `Javi3r$Bank99`        | PREMIUM  | MX-4821-0004      |
| `cliente_005`  | `Luc1a_Clave#7`        | STANDARD | MX-4821-0005      |
| `cliente_006`  | `Dani3l#Pass456`       | PREMIUM  | MX-4821-0006      |
| `cliente_007`  | `Valen#Banco88`        | STANDARD | MX-4821-0007      |
| `cliente_008`  | `Mig3l$Segur0!`        | STANDARD | MX-4821-0008      |
| `cliente_009`  | `Camil4#Vault22`       | PREMIUM  | MX-4821-0009      |
| `cliente_010`  | `Rod0lfo$Key33`        | STANDARD | MX-4821-0010      |
| `cliente_011`  | `Isa4b3l#Pin09`        | STANDARD | MX-4821-0011      |
| `cliente_012`  | `Emili0$Token71`       | PREMIUM  | MX-4821-0012      |
| `admin_bgg`    | `BGG_AdmIn!2024`       | ADMIN    | MX-0000-ADMIN     |
| `soporte_bgg`  | `Soport3#BGG2024`      | SUPPORT  | MX-0000-SOPORTE   |
| `auditor_bgg`  | `Audit0r$Ghost1`       | AUDITOR  | MX-0000-AUDITOR   |

---

## 🤖 Integración con IA (Detección de Bots)

Cada login y cada transferencia se evalúan en tiempo real contra el modelo de
Angela (Isolation Forest, servido en un servicio HTTP separado — `api.py` +
`model_isolation.py`).

**Flujo:**

```
Login o transferencia llega al backend
    ↓
¿La cuenta tiene un cierre automático activo? → 423, rechazado
    ↓ No
Backend llama a la API de Angela: POST {AI_API_URL}
    { status_code, latency (ms), user_speed (s) }
    ↓
¿Angela responde "bloquear": true?
    ├─ Sí → cierra la cuenta 5 minutos (afecta login humano y bot,
    │        comparten cuenta), avisa a los administradores, y
    │        responde 423 con el tiempo exacto restante
    └─ No → sigue el flujo normal
```

El cierre se levanta **solo**, sin que nadie tenga que desbloquear nada. El
aviso siempre queda en el log del servidor y en `GET /api/v1/alerts`; si se
configura `ADMIN_DISCORD_WEBHOOK`, también se manda un mensaje al canal de
Discord del equipo.

> ⚠️ La API de Angela debe correr por separado (misma VM en otro puerto, o su
> propia máquina) y estar accesible desde donde corre este backend.

---

## ⚙️ Variables de Entorno

| Variable                 | Requerida | Descripción                                                                 | Ejemplo                                              |
|---------------------------|-----------|-------------------------------------------------------------------------------|-------------------------------------------------------|
| `AI_API_URL`              | No*       | URL del endpoint de predicción de Angela. Si no está configurada, la app funciona en modo degradado (sin clasificación de IA). | `http://localhost:9000/api/v1/predict`                |
| `ADMIN_DISCORD_WEBHOOK`   | No        | Webhook de Discord para avisos automáticos de bots detectados. Si no se configura, el aviso solo queda en el log y en `/api/v1/alerts`. | `https://discord.com/api/webhooks/...`                |

*No es obligatoria para que el sandbox arranque, pero sin ella la detección de bots no funciona.

---

## 📋 Formato del Log (`bgg_operativo.log`)

```
2026-08-07T16:52:00 UTC | INFO     | STARTUP  | BGG Banking Simulator v1.9.1 iniciando...
2026-08-07T16:52:05 UTC | INFO     | REQUEST  | method=GET    endpoint=/                    status=200 latency=    1.24ms
2026-08-07T16:52:10 UTC | INFO     | AUTH     | user=cliente_001 network_delay=0.8341s user_speed=7.43s source_type=human geo_lat=19.43260 geo_lon=-99.13320
2026-08-07T16:52:10 UTC | INFO     | AI_PREDICT | user=cliente_001 is_bot=False score=0.08 mensaje_ia="🟢 Acceso normal verificado con éxito." formato_reconocido=True
2026-08-07T16:52:10 UTC | INFO     | AUTH_OK  | user=cliente_001 account=MX-4821-0001 type=PREMIUM user_speed=7.43s source_type=human ai_score=0.08
2026-08-07T16:53:02 UTC | WARNING  | AI_ALERT | ¡BOT DETECTADO! account=MX-4821-0006 user=cliente_006 anomaly_score=-0.15 mensaje_ia="⚠️ Tráfico automatizado detectado." sesión cerrada 5 min
```

El log vive en `./logs/active/bgg_operativo.log` (relativo al `docker-compose.yml`).

---

## 🧪 Para el Equipo de IA — Generar Tráfico de Prueba

```bash
# Instalar herramienta de carga (si no está)
pip install httpx

# Script de benchmark rápido (100 requests)
for i in $(seq 1 100); do
  curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"cliente_001","password":"Banco$ecure#2024"}' > /dev/null
done
```

---

## 🔐 Para el Equipo de Seguridad

El tráfico HTTP corre en el puerto **8000/tcp** del host de la VM.

```bash
# Verificar que el proceso uvicorn es visible desde el kernel
ss -tlnp | grep 8000
```

> La interceptación real en Kernel (eBPF/XDP) es la siguiente fase del
> proyecto (Fase 2b del roadmap) — todavía no está implementada en este
> repositorio. Lo que existe hoy es observación de tráfico a nivel de
> sistema operativo, no bloqueo activo en Kernel.

---

## 🛠️ Comandos Útiles de Operación

```bash
# Ver logs en tiempo real
docker compose logs -f bgg-simulator

# Reiniciar el servicio
docker compose restart bgg-simulator

# Detener sin eliminar
docker compose stop

# Eliminar contenedor (logs en host se conservan)
docker compose down

# Ver uso de recursos
docker stats bgg-banking-simulator

# Verificar conexión con la API de IA
curl http://localhost:8000/api/v1/ai/status
```

---

## 🗺️ Estado del Proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| 2a | Sandbox y Observabilidad (este repositorio) | ✅ Completada |
| 2b | Ghost-MTD Real — eBPF/XDP, rotación de IPs | ⏳ Siguiente paso |
| 3a | Detección Conductual (IA de Angela conectada) | ✅ En producción en el sandbox |
| 3b | Detección Biométrica (deepfakes) | ⏳ Punto de partida definido, no iniciada |

Para el detalle completo de cada fase, cifras de mercado y modelo de negocio, ver `Project_Roadmap.docx`.
