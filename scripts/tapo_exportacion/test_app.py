import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import app
import cloud_probe


class AppWorkflowTest(unittest.TestCase):
    def test_reports_are_sent_in_order_with_same_dates_and_rejections_do_not_stop(self):
        sensors = [{"thingName": f"id-{i}"} for i in range(3)]
        session = app.Session("host", "token", "terminal", "app", None, sensors)
        body = {"startTimestamp": 1, "endTimestamp": 2}
        progress = []
        with patch.object(app.export_tapo, "request_report", side_effect=[0, -1, 0]) as request:
            outcomes = app.send_reports(session, sensors, body, lambda i, n: progress.append((i, n)))
        self.assertEqual(outcomes, [("accepted", 0), ("rejected", -1), ("accepted", 0)])
        self.assertEqual(progress, [(1, 3), (2, 3), (3, 3)])
        self.assertEqual([call.args[0] for call in request.call_args_list], sensors)
        self.assertTrue(all(call.args[5] == body for call in request.call_args_list))

    def test_reports_stop_after_uncertain_result_and_never_retry(self):
        sensors = [{"thingName": f"id-{i}"} for i in range(4)]
        session = app.Session("host", "token", "terminal", "app", None, sensors)
        with patch.object(app.export_tapo, "request_report", side_effect=[0, TimeoutError()]) as request:
            outcomes = app.send_reports(session, sensors, {}, lambda _i, _n: None)
        self.assertEqual(outcomes, [("accepted", 0), ("unknown", None),
                                    ("not_sent", None), ("not_sent", None)])
        self.assertEqual(request.call_count, 2)

    def test_discovery_returns_complete_session_and_passes_mfa_prompt(self):
        prompt = lambda _: "123456"
        sensors = [{"thingName": "fake", "model": "T310"}]

        def fake_probe(email, password, callback, code_prompt):
            self.assertEqual((email, password), ("user@example.invalid", "test"))
            self.assertIs(code_prompt, prompt)
            callback("host", "token", "terminal", "app", None)
            return {}, (), "ok"

        with patch.object(cloud_probe, "probe", side_effect=fake_probe), patch.object(
            cloud_probe, "sensor_list", return_value=(sensors, True)
        ):
            session, status = app.discover("user@example.invalid", "test", prompt)
        self.assertEqual(status, "ok")
        self.assertEqual(session.sensors, sensors)
        self.assertNotIn("token", repr(session))

    def test_discovery_rejects_partial_list(self):
        def fake_probe(_email, _password, callback, _prompt):
            callback("host", "token", "terminal", "app", None)

        with patch.object(cloud_probe, "probe", side_effect=fake_probe), patch.object(
            cloud_probe, "sensor_list", return_value=([{"model": "T310"}], False)
        ), self.assertRaisesRegex(ValueError, "incompleta"):
            app.discover("user@example.invalid", "test", lambda _: "")

    def test_report_validation_and_date_limit(self):
        end = datetime.now(ZoneInfo("Europe/Madrid")).date() - timedelta(days=1)
        start = end - timedelta(days=30)
        body = app.make_report(start.isoformat(), end.isoformat(), "Europe/Madrid", "a@example.invalid")
        self.assertEqual(body["interval"], 60)
        for start, end, zone in (("bad", "2026-01-01", "Europe/Madrid"),
                                 ("2026-01-01", "2026-02-01", "Europe/Madrid"),
                                 ("2026-01-01", "2026-01-01", "bad/zone"),
                                 ("2026-01-01", "9999-01-01", "Europe/Madrid")):
            with self.subTest(start=start, end=end, zone=zone), self.assertRaises(ValueError):
                app.make_report(start, end, zone, "a@example.invalid")

    def test_mfa_callback_is_used_without_terminal_input(self):
        responses = [{"error_code": 0}, {"error_code": 0, "result": {"token": "fake"}}]
        with patch.object(cloud_probe, "signed_v2_call", side_effect=responses), patch.object(
            cloud_probe.getpass, "getpass", side_effect=AssertionError("terminal input used")
        ):
            result, status = cloud_probe.verify_mfa(
                "host", "user", "password", "terminal", ("app", "key", "secret"),
                None, {"MFAProcessId": "fake", "supportedMFATypes": [2]}, lambda _: "123456"
            )
        self.assertEqual(status, "ok")
        self.assertEqual(result, {"token": "fake"})

    def test_discovery_runs_mfa_and_delivers_sensor_session(self):
        login_responses = [
            {"error_code": 0, "result": {"token": "legacy-token"}},
            {"error_code": 0, "result": {"deviceList": []}},
        ]
        v2_responses = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {"errorCode": -20677, "MFAProcessId": "fake",
                                          "supportedMFATypes": [2]}},
            {"error_code": 0},
            {"error_code": 0, "result": {"token": "verified-token"}},
            {"error_code": 0, "result": {
                "serviceUrls": {"nbu.iot-app-server.app": "https://app.tplinknbu.com"}}},
        ]
        sensor = {"thingName": "fake-sensor", "model": "T310"}
        with patch.object(cloud_probe, "cloud_call", side_effect=login_responses), patch.object(
            cloud_probe, "app_identity", return_value=("app", "key", "secret")
        ), patch.object(cloud_probe, "v2_context", return_value=None), patch.object(
            cloud_probe, "signed_v2_call", side_effect=v2_responses
        ) as signed, patch.object(cloud_probe, "sensor_list", return_value=([sensor], True)), patch.object(
            cloud_probe.getpass, "getpass", side_effect=AssertionError("terminal input used")
        ):
            methods = []
            session, status = app.discover("user@example.invalid", "fake-password",
                                           lambda method: methods.append(method) or "123456")
        self.assertEqual(methods, [2])
        self.assertEqual(signed.call_count, 6)
        self.assertIn("checkMFACodeAndLogin", signed.call_args_list[4].args[1])
        self.assertEqual(session.token, "verified-token")
        self.assertEqual(session.sensors, [sensor])
        self.assertIn("lista completa", status)

    def test_cancelled_mfa_does_not_submit_a_verification_code(self):
        with patch.object(cloud_probe, "signed_v2_call", return_value={"error_code": 0}) as call:
            result, status = cloud_probe.verify_mfa(
                "host", "user", "password", "terminal", ("app", "key", "secret"),
                None, {"MFAProcessId": "fake", "supportedMFATypes": [2]}, lambda _: ""
            )
        self.assertIsNone(result)
        self.assertIn("no válido", status)
        self.assertEqual(call.call_count, 1)
        self.assertIn("getEmailVC4TerminalMFA", call.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
