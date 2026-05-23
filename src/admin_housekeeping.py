"""
=============================================================================
 PROYECTO: Biometric Ghost-Gate (BGG)
 MÓDULO:   Administración Automática (Housekeeping)
 VERSIÓN:  1.0.0
 AUTOR:    Ingeniería de Seguridad BGG
 NORMA:    Cumplimiento CNBV - Trazabilidad de Auditoría
=============================================================================

DESCRIPCIÓN:
    Script de housekeeping para el proyecto BGG. Gestiona la rotación de
    certificados mTLS, limpieza de logs operativos y está estructurado para
    integrarse con Oracle Cloud Infrastructure (OCI) mediante Instance
    Principals, eliminando el uso de credenciales estáticas.

DEPENDENCIAS:
    - Python 3.8+
    - Librerías estándar: logging, os, shutil, time, datetime, uuid, pathlib
    - OCI SDK (comentado): oci  -> pip install oci

EJECUCIÓN:
    $ python bgg_housekeeping.py
=============================================================================
"""

import logging
import os
import shutil    # Mueve archivos entre directorios (y elimina el original)
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# =============================================================================
# SECCIÓN 1: CONFIGURACIÓN DE DIRECTORIOS Y CONSTANTES
# =============================================================================

# Directorio raíz del proyecto (relativo al script)
BASE_DIR = Path(__file__).parent

# Directorios de logs operativos
LOGS_ACTIVE_DIR  = BASE_DIR / "logs" / "active"
LOGS_ARCHIVE_DIR = BASE_DIR / "logs" / "archive"

# Directorio de certificados (simulado)
CERTS_DIR = BASE_DIR / "certs"

# Archivo central de auditoría (requerimiento CNBV)
AUDIT_TRAIL_FILE = BASE_DIR / "audit_trail.log"

# Umbral de antigüedad para rotación de logs (en segundos)
# LFPDPPP Art. 37: retención mínima de 10 años para datos personales.
# 10 años = 365 días × 10 × 24h × 60m × 60s = 315,360,000 segundos.
LOG_ROTATION_THRESHOLD_SECONDS = 315_360_000  # 10 años — cumplimiento LFPDPPP
 
# Retención mínima obligatoria en archivo (no borrar antes de esta fecha)
# Misma base legal: LFPDPPP Art. 37 — los archivos en logs/archive
# NO pueden eliminarse hasta cumplir este período desde su creación.
RETENCION_MINIMA_SEGUNDOS = 315_360_000  # 10 años — cumplimiento LFPDPPP


# Identificador del sistema para trazabilidad
SYSTEM_ID = "BGG-HOUSEKEEPING-v1.0"


# =============================================================================
# SECCIÓN 2: CONFIGURACIÓN DEL SISTEMA DE LOGGING (DOBLE SALIDA)
# =============================================================================

def configurar_logging() -> logging.Logger:
    """
    Configura el sistema de logging con dos handlers:
      1. Consola (stdout): Para visibilidad inmediata en VS Code / terminal.
      2. audit_trail.log: Registro persistente para auditorías CNBV.

    Formato de marca de tiempo: ISO 8601 con zona horaria UTC.

    Returns:
        logging.Logger: Logger principal configurado.
    """
    logger = logging.getLogger("BGG_HOUSEKEEPING")
    logger.setLevel(logging.DEBUG)

    # Evitar duplicación de handlers si la función se llama varias veces
    if logger.handlers:
        return logger

    formato_auditoria = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )

    # --- Handler 1: Consola ---
    handler_consola = logging.StreamHandler()
    handler_consola.setLevel(logging.DEBUG)
    handler_consola.setFormatter(formato_auditoria)

    # --- Handler 2: Archivo audit_trail.log ---
    # Se usa 'a' (append) para no sobreescribir el historial entre ejecuciones
    handler_archivo = logging.FileHandler(
        filename=AUDIT_TRAIL_FILE,
        mode="a",
        encoding="utf-8"
    )
    handler_archivo.setLevel(logging.INFO)
    handler_archivo.setFormatter(formato_auditoria)

    logger.addHandler(handler_consola)
    logger.addHandler(handler_archivo)

    return logger


