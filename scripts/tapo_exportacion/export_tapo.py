"""Request one Tapo sensor history report from a local interactive session."""

from __future__ import annotations

import base64
import binascii
import getpass
import json
import re
import ssl
import sys
from datetime import date, datetime, time, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import cloud_probe


def display_name(value: object) -> str:
    """Decode a cloud nickname where possible and filter terminal control characters."""
    if not isinstance(value, str) or len(value) > 256:
        return "sin nombre"
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        if decoded.isprintable():
            value = decoded
    except (ValueError, UnicodeError, binascii.Error):
        pass
    clean = "".join(c for c in value if c.isprintable()).strip()
    return clean[:80] or "sin nombre"


def report_body(start: date, end: date, today: date, zone: ZoneInfo, email: str) -> dict:
    """Build one-minute intervals using inclusive local calendar days."""
    if end < start or end > today or (end - start).days >= 31:
        raise ValueError("Elige fechas ordenadas, hasta hoy, con un máximo de 31 días incluidos.")
    if not email or len(email) > 254 or "@" not in email:
        raise ValueError("El correo de la cuenta no es válido para la exportación.")
    return {
        "emailAddress": email, "lang": "es_ES", "interval": 60,
        "startTimestamp": int(datetime.combine(start, time.min, zone).timestamp()),
        "endTimestamp": int(datetime.combine(end + timedelta(days=1), time.min, zone).timestamp()),
    }


def request_report(
    sensor: dict, host: str, token: str, terminal: str, app_type: str,
    body: dict, context: ssl.SSLContext,
) -> int:
    """Send once to the sensor's validated cloud host and return its status code."""
    thing = sensor.get("thingName")
    if not isinstance(thing, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", thing):
        raise ValueError("El sensor no tiene un identificador válido para la exportación.")
    sensor_url = sensor.get("appServerUrl")
    target_host = cloud_probe.checked_host(sensor_url) if sensor_url else host
    path = f"/v1/things/{quote(thing, safe='')}/history-data/temp-hmdt/report"
    headers = cloud_probe.iot_headers(token, terminal, app_type)
    headers["Content-Type"] = "application/json;charset=UTF-8"
    response = cloud_probe.post_json(path, json.dumps(body).encode("utf-8"), headers,
                                     host=target_host, context=context)
    code = response.get("code")
    if type(code) is not int:
        raise ValueError("Respuesta de exportación sin código de resultado reconocible.")
    return code


def interactive_export(email: str):
    """Create a session callback; credentials and cloud identifiers remain local."""
    def run(host: str, token: str, terminal: str, app_type: str, context: ssl.SSLContext) -> None:
        sensors, complete = cloud_probe.sensor_list(host, token, terminal, app_type, context)
        if not complete:
            raise ValueError("La lista de sensores está incompleta; no se enviará la solicitud.")
        if not sensors:
            raise ValueError("No se encontraron sensores T310/T315.")
        print("\nSensores disponibles:")
        for index, sensor in enumerate(sensors, 1):
            model = cloud_probe.safe_label(sensor.get("deviceModel") or sensor.get("model"))
            print(f"  {index}. {display_name(sensor.get('nickname'))} ({model})")
        try:
            selection = int(input("Número del sensor: ").strip())
            if not 1 <= selection <= len(sensors):
                raise ValueError("Número de sensor fuera de la lista.")
            start = date.fromisoformat(input("Fecha inicial (AAAA-MM-DD): ").strip())
            end = date.fromisoformat(input("Fecha final incluida (AAAA-MM-DD): ").strip())
            zone_name = input("Zona horaria del sensor [Europe/Madrid]: ").strip()
            zone_name = zone_name or "Europe/Madrid"
            zone = ZoneInfo(zone_name)
        except (ValueError, ZoneInfoNotFoundError):
            print("Selección, fecha o zona horaria no válida; no se ha enviado nada.")
            return
        try:
            body = report_body(start, end, datetime.now(zone).date(), zone, email)
        except ValueError as exc:
            print(str(exc))
            return
        print(f"Informe para el sensor {selection}, del {start} al {end}, "
              f"intervalos de un minuto y zona {zone_name}.")
        if input("Escribe SI para enviar una única solicitud: ").strip().upper() != "SI":
            print("Solicitud cancelada.")
            return
        try:
            code = request_report(sensors[selection - 1], host, token, terminal, app_type,
                                  body, context)
        except (OSError, cloud_probe.CloudHTTPError, ValueError):
            print("No se pudo confirmar el resultado. La solicitud podría haber llegado a Tapo; "
                  "comprueba el correo antes de volver a enviarla.")
            return
        if code == 0:
            print("Tapo ha aceptado la solicitud. Comprueba el correo de tu cuenta; "
                  "la recepción y el contenido del archivo no se comprueban automáticamente.")
        else:
            print(f"Tapo ha rechazado la solicitud de exportación: código {code}.")
    return run


def main() -> None:
    print("Exportación experimental: una solicitud a Tapo por correo, sin reintentos automáticos.")
    email = input("Correo de la cuenta Tapo: ").strip()
    password = getpass.getpass("Contraseña: ")
    try:
        _, services, status = cloud_probe.probe(email, password, interactive_export(email))
        if services is None:
            print(f"No se ha solicitado ninguna exportación: {status}.")
    except (cloud_probe.CloudHTTPError, OSError, ValueError):
        print("No se ha podido completar la preparación. Comprueba los datos y la conexión.",
              file=sys.stderr)
    finally:
        password = ""


if __name__ == "__main__":
    main()
