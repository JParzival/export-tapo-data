import threading
import unittest
from datetime import date
from http.server import ThreadingHTTPServer
from zoneinfo import ZoneInfo

from mock_tapo import MockHandler, build_request, send_local


class RequestDatesTest(unittest.TestCase):
    def test_normal_day_is_one_day(self):
        body = build_request(date(2026, 10, 1), date(2026, 10, 1), ZoneInfo("Europe/Madrid"))
        self.assertEqual(body["endTimestamp"] - body["startTimestamp"], 86400)
        self.assertEqual(body["interval"], 60)

    def test_spring_clock_change_is_23_hours(self):
        body = build_request(date(2026, 3, 29), date(2026, 3, 29), ZoneInfo("Europe/Madrid"))
        self.assertEqual(body["endTimestamp"] - body["startTimestamp"], 23 * 3600)

    def test_fall_clock_change_is_25_hours(self):
        body = build_request(date(2026, 10, 25), date(2026, 10, 25), ZoneInfo("Europe/Madrid"))
        self.assertEqual(body["endTimestamp"] - body["startTimestamp"], 25 * 3600)

    def test_reversed_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            build_request(date(2026, 10, 2), date(2026, 10, 1), ZoneInfo("Europe/Madrid"))


class LocalHttpTest(unittest.TestCase):
    def test_request_and_rejection(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), MockHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = build_request(
                    date(2026, 10, 1), date(2026, 10, 1), ZoneInfo("Europe/Madrid")
                )
                self.assertEqual(
                    send_local(server.server_port, body),
                    {"mock": True, "accepted": True, "email_sent": False},
                )
                body["interval"] = 0
                with self.assertRaisesRegex(ValueError, "HTTP 400"):
                    send_local(server.server_port, body)
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