# =============================================================================
# SECCIÓN 3: AUTENTICACIÓN OCI CON INSTANCE PRINCIPALS (SIN CREDENCIALES ESTÁTICAS)
# =============================================================================

def obtener_cliente_oci_identity(logger: logging.Logger):
    """
    Obtiene un cliente OCI autenticado mediante Instance Principals.

    Este método es el estándar de seguridad para workloads en OCI:
    NO requiere API keys, contraseñas ni archivos de configuración locales.
    Las credenciales son gestionadas automáticamente por el metadata service
    de la instancia de cómputo.

    NOTA: Bloque comentado hasta que el entorno OCI esté aprovisionado.
    En un ambiente de desarrollo local, se puede usar 'config_from_file'
    apuntando a ~/.oci/config con un perfil de pruebas.

    Args:
        logger: Logger activo para trazabilidad.

    Returns:
        Objeto cliente OCI o None en entorno de simulación.
    """
    logger.info("OCI | Iniciando autenticación via Instance Principals...")

    # -------------------------------------------------------------------------
    # TODO: INTEGRACIÓN OCI SDK - Descomentar en ambiente de producción OCI
    # -------------------------------------------------------------------------
    #
    # import oci
    #
    # try:
    #     # Instance Principal Signer: OCI gestiona las credenciales
    #     # automáticamente a través del Instance Metadata Service (IMDS).
    #     # Requiere que la instancia tenga una Dynamic Group y Policy en IAM.
    #     signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    #
    #     # Cliente de Identity para operaciones de IAM/Vault
    #     cliente_identity = oci.identity.IdentityClient(
    #         config={},  # Vacío: Instance Principals no usa config file
    #         signer=signer
    #     )
    #
    #     # Cliente de Vault para rotación de secretos (certificados)
    #     cliente_vault = oci.vault.VaultsClient(
    #         config={},
    #         signer=signer
    #     )
    #
    #     logger.info("OCI | Autenticación exitosa. Signer: InstancePrincipal.")
    #     return {"identity": cliente_identity, "vault": cliente_vault}
    #
    # except oci.exceptions.RequestException as e:
    #     logger.error(f"OCI | Fallo de autenticación: {e}")
    #     raise
    # -------------------------------------------------------------------------

    logger.warning(
        "OCI | [SIMULACIÓN] Instance Principals desactivados. "
        "Ejecutando en modo local sin conexión a OCI."
    )
    return None  # Retorna None en modo simulación


# =============================================================================
# SECCIÓN 4: ROTACIÓN DE TOKENS / CERTIFICADOS mTLS
# =============================================================================

