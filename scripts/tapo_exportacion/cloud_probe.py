"""Interactive, read-only proof of concept for the EU TP-Link cloud endpoint."""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import json
import re
import ssl
import string
import uuid
from collections import Counter
from collections.abc import Callable
from http.client import HTTPSConnection
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit
from zipfile import ZipFile

CLOUD_HOST = "eu-wap.tplinkcloud.com"
MAX_RESPONSE = 2_000_000
SAFE_MODEL_CHARS = frozenset(string.ascii_letters + string.digits + " _.-/")
SERVICE_IDS = ("nbu.iot-app-server.app", "nbu.iot-cloud-gateway.app", "nbu.iot-security.appdevice")
APK_SHA256 = "a01fd475f378687d4be684741161df0f5e3daa274acb15303c44c0198b37b88f"
APK_PATH = Path(__file__).resolve().parents[2] / "assets" / "tapo" / "tapo-3.22.105.apk"
V2_HOST = "n-wap.i.tplinkcloud.com"
TRUSTED_CERTS = {
    "8d27224dac20c2db8a380e3103b4e383c481ee41b681908579aee416761da289",
    "8b54f0364e840fb010d517324725f0d30245d35b45f9be4b6e50b84f03fdec19",
}


def safe_label(value: Any) -> str:
    """Bound untrusted model labels before displaying them on a terminal."""
    if not isinstance(value, str) or not value or len(value) > 80:
        return "desconocido"
    return value if all(character in SAFE_MODEL_CHARS for character in value) else "desconocido"


class CloudHTTPError(Exception):
    """An HTTP failure containing only the non-sensitive status code."""

    def __init__(self, status: int):
        self.status = status
        super().__init__(f"HTTP {status}")


def post_json(
    path: str, body: bytes, headers: dict[str, str], *,
    host: str = CLOUD_HOST, context: ssl.SSLContext | None = None,
) -> dict[str, Any]:
    """Post to a validated TP-Link cloud endpoint; never follow redirects."""
    connection = HTTPSConnection(host, timeout=20, context=context or ssl.create_default_context())
    try:
        connection.request("POST", path, body, headers)
        response = connection.getresponse()
        if response.status != 200:
            raise CloudHTTPError(response.status)
        payload = response.read(MAX_RESPONSE + 1)
    finally:
        connection.close()
    if len(payload) > MAX_RESPONSE:
        raise ValueError("La respuesta del servidor supera el tamaño permitido.")
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise ValueError("La respuesta del servidor no es un objeto JSON.")
    return result


