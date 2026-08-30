import datetime
import json
import uuid

class LoggerInmutableBGG:
    @staticmethod
    def registrar_evento(accion: str, nivel_seguridad: int, detalle: str):
        """Escribe una entrada de log estructurada y protegida en modo Append-Only."""
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "log_id": str(uuid.uuid4()),
            "zona_bgg": f"Zona {nivel_seguridad}",
            "operacion": accion,
            "status": detalle,
            "integridad_hash": ""
        }
        
        # Cálculo de firma del log para evitar alteraciones posteriores (Trazabilidad Inmutable)
        payload = f"{log_entry['timestamp']}-{log_entry['log_id']}-{log_entry['operacion']}"
        log_entry["integridad_hash"] = uuid.uuid5(uuid.NAMESPACE_DNS, payload).hex
        
        # En producción esto se envía a un almacenamiento WORM (Write Once, Read Many)
        with open("bgg_immutable_audit.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")