def rotar_certificado_mtls(logger: logging.Logger, cliente_oci=None) -> bool:
    """
    Simula el proceso completo de rotación de un certificado mTLS para BGG.

    Flujo de rotación:
      1. Detectar el certificado activo vigente.
      2. Generar un nuevo certificado con UUID único (simulado).
      3. Registrar el nuevo certificado como activo.
      4. Invalidar/revocar el certificado anterior.
      5. Registrar todo en el audit trail.

    En producción, los pasos 2-4 se ejecutarían contra OCI Certificates Service
    o un Vault para almacenar el secreto de forma segura.

    Args:
        logger:      Logger activo para trazabilidad.
        cliente_oci: Cliente OCI autenticado (None en simulación).

    Returns:
        bool: True si la rotación fue exitosa, False en caso contrario.
    """
    logger.info("=" * 60)
    logger.info("CERTIFICADOS | Iniciando proceso de rotación mTLS...")

    try:
        # Asegurar que el directorio de certificados existe
        CERTS_DIR.mkdir(parents=True, exist_ok=True)

        archivo_cert_activo = CERTS_DIR / "mtls_cert_active.pem"

        # --- PASO 1: Detectar certificado vigente ---
        cert_anterior_id = None
        if archivo_cert_activo.exists():
            # En producción: leer el serial/fingerprint real del certificado
            # usando la librería 'cryptography': cert.serial_number
            cert_anterior_id = archivo_cert_activo.read_text(encoding="utf-8").strip()
            logger.info(
                f"CERTIFICADOS | Certificado anterior detectado: [{cert_anterior_id[:40]}...]"
            )
        else:
            logger.info("CERTIFICADOS | No existe certificado previo. Primera emisión.")

        # --- PASO 2: Generar nuevo certificado (simulado con UUID) ---
        nuevo_cert_id = f"BGG-CERT-{uuid.uuid4().hex.upper()}"
        timestamp_emision = datetime.now(timezone.utc).isoformat()
        contenido_simulado = (
            f"CERT_ID={nuevo_cert_id}\n"
            f"EMITIDO={timestamp_emision}\n"
            f"SUJETO=CN=bgg.biometric.ghost-gate,O=BGG-SEC,C=MX\n"
            f"EMISOR=CN=BGG-Internal-CA,O=BGG-SEC,C=MX\n"
            f"ALGORITMO=TLS_AES_256_GCM_SHA384\n"
        )

        # -------------------------------------------------------------------------
        # TODO: INTEGRACIÓN OCI Certificates - Descomentar en producción
        # -------------------------------------------------------------------------
        # if cliente_oci:
        #     import oci
        #     cert_request = oci.certificates_management.models.CreateCertificateDetails(
        #         name=f"bgg-mtls-cert-{uuid.uuid4().hex[:8]}",
        #         compartment_id="ocid1.compartment.oc1..XXXXX",  # Leer de variable de entorno
        #         certificate_config=oci.certificates_management.models.CreateCertificateManagedExternallyIssuedByInternalCaConfigDetails(
        #             config_type="MANAGED_EXTERNALLY_ISSUED_BY_INTERNAL_CA",
        #             issuer_certificate_authority_id="ocid1.certificateauthority.oc1..XXXXX"
        #         )
        #     )
        #     respuesta = cliente_oci["certificates"].create_certificate(cert_request)
        #     nuevo_cert_id = respuesta.data.id
        #     logger.info(f"CERTIFICADOS | OCI Certificate creado: {nuevo_cert_id}")
        # -------------------------------------------------------------------------

        logger.info(f"CERTIFICADOS | Nuevo certificado generado: [{nuevo_cert_id}]")

        # --- PASO 3: Persistir el nuevo certificado como activo ---
        archivo_cert_activo.write_text(contenido_simulado, encoding="utf-8")
        logger.info(
            f"CERTIFICADOS | Certificado activo actualizado en: {archivo_cert_activo}"
        )

        # --- PASO 4: Invalidar certificado anterior ---
        if cert_anterior_id:
            # En producción: llamar a OCI Vault para marcar el secreto como DEPRECATED
            # o a OCI Certificates para iniciar la revocación:
            #
            # cliente_oci["certificates"].schedule_certificate_deletion(
            #     certificate_id=cert_anterior_id,
            #     schedule_certificate_deletion_details=oci.certificates_management.models
            #         .ScheduleCertificateDeletionDetails(
            #             time_of_deletion=datetime.now(timezone.utc) + timedelta(hours=24)
            #         )
            # )
            logger.info(
                f"CERTIFICADOS | [SIMULACIÓN] Certificado anterior INVALIDADO: "
                f"[{cert_anterior_id[:40]}...]"
            )

        logger.info("CERTIFICADOS | Rotación mTLS completada exitosamente.")
        logger.info("=" * 60)
        return True

    except OSError as e:
        logger.error(f"CERTIFICADOS | Error de sistema de archivos durante rotación: {e}")
        return False
    except Exception as e:
        logger.critical(
            f"CERTIFICADOS | Error inesperado durante rotación de certificado: {e}",
            exc_info=True
        )
        return False


# =============================================================================
# SECCIÓN 5: LIMPIEZA DE LOGS (HOUSEKEEPING)
# =============================================================================