def cloud_call(body: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    """Call the fixed EU cloud endpoint once; responses and credentials stay in memory."""
    path = "/" if token is None else f"/?{urlencode({'token': token})}"
    return post_json(path, json.dumps(body).encode(), {"Content-Type": "application/json"})


def get_json(
    host: str, path: str, headers: dict[str, str], context: ssl.SSLContext
) -> dict[str, Any]:
    """Read a bounded response from an already validated TP-Link host."""
    connection = HTTPSConnection(host, timeout=20, context=context)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise CloudHTTPError(response.status)
        payload = response.read(MAX_RESPONSE + 1)
    finally:
        connection.close()
    if len(payload) > MAX_RESPONSE:
        raise ValueError("La respuesta del servidor supera el tamaño permitido.")
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise ValueError("La respuesta del servidor no es un objeto JSON.")
    return result


def apk_path() -> Path:
    """Verify the entire APK before reading application identity or certificates."""
    with APK_PATH.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != APK_SHA256:
            raise ValueError("La APK base no coincide con la versión verificada.")
    return APK_PATH


def app_identity() -> tuple[str, str, str]:
    """Read the app's signing configuration from the previously verified APK in memory."""
    with ZipFile(apk_path()) as archive:
        info = archive.getinfo("assets/sdkconfig.xml")
        if info.file_size > 2_000_000:
            raise ValueError("La configuración de la APK supera el tamaño permitido.")
        config = archive.read(info)
    app = re.search(rb"<TPLINKAppServer>(.*?)</TPLINKAppServer>", config, re.DOTALL)
    if not app:
        raise ValueError("La APK no contiene la configuración de la aplicación.")
    values = []
    for field in (b"AppType", b"AccessKey", b"SecretKey"):
        value = re.search(rb"<" + field + rb">([A-Za-z0-9_-]{1,80})</" + field + rb">", app[1])
        if value is None:
            raise ValueError("La configuración de la aplicación está incompleta.")
        values.append(value[1].decode("ascii"))
    return values[0], values[1], values[2]


def v2_context() -> ssl.SSLContext:
    """Add only the two TLS certificates embedded in the verified Tapo APK."""
    with ZipFile(apk_path()) as archive:
        entry = archive.getinfo("classes13.dex")
        if entry.file_size > 30_000_000:
            raise ValueError("La entrada de certificados supera el tamaño permitido.")
        data = archive.read(entry)
    certs = re.findall(
        rb"-----BEGIN CERTIFICATE-----\n[A-Za-z0-9+/=\n\r]+-----END CERTIFICATE-----", data
    )
    selected = []
    for cert in certs:
        text = cert.decode("ascii")
        der = ssl.PEM_cert_to_DER_cert(text)
        if hashlib.sha256(der).hexdigest() in TRUSTED_CERTS:
            selected.append(text)
    if len(selected) != len(TRUSTED_CERTS):
        raise ValueError("No se encontraron los certificados esperados en la APK.")
    context = ssl.create_default_context()
    context.load_verify_locations(cadata="\n".join(selected))
    return context


def checked_host(url: str) -> str:
    """Only accept HTTPS regional endpoints under TP-Link domains with no path or credentials."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    trusted = any(host.endswith("." + domain) for domain in ("tplinkcloud.com", "tplinknbu.com"))
    if (parsed.scheme != "https" or not trusted or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("La dirección regional no es un servidor HTTPS admitido de TP-Link.")
    return host


def signed_v2_call(
    host: str, path: str, body_data: dict[str, Any], terminal: str,
    identity: tuple[str, str, str], context: ssl.SSLContext, token: str | None = None,
) -> dict[str, Any]:
    """Make one signed V2 request using the same bytes for the digest and HTTP body."""
    app_type, access_key, secret_key = identity
    body = json.dumps(body_data).encode()
    digest = base64.b64encode(hashlib.md5(body, usedforsecurity=False).digest()).decode()
    nonce = str(uuid.uuid4())
    timestamp = "9999999999"
    message = f"{digest}\n{timestamp}\n{nonce}\n{path}".encode()
    signature = hmac.new(secret_key.encode(), message, "sha1").hexdigest()
    auth = (
        f"Timestamp={timestamp}, Nonce={nonce}, "
        f"AccessKey={access_key}, Signature={signature}"
    )
    params = {
        "appName": app_type, "appVer": "3.22.105", "termID": terminal,
        "ospf": "Android 14", "brand": "TPLINK", "locale": "es_ES", "netType": "wifi",
        "model": "Pixel", "termName": "Pixel", "termMeta": "Pixel",
    }
    if token is not None:
        params["token"] = token
    return post_json(f"{path}?{urlencode(params)}", body, {
        "Content-Type": "application/json;charset=UTF-8", "Content-MD5": digest,
        "X-Authorization": auth,
    }, host=host, context=context)


def iot_headers(token: str, terminal: str, app_type: str) -> dict[str, str]:
    """Return the authenticated IoT client headers without logging their values."""
    return {
        "Authorization": f"ut|{token}", "x-app-name": app_type,
        "x-app-version": "3.22.105", "x-term-id": terminal,
        "x-ospf": "Android 14", "x-net-type": "wifi", "x-strict": "0",
        "x-locale": "es_ES", "app-cid": f"app:{app_type}:{terminal}",
    }


def sensor_list(
    host: str, token: str, terminal: str, app_type: str, context: ssl.SSLContext
) -> tuple[list[dict[str, Any]], bool]:
    """Read up to ten pages, keeping matching devices in memory only."""
    headers = iot_headers(token, terminal, app_type)
    sensors: list[dict[str, Any]] = []
    seen = 0
    for page in range(10):
        query = urlencode({
            "page": page, "pageSize": 100, "includePcDevice": "false",
            "includeKasaShareDevices": "false", "includeMatterDevice": "false",
            "includeExternalVendorDeviceInfo": "false",
        })
        response = get_json(host, f"/v2/things?{query}", headers, context)
        result = response.get("result", response)
        if not isinstance(result, dict) or not isinstance(result.get("data"), list):
            raise ValueError("La lista IoT no tiene el formato esperado.")
        devices = result["data"]
        if any(not isinstance(device, dict) for device in devices):
            raise ValueError("La lista IoT contiene una entrada inválida.")
        for device in devices:
            model = device.get("deviceModel") or device.get("model") or ""
            if isinstance(model, str) and model.upper().startswith(("T310", "T315")):
                sensors.append(device)
        seen += len(devices)
        total = result.get("total")
        if type(total) is int and total >= 0 and seen >= total:
            return sensors, True
        if not devices or (total is None and len(devices) < 100):
            return sensors, total is None
    return sensors, False


def count_sensors(
    host: str, token: str, terminal: str, app_type: str, context: ssl.SSLContext
) -> tuple[int, bool]:
    """Count T310/T315 sensors without displaying device details."""
    sensors, complete = sensor_list(host, token, terminal, app_type, context)
    return len(sensors), complete


ConnectedCallback = Callable[[str, str, str, str, ssl.SSLContext], None]


def response_error(response: dict[str, Any]) -> int | None:
    """Read numeric error codes from either the envelope or the nested result."""
    outer = response.get("error_code", response.get("errorCode"))
    result = response.get("result")
    nested = result.get("errorCode", result.get("error_code")) if isinstance(result, dict) else None
    for value in (outer, nested):
        if isinstance(value, str) and re.fullmatch(r"-?\d{1,8}", value):
            value = int(value)
        if type(value) is int and value != 0:
            return value
    return 0 if outer in (0, "0") else None


def mfa_process_id(result: dict[str, Any]) -> str | None:
    """Accept observed Tapo spelling and the variant used by other clients."""
    candidates = [result.get("MFAProcessId"), result.get("mfaProcessId")]
    present = [value for value in candidates if isinstance(value, str) and value]
    if not present or any(value != present[0] for value in present):
        return None
    return present[0]


def verify_mfa(
    host: str, username: str, password: str, terminal: str, identity: tuple[str, str, str],
    context: ssl.SSLContext, login_result: dict[str, Any],
    code_prompt: Callable[[int], str] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Request one email code or accept a TOTP code, then verify it once."""
    process_id = mfa_process_id(login_result)
    methods = login_result.get("supportedMFATypes")
    if process_id is None:
        return None, "verificación adicional: falta el identificador del proceso"
    if methods is not None and not isinstance(methods, list):
        return None, "verificación adicional: formato de métodos desconocido"
    # Tapo's login screen does not require supportedMFATypes before offering email.
    if not methods or 2 in methods:
        sent = signed_v2_call(host, "/api/v2/account/getEmailVC4TerminalMFA", {
            "cloudUserName": username, "cloudPassword": password,
            "appType": identity[0], "terminalUUID": terminal,
        }, terminal, identity, context)
        error = response_error(sent)
        if error != 0:
            detail = f"código {error}" if type(error) is int else "error de respuesta"
            return None, f"envío del código por correo: {detail}"
        if code_prompt is None:
            print("Tapo ha aceptado la solicitud de código. Revisa el correo de tu cuenta.")
        mfa_type = 2
    elif 3 in methods:
        if code_prompt is None:
            print("Introduce el código de tu aplicación de autenticación.")
        mfa_type = 3
    else:
        available = sorted(value for value in methods if type(value) is int and 0 <= value <= 9)
        return None, f"verificación sin correo ni TOTP disponible; tipos: {available}"
    code = (code_prompt(mfa_type) if code_prompt else
            getpass.getpass("Código de verificación (no se mostrará): ")).strip()
    if not re.fullmatch(r"[0-9]{4,12}", code):
        return None, "código de verificación no válido; no se ha enviado"
    params = {
        "appType": identity[0], "cloudUserName": username, "code": code,
        "MFAType": mfa_type,
        "supportBindAccount": False, "terminalBindEnabled": False,
    }
    params["MFAProcessId"] = process_id
    verified = signed_v2_call(host, "/api/v2/account/checkMFACodeAndLogin", params,
                              terminal, identity, context)
    code = ""
    error = response_error(verified)
    if error != 0:
        detail = f"código {error}" if type(error) is int else "error de respuesta"
        return None, f"verificación: {detail}"
    result = verified.get("result")
    if not isinstance(result, dict):
        return None, "verificación: respuesta incompleta"
    return result, "ok"


def mfa_response_shape(response: dict[str, Any]) -> str:
    """Describe only preselected response fields, without disclosing their values."""
    def state(obj: Any, key: str) -> str:
        if not isinstance(obj, dict) or key not in obj:
            return "ausente"
        value = obj[key]
        if value is None:
            return "nulo"
        if isinstance(value, str):
            return "texto" if value else "vacío"
        if isinstance(value, list):
            return "lista"
        return "otro tipo"

    result = response.get("result")
    fields = (
        ("id MFA en resultado", result, "MFAProcessId"),
        ("id mfa en resultado", result, "mfaProcessId"),
        ("métodos", result, "supportedMFATypes"),
        ("correo MFA", result, "mfaEmail"),
        ("servidor V2", result, "appServerUrlV2"),
    )
    return "; ".join(f"{label}: {state(obj, key)}" for label, obj, key in fields)


def discover_iot_services(
    username: str, password: str, terminal: str, legacy_token: str,
    on_connected: ConnectedCallback | None = None,
    code_prompt: Callable[[int], str] | None = None,
) -> tuple[tuple[str, ...] | None, str]:
    """Discover the regional server and try the existing session before a V2 login."""
    try:
        identity = app_identity()
        context = v2_context()
        region = signed_v2_call(V2_HOST, "/api/v2/account/getAccountStatusAndUrl", {
            "appType": identity[0], "cloudUserName": username, "regionCode": "ES",
        }, terminal, identity, context)
        error = region.get("error_code", region.get("errorCode"))
        if error != 0:
            return None, f"región: código {error}" if type(error) is int else "región: error"
        region_result = region.get("result")
        if not isinstance(region_result, dict):
            return None, "región: respuesta incompleta"
        region_url = region_result.get("appServerUrl") or region_result.get("appServerUrlV2")
        if not isinstance(region_url, str):
            return None, "región: dirección ausente"
        host = checked_host(region_url)
        account_url = region_result.get("accountApiUrl") or region_url
        if not isinstance(account_url, str):
            return None, "región: dirección de cuenta ausente"
        account_host = checked_host(account_url)
        response = signed_v2_call(host, "/api/v2/common/getAppServiceUrl", {
            "serviceIds": list(SERVICE_IDS),
        }, terminal, identity, context, legacy_token)
        active_token = legacy_token
        service_result = response.get("result")
        if (response.get("error_code", response.get("errorCode")) != 0
                or not isinstance(service_result, dict)
                or not isinstance(service_result.get("serviceUrls"), dict)):
            login = signed_v2_call(host, "/api/v2/account/login", {
                "appType": identity[0], "appVersion": "3.22.105", "cloudPassword": password,
                "cloudUserName": username, "platform": "Android", "refreshTokenNeeded": False,
                "supportBindAccount": False, "terminalUUID": terminal,
                "terminalName": "Codex", "terminalMeta": "Codex",
            }, terminal, identity, context)
            login_result = login.get("result")
            if not isinstance(login_result, dict):
                return None, "acceso V2: respuesta incompleta"
            error = response_error(login)
            if error == -20677:
                if mfa_process_id(login_result) is None:
                    diagnostic = mfa_response_shape(login)
                    return None, f"verificación incompleta (sin enviar código); {diagnostic}"
                args = (account_host, username, password, terminal, identity, context, login_result)
                login_result, status = (verify_mfa(*args, code_prompt=code_prompt)
                                        if code_prompt else verify_mfa(*args))
                if login_result is None:
                    return None, status
            elif error != 0:
                detail = f"código interno {error}" if type(error) is int else "error"
                return None, f"acceso V2: {detail}"
            active_token = login_result.get("token")
            if not isinstance(active_token, str) or not active_token:
                return None, "acceso V2: token ausente sin código de error reconocido"
            login_url = login_result.get("appServerUrl")
            if login_url is not None:
                if not isinstance(login_url, str):
                    return None, "acceso V2: dirección regional no válida"
                host = checked_host(login_url)
            response = signed_v2_call(host, "/api/v2/common/getAppServiceUrl", {
                "serviceIds": list(SERVICE_IDS),
            }, terminal, identity, context, active_token)
    except FileNotFoundError:
        return None, "APK verificada ausente en assets/tapo/tapo-3.22.105.apk"
    except CloudHTTPError as exc:
        return None, f"HTTP {exc.status}"
    except (OSError, ValueError, KeyError):
        return None, "error de conexión o configuración"
    error = response.get("error_code", response.get("errorCode"))
    if error not in (None, 0):
        return None, f"servicios IoT: código {error}" if type(error) is int else "error de servicio"
    result = response.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("serviceUrls"), dict):
        return None, "respuesta sin lista de servicios"
    urls = result["serviceUrls"]
    services = tuple(
        service_id for service_id in SERVICE_IDS if isinstance(urls.get(service_id), str)
    )
    app_url = urls.get("nbu.iot-app-server.app")
    if not isinstance(app_url, str):
        return services, "servicio de listado IoT ausente"
    try:
        host = checked_host(app_url)
        sensors, complete = count_sensors(
            host, active_token, terminal, identity[0], context
        )
    except CloudHTTPError as exc:
        return services, f"listado IoT: HTTP {exc.status}"
    except (OSError, ValueError, KeyError):
        return services, "listado IoT: error de conexión o formato"
    suffix = "lista completa" if complete else "lista parcial"
    if on_connected is not None:
        on_connected(host, active_token, terminal, identity[0], context)
    return services, f"sensores T310/T315: {sensors} ({suffix})"


