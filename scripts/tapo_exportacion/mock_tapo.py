"""Local-only Tapo export request experiment; no actual Tapo service is used."""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, time, timedelta
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo


def build_request(start: date, end: date, zone: ZoneInfo) -> dict[str, object]:
    """Build a synthetic request using the app's inclusive calendar boundaries."""
    if end < start:
        raise ValueError("End date must be on or after start date")
    start_time = datetime.combine(start, time.min, tzinfo=zone)
    end_time = datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone)
    return {
        "emailAddress": "ejemplo@example.invalid",
        "lang": "es_ES",
        "startTimestamp": int(start_time.timestamp()),
        "endTimestamp": int(end_time.timestamp()),
        "interval": 60,
    }


class MockHandler(BaseHTTPRequestHandler):
    """Accept requests locally and return a clearly synthetic response."""

    def do_POST(self) -> None:
        expected = "/v1/things/sensor-demo/history-data/temp-hmdt/report"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != expected or length <= 0 or length > 4096:
                raise ValueError("Unexpected path or body length")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object")
            start = data.get("startTimestamp")
            end = data.get("endTimestamp")
            if type(start) is not int or type(end) is not int or end <= start:
                raise ValueError("Invalid time range")
            if data.get("interval") != 60:
                raise ValueError("This demonstration expects one-minute intervals")
            response = {"mock": True, "accepted": True, "email_sent": False}
            self.send_response(200)
        except (ValueError, UnicodeError, json.JSONDecodeError):
            response = {"mock": True, "accepted": False, "email_sent": False}
            self.send_response(400)
        payload = json.dumps(response).encode("utf-8")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass


def send_local(port: int, body: dict[str, object]) -> dict[str, object]:
    """Send only to the local mock; this does not contact the Tapo cloud."""
    path = "/v1/things/sensor-demo/history-data/temp-hmdt/report"
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(
            "POST", path, body=json.dumps(body), headers={"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        result = json.loads(response.read(4096))
        if response.status != 200:
            raise ValueError(f"Mock server rejected request: HTTP {response.status}")
        return result
    finally:
        connection.close()


def main() -> None:
    today = datetime.now(ZoneInfo("Europe/Madrid")).date()
    yesterday = today - timedelta(days=1)
    body = build_request(yesterday, yesterday, ZoneInfo("Europe/Madrid"))
    with ThreadingHTTPServer(("127.0.0.1", 0), MockHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            print("Solicitud simulada:", json.dumps(body, ensure_ascii=False, indent=2))
            result = send_local(server.server_port, body)
            print("Respuesta simulada:", json.dumps(result, ensure_ascii=False))
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