def limpiar_logs_activos(
    logger: logging.Logger,
    umbral_segundos: int = LOG_ROTATION_THRESHOLD_SECONDS
) -> dict:
    """
    Función de housekeeping para logs operativos de BGG.

    Proceso:
      1. Escanea `logs/active` buscando archivos `.log`.
      2. Calcula la antigüedad de cada archivo.
      3. Los archivos más antiguos que `umbral_segundos` se MUEVEN a `logs/archive`.
      4. El archivo original es eliminado del directorio activo automáticamente
         por `shutil.move`.

    Los archivos archivados conservan su nombre original para trazabilidad
    forense, con un prefijo de timestamp para evitar colisiones.

    Args:
        logger:           Logger activo para trazabilidad.
        umbral_segundos:  Segundos de antigüedad mínima para archivar.

    Returns:
        dict: Resumen con contadores { "procesados", "archivados", "errores" }.
    """
    logger.info("=" * 60)
    logger.info(
        f"HOUSEKEEPING | Iniciando limpieza de logs. "
        f"Umbral de antigüedad: {umbral_segundos}s"
    )

    resumen = {"procesados": 0, "archivados": 0, "errores": 0}

    try:
        # Crear directorios si no existen
        LOGS_ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        tiempo_actual = time.time()
        archivos_log = list(LOGS_ACTIVE_DIR.glob("*.log"))

        if not archivos_log:
            logger.info("HOUSEKEEPING | No se encontraron archivos .log en logs/active.")
            logger.info("=" * 60)
            return resumen

        logger.info(
            f"HOUSEKEEPING | {len(archivos_log)} archivo(s) .log encontrado(s) en logs/active."
        )

        for archivo in archivos_log:
            resumen["procesados"] += 1

            try:
                # Obtener la fecha de última modificación del archivo
                tiempo_modificacion = archivo.stat().st_mtime
                antiguedad_segundos = tiempo_actual - tiempo_modificacion

                logger.debug(
                    f"HOUSEKEEPING | Evaluando: {archivo.name} | "
                    f"Antigüedad: {antiguedad_segundos:.1f}s"
                )

                if antiguedad_segundos > umbral_segundos:
                    # Construir nombre de destino con timestamp para evitar colisiones
                    timestamp_archivo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    nombre_destino = f"{timestamp_archivo}_{archivo.name}"
                    destino = LOGS_ARCHIVE_DIR / nombre_destino

                    # shutil.move: mueve el archivo Y elimina el original automáticamente
                    shutil.move(str(archivo), str(destino))

                    #Calcular fecha exacta de vencimiento para cumplimiento LFPDPPP
                    # El archivo NO puede borrarse antes de esta fecha (Art. 37 LFPDPPP - retención mínima de 10 años).
                    fecha_vencimiento = datetime.fromtimestamp(
                        tiempo_modificacion + RETENCION_MINIMA_SEGUNDOS,
                          tz=timezone.utc
                          ).isoformat()

                    resumen["archivados"] += 1
                    logger.info(
                        f"HOUSEKEEPING | RETENCIÓN LFPDPPP Art.37: {nombre_destino} "
                        f"conservar hasta: {fecha_vencimiento}"
                    )
                else:
                    logger.debug(
                        f"HOUSEKEEPING | OMITIDO (reciente): {archivo.name} "
                        f"(antigüedad: {antiguedad_segundos:.1f}s < umbral {umbral_segundos}s)"
                    )

            except PermissionError as e:
                resumen["errores"] += 1
                logger.error(
                    f"HOUSEKEEPING | Sin permisos para mover {archivo.name}: {e}"
                )
            except OSError as e:
                resumen["errores"] += 1
                logger.error(
                    f"HOUSEKEEPING | Error de OS al procesar {archivo.name}: {e}"
                )

        logger.info(
            f"HOUSEKEEPING | Resumen: "
            f"Procesados={resumen['procesados']} | "
            f"Archivados={resumen['archivados']} | "
            f"Errores={resumen['errores']}"
        )
        logger.info("=" * 60)
        return resumen

    except Exception as e:
        logger.critical(
            f"HOUSEKEEPING | Fallo crítico en limpieza de logs: {e}",
            exc_info=True
        )
        resumen["errores"] += 1
        return resumen


# =============================================================================
# SECCIÓN 6: GENERADOR DE LOGS DE PRUEBA (UTILIDAD DE DESARROLLO)
# =============================================================================