def probe(
    username: str, password: str, on_connected: ConnectedCallback | None = None,
    code_prompt: Callable[[int], str] | None = None,
) -> tuple[Counter[tuple[str, str]], tuple[str, ...] | None, str]:
    """Log in and summarize device types without returning credentials or tokens."""
    if not username or not password:
        raise ValueError("Es necesario indicar usuario y contraseña.")
    terminal = str(uuid.uuid4())
    login = cloud_call(
        {
            "method": "login",
            "params": {
                "appType": "Tapo_Android",
                "cloudUserName": username,
                "cloudPassword": password,
                "terminalUUID": terminal,
            },
        }
    )
    result = login.get("result")
    error = login.get("error_code", login.get("errorCode"))
    if error not in (None, 0) or not isinstance(result, dict):
        raise ValueError("La nube no ha aceptado el inicio de sesión.")
    token = result.get("token")
    if not isinstance(token, str) or not token:
        raise ValueError("La respuesta de inicio de sesión no incluye un token utilizable.")
    devices = cloud_call({"method": "getDeviceList"}, token)
    result = devices.get("result")
    error = devices.get("error_code", devices.get("errorCode"))
    if error not in (None, 0) or not isinstance(result, dict):
        raise ValueError("La nube no ha devuelto una lista de dispositivos utilizable.")
    device_list = result.get("deviceList")
    if not isinstance(device_list, list) or any(not isinstance(d, dict) for d in device_list):
        raise ValueError("La lista de dispositivos tiene un formato inesperado.")
    counts = Counter(
        (safe_label(device.get("deviceType")), safe_label(device.get("deviceModel")))
        for device in device_list
    )
    if code_prompt is not None:
        services, status = discover_iot_services(
            username, password, terminal, token, on_connected, code_prompt
        )
    elif on_connected is None:
        services, status = discover_iot_services(username, password, terminal, token)
    else:
        services, status = discover_iot_services(username, password, terminal, token, on_connected)
    return counts, services, status


