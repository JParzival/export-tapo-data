import json
import ssl
import unittest
from datetime import date
from unittest.mock import patch
from zoneinfo import ZoneInfo

from export_tapo import display_name, interactive_export, report_body, request_report


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo("Europe/Madrid")
        self.body = report_body(date(2026, 3, 29), date(2026, 3, 29), date(2026, 4, 1),
                                self.zone, "user@example.invalid")

    def test_calendar_range_accounts_for_summer_time(self):
        self.assertEqual(self.body["endTimestamp"] - self.body["startTimestamp"], 23 * 3600)
        self.assertEqual(self.body["interval"], 60)

    def test_rejects_reversed_future_or_overlong_ranges(self):
        for start, end in ((date(2026, 4, 2), date(2026, 4, 1)),
                           (date(2026, 4, 1), date(2026, 4, 2)),
                           (date(2026, 3, 1), date(2026, 4, 1))):
            with self.subTest(start=start), self.assertRaises(ValueError):
                report_body(start, end, date(2026, 4, 1), self.zone, "user@example.invalid")

    def test_name_decoding_and_control_filtering(self):
        self.assertEqual(display_name("Q29jaW5h"), "Cocina")
        self.assertNotIn("\x1b", display_name("sensor\x1b[2J"))

    @patch("cloud_probe.post_json", return_value={"code": 0, "data": "private"})
    def test_report_uses_sensor_host_and_exact_one_minute_request(self, post):
        context = ssl.create_default_context()
        sensor = {"thingName": "sensor_123", "appServerUrl": "https://region.tplinknbu.com"}
        self.assertEqual(request_report(sensor, "default.tplinknbu.com", "token", "terminal",
                                        "app", self.body, context), 0)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "/v1/things/sensor_123/history-data/temp-hmdt/report")
        self.assertEqual(json.loads(args[1]), self.body)
        self.assertEqual(args[2]["Authorization"], "ut|token")
        self.assertEqual(kwargs["host"], "region.tplinknbu.com")
        post.assert_called_once()

    @patch("cloud_probe.post_json")
    def test_invalid_sensor_or_host_never_sends(self, post):
        for sensor in ({"thingName": "../escape"},
                       {"thingName": "id", "appServerUrl": "https://attacker.example"}):
            with self.subTest(sensor=sensor), self.assertRaises(ValueError):
                request_report(sensor, "good.tplinknbu.com", "token", "terminal", "app",
                               self.body, None)
        post.assert_not_called()

    @patch("cloud_probe.post_json", return_value={"message": "no status"})
    def test_unrecognized_response_is_not_success(self, _post):
        with self.assertRaises(ValueError):
            request_report({"thingName": "id"}, "good.tplinknbu.com", "token", "terminal",
                           "app", self.body, None)

    @patch("builtins.input", side_effect=["1", "2026-01-01", "2026-01-01", "", "NO"])
    @patch("cloud_probe.sensor_list", return_value=([
        {"thingName": "id", "model": "T310", "nickname": "Cocina"}], True))
    @patch("export_tapo.request_report")
    def test_cancel_does_not_send(self, request, _sensors, _input):
        interactive_export("user@example.invalid")("host", "token", "terminal", "app", None)
        request.assert_not_called()

    @patch("builtins.input", side_effect=["1", "2026-01-01", "2026-01-01", "", "SI"])
    @patch("cloud_probe.sensor_list", return_value=([
        {"thingName": "id", "model": "T310", "nickname": "Cocina"}], True))
    @patch("cloud_probe.post_json", return_value={"code": 0})
    def test_confirmed_flow_sends_one_request_to_the_selected_sensor(self, post, _sensors, _input):
        interactive_export("user@example.invalid")("iot.tplinknbu.com", "token", "terminal",
                                                     "app", None)
        post.assert_called_once()
        self.assertEqual(json.loads(post.call_args.args[1])["interval"], 60)
        self.assertIn("/things/id/", post.call_args.args[0])

    @patch("cloud_probe.sensor_list", return_value=([{"thingName": "id"}], False))
    @patch("export_tapo.request_report")
    def test_incomplete_listing_does_not_send(self, request, _sensors):
        with self.assertRaises(ValueError):
            interactive_export("user@example.invalid")("host", "token", "terminal", "app", None)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