def generar_logs_prueba(logger: logging.Logger, cantidad: int = 5) -> None:
    """
    Utilidad de desarrollo: crea archivos .log de prueba en `logs/active`.

    Los primeros archivos se marcan con una fecha antigua (simulando logs
    viejos) para validar el comportamiento de la función de housekeeping.

    Args:
        logger:   Logger activo para trazabilidad.
        cantidad: Número de archivos de prueba a generar.
    """
    logger.info(f"TEST | Generando {cantidad} archivo(s) de log de prueba...")
    LOGS_ACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    for i in range(1, cantidad + 1):
        nombre = f"bgg_operativo_{i:03d}.log"
        ruta   = LOGS_ACTIVE_DIR / nombre

        contenido = (
            f"[{datetime.now(timezone.utc).isoformat()}] INFO BGG | "
            f"Log operativo de prueba #{i} | Módulo: AUTH_BIOMETRIC\n"
        )
        ruta.write_text(contenido, encoding="utf-8")

        # Simular logs "viejos": modificar el tiempo de los primeros 3 archivos
        if i <= 3:
            tiempo_antiguo = time.time() - (LOG_ROTATION_THRESHOLD_SECONDS + 10)
            os.utime(ruta, (tiempo_antiguo, tiempo_antiguo))
            logger.debug(f"TEST | Creado (ANTIGUO): {nombre}")
        else:
            logger.debug(f"TEST | Creado (RECIENTE): {nombre}")

    logger.info("TEST | Archivos de prueba generados correctamente.")


# =============================================================================
# SECCIÓN 7: PUNTO DE ENTRADA PRINCIPAL
# =============================================================================

def main():
    """
    Orquestador principal del proceso de housekeeping de BGG.

    Secuencia de ejecución:
      1. Configurar logging y audit trail.
      2. Autenticar con OCI Instance Principals.
      3. Generar datos de prueba (solo en dev).
      4. Ejecutar rotación de certificados mTLS.
      5. Ejecutar limpieza de logs activos.
      6. Reportar estado final de la ejecución.
    """
    # Inicialización del logger (primer paso, siempre)
    logger = configurar_logging()

    logger.info("*" * 60)
    logger.info(f"INICIO | Sistema: {SYSTEM_ID}")
    logger.info(f"INICIO | Timestamp UTC: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"INICIO | PID del proceso: {os.getpid()}")
    logger.info("*" * 60)

    estado_global = {"exito": True, "errores": []}

    # -------------------------------------------------------------------------
    # PASO 1: Autenticación OCI
    # -------------------------------------------------------------------------
    try:
        cliente_oci = obtener_cliente_oci_identity(logger)
    except Exception as e:
        logger.error(f"MAIN | No se pudo inicializar OCI: {e}")
        cliente_oci = None
        estado_global["errores"].append("oci_auth")

    # -------------------------------------------------------------------------
    # PASO 2: Generar logs de prueba (REMOVER EN PRODUCCIÓN)
    # -------------------------------------------------------------------------
    logger.info("DEV | Generando datos de prueba para demostración...")
    try:
        generar_logs_prueba(logger, cantidad=5)
    except Exception as e:
        logger.error(f"DEV | Error al generar logs de prueba: {e}")

    # -------------------------------------------------------------------------
    # PASO 3: Rotación de certificados mTLS
    # -------------------------------------------------------------------------
    rotacion_exitosa = rotar_certificado_mtls(logger, cliente_oci)
    if not rotacion_exitosa:
        estado_global["exito"] = False
        estado_global["errores"].append("cert_rotation")
        logger.error("MAIN | La rotación de certificados FALLÓ. Revisar audit_trail.log.")

    # -------------------------------------------------------------------------
    # PASO 4: Housekeeping de logs activos
    # -------------------------------------------------------------------------
    resumen_logs = limpiar_logs_activos(logger, umbral_segundos=LOG_ROTATION_THRESHOLD_SECONDS)
    if resumen_logs["errores"] > 0:
        estado_global["exito"] = False
        estado_global["errores"].append("log_cleanup")

    # -------------------------------------------------------------------------
    # REPORTE FINAL
    # -------------------------------------------------------------------------
    logger.info("*" * 60)
    if estado_global["exito"]:
        logger.info(
            f"FIN | Housekeeping completado EXITOSAMENTE. "
            f"Logs archivados: {resumen_logs['archivados']}."
        )
    else:
        logger.warning(
            f"FIN | Housekeeping completado con ERRORES: {estado_global['errores']}. "
            f"Revisar audit_trail.log para detalles."
        )
    logger.info(f"FIN | Timestamp UTC: {datetime.now(timezone.utc).isoformat()}")
    logger.info("*" * 60)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == "__main__":
    main()
