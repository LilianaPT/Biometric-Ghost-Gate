# 🛡️ Biometric Ghost Gate (BGG)
**Infraestructura de Ciberseguridad de Alta Resiliencia para Entornos Bancarios y Fintech.**

## 🚀 Visión General
Biometric Ghost Gate (BGG) es un framework de seguridad diseñado para crear una "Bóveda Invisible" entre las aplicaciones de usuario y los servidores bancarios legacy. El sistema elimina el riesgo de intervención humana mediante la automatización total de la administración y el uso de identidades de máquina autónomas.

## 🛠️ Innovación: Administración Invisible
BGG resuelve el problema de las credenciales estáticas y el error humano mediante:
* **Identidades Autónomas:** Implementación de *Instance Principals* y *Dynamic Groups* en OCI.
* **Self-Healing Housekeeping:** Un motor en Python que gestiona la rotación de certificados mTLS y el mantenimiento de registros sin intervención manual.
* **Trazabilidad Inmutable:** Logs de auditoría automáticos diseñados para cumplir con normativas de la CNBV.

## 📂 Estructura del Repositorio
* `/src`: Scripts de automatización (Módulo de Housekeeping).
* `/docs`: Blueprints técnicos y diagramas de flujo administrativo.

## 👥 Equipo AQ Tech (Multidisciplinary Team)

El éxito de **Biometric Ghost Gate** se basa en la integración de tecnología avanzada, cumplimiento normativo y estrategia de mercado:

* **Liliana Pantoja:** Lead Developer & Arquitectura de Nube. Responsable del diseño del "Búnker Digital" y la automatización de infraestructura en OCI.
* **Evelyn:** Ingeniería de Kernel & Redes. Especialista en seguridad de bajo nivel y monitoreo mediante eBPF.
* **Ángela:** IA & Monitoreo Predictivo. Encargada de los modelos de detección de anomalías y respuesta ante amenazas.
* **Mar:** Marketing & Estrategia de Marca. Responsable de la identidad corporativa de AQ Tech y el posicionamiento de BGG en el sector Fintech.
* **Avygail:** Legal & Compliance. Encargada de asegurar que el framework cumpla con las normativas LFPDPPP y los estándares regulatorios de la CNBV.

🚀 Conexión con Discord establecida.

# Biometric Ghost Gate (BGG) — Banking Login Simulator

> **AQ Tech** · Proyecto interno · Sandbox / IA Training · eBPF Monitoring

---

## Estructura del Proyecto

```
bgg/
├── src/
│   └── app_simulador.py      ← Backend FastAPI (único módulo)
├── logs/
│   └── active/
│       └── bgg_operativo.log ← Generado en runtime (montado como volumen)
├── Dockerfile                ← Multi-stage, imagen slim
├── docker-compose.yml        ← Orquestación + volumen + reinicio automático
├── requirements.txt          ← Dependencias pinned
└── README.md
```

---

## Inicio Rápido

```bash
# 1. Clonar / copiar el proyecto en la VM Linux
cd /opt/bgg   # o el path que prefiera el equipo

# 2. Crear la carpeta de logs en el host (el bind mount la requiere)
mkdir -p logs/active

# 3. Construir y levantar el contenedor en background
docker compose up -d --build

# 4. Verificar estado
docker compose ps
docker compose logs -f
```

---

## Endpoints

| Método | Ruta                    | Descripción                          |
|--------|-------------------------|--------------------------------------|
| GET    | `/`                     | Healthcheck del sistema              |
| POST   | `/api/v1/auth/login`    | Simulación de autenticación bancaria |
| GET    | `/docs`                 | Swagger UI interactivo               |
| GET    | `/redoc`                | Documentación ReDoc                  |

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

---

## Usuarios Mock

| Username       | Password           | Tipo     | Account ID    |
|----------------|--------------------|----------|---------------|
| `cliente_001`  | `Banco$ecure#2024` | PREMIUM  | MX-4821-0001  |
| `cliente_002`  | `P@ssw0rd_BGG`     | STANDARD | MX-4821-0002  |
| `admin_bgg`    | `BGG_AdmIn!2024`   | ADMIN    | MX-0000-ADMIN |

---

## Formato del Log (`bgg_operativo.log`)

```
2024-11-15T14:23:01 UTC | INFO     | STARTUP  | BGG Banking Simulator v1.0.0 iniciando...
2024-11-15T14:23:05 UTC | INFO     | REQUEST  | method=GET    endpoint=/                    status=200 latency=    1.24ms
2024-11-15T14:23:10 UTC | INFO     | AUTH     | user=cliente_001            network_delay=0.8341s
2024-11-15T14:23:10 UTC | INFO     | REQUEST  | method=POST   endpoint=/api/v1/auth/login   status=200 latency=  835.42ms
2024-11-15T14:23:15 UTC | WARNING  | AUTH_FAIL| user=hacker_user            reason=invalid_credentials
```

El log vive en `./logs/active/bgg_operativo.log` (relativo al `docker-compose.yml`).

---

## Para el Equipo de IA (Análisis de Latencia)

- El endpoint `/api/v1/auth/login` introduce un **delay aleatorio entre 0.1 s y 1.5 s** via `asyncio.sleep`.
- El middleware registra la **latencia total** en milisegundos en cada línea de log.
- Para generar tráfico de prueba continuo:

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

## Para el Equipo de Seguridad (eBPF)

El tráfico HTTP corre en el puerto **8000/tcp** del host de la VM.

```bash
# Verificar que el proceso uvicorn es visible desde el kernel
ss -tlnp | grep 8000

# Ejemplo de tracing con bpftrace (monitorear syscalls write en el proceso)
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_write /comm == "uvicorn"/ { printf("%s\n", str(args->buf)); }'
```

---

## Comandos Útiles de Operación

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
```