def main() -> None:
    print("Prueba de lectura de la nube de Tapo: sin exportaciones ni cambios.")
    print("La contraseña no se mostrará ni se guardará en archivos.")
    username = input("Correo de la cuenta Tapo: ").strip()
    password = getpass.getpass("Contraseña: ")
    try:
        counts, services, status = probe(username, password)
    except CloudHTTPError as exc:
        raise SystemExit(
            f"La nube ha respondido HTTP {exc.status}; no se ha reintentado."
        ) from None
    except (TimeoutError, OSError):
        raise SystemExit(
            "No se pudo conectar de forma segura con la nube; no se ha reintentado."
        ) from None
    except (ValueError, json.JSONDecodeError) as exc:
        # Server-provided text may contain identifiers or secrets; do not print it.
        if isinstance(exc, json.JSONDecodeError):
            raise SystemExit("La respuesta no es JSON válido.") from None
        raise SystemExit(str(exc)) from None
    finally:
        password = ""
    print(f"Acceso correcto. Dispositivos informados por la nube: {sum(counts.values())}.")
    for (device_type, model), count in sorted(counts.items()):
        print(f"  {device_type} / {model}: {count}")
    print("Los sensores conectados a un hub pueden no figurar en esta lista.")
    if services is None:
        print(f"Descubrimiento IoT V2: {status}.")
    else:
        print(
            f"Descubrimiento IoT V2: {len(services)} de {len(SERVICE_IDS)} servicios identificados."
        )
        for service in services:
            print(f"  {service}")
        print(f"  {status}")


if __name__ == "__main__":
    main()
