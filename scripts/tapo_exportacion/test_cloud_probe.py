import unittest
from collections import Counter
from unittest.mock import patch

from cloud_probe import (
    CloudHTTPError,
    checked_host,
    cloud_call,
    count_sensors,
    discover_iot_services,
    mfa_process_id,
    probe,
    verify_mfa,
)


class CloudProbeTest(unittest.TestCase):
    @patch("cloud_probe.discover_iot_services", return_value=(("nbu.iot-app-server.app",), "ok"))
    @patch("cloud_probe.cloud_call")
    def test_login_and_device_list(self, cloud_call, discover):
        cloud_call.side_effect = [
            {"error_code": 0, "result": {"token": "test-token"}},
            {
                "error_code": 0,
                "result": {
                    "deviceList": [
                        {"deviceType": "SMART.TAPOHUB", "deviceModel": "H100"},
                        {"deviceType": "SMART.TAPOHUB", "deviceModel": "H100"},
                    ]
                },
            },
        ]
        result, services, status = probe("person@example.invalid", "secret")
        self.assertEqual(result, Counter({("SMART.TAPOHUB", "H100"): 2}))
        self.assertEqual(services, ("nbu.iot-app-server.app",))
        self.assertEqual(status, "ok")
        self.assertEqual(cloud_call.call_count, 2)
        self.assertEqual(cloud_call.call_args.args[1], "test-token")
        self.assertEqual(discover.call_args.args[0], "person@example.invalid")

    @patch("cloud_probe.cloud_call", return_value={"errorCode": -1})
    def test_refused_login_stops_before_device_listing(self, cloud_call):
        with self.assertRaisesRegex(ValueError, "no ha aceptado"):
            probe("person@example.invalid", "secret")
        self.assertEqual(cloud_call.call_count, 1)

    @patch("cloud_probe.cloud_call", return_value={"result": {}})
    def test_missing_token_stops_before_device_listing(self, cloud_call):
        with self.assertRaisesRegex(ValueError, "no incluye un token"):
            probe("person@example.invalid", "secret")
        self.assertEqual(cloud_call.call_count, 1)

    @patch("cloud_probe.HTTPSConnection")
    def test_redirect_is_rejected_without_forwarding(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 302
        with self.assertRaises(CloudHTTPError) as error:
            cloud_call({"method": "login", "password": "secret"})
        self.assertEqual(error.exception.status, 302)
        connection.assert_called_once()
        connection.return_value.request.assert_called_once()
        connection.return_value.close.assert_called_once()

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.post_json")
    def test_signed_service_discovery_preserves_error_code(self, post, _context, _identity):
        post.return_value = {"error_code": -20104}
        services, status = discover_iot_services("user", "pass", "test-terminal", "v1-token")
        self.assertIsNone(services)
        self.assertEqual(status, "región: código -20104")
        self.assertTrue(post.call_args.args[0].startswith("/api/v2/account/getAccountStatusAndUrl?"))
        self.assertIn("X-Authorization", post.call_args.args[2])

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.count_sensors", return_value=(2, True))
    @patch("cloud_probe.signed_v2_call")
    def test_v2_login_and_service_discovery(self, call, _count, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {"token": "v2-token"}},
            {"error_code": 0, "result": {
                "serviceUrls": {"nbu.iot-app-server.app": "https://app.tplinknbu.com"}
            }},
        ]
        services, status = discover_iot_services("user", "pass", "test-terminal", "v1-token")
        self.assertEqual(services, ("nbu.iot-app-server.app",))
        self.assertEqual(status, "sensores T310/T315: 2 (lista completa)")
        self.assertEqual(call.call_count, 4)
        self.assertEqual(call.call_args.args[-1], "v2-token")
        self.assertEqual(call.call_args.args[2]["serviceIds"], [
            "nbu.iot-app-server.app", "nbu.iot-cloud-gateway.app", "nbu.iot-security.appdevice",
        ])

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.count_sensors", return_value=(1, True))
    @patch("cloud_probe.signed_v2_call")
    def test_service_discovery_uses_validated_login_region(self, call, _count, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {
                "token": "v2-token", "appServerUrl": "https://login.tplinkcloud.com",
            }},
            {"error_code": 0, "result": {
                "serviceUrls": {"nbu.iot-app-server.app": "https://app.tplinknbu.com"}
            }},
        ]
        _, status = discover_iot_services("user", "pass", "terminal", "v1-token")
        self.assertEqual(status, "sensores T310/T315: 1 (lista completa)")
        self.assertEqual(call.call_args.args[0], "login.tplinkcloud.com")

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.signed_v2_call")
    def test_login_region_rejects_untrusted_hosts(self, call, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {"token": "t", "appServerUrl": "https://evil.example"}},
        ]
        services, status = discover_iot_services("user", "pass", "terminal", "v1-token")
        self.assertIsNone(services)
        self.assertIn("error de conexión o configuración", status)
        self.assertEqual(call.call_count, 3)

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.signed_v2_call")
    def test_nested_v2_login_error_is_reported(self, call, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {"errorCode": "-20601"}},
        ]
        services, status = discover_iot_services("user", "pass", "test-terminal", "v1-token")
        self.assertIsNone(services)
        self.assertEqual(status, "acceso V2: código interno -20601")
        self.assertEqual(call.call_count, 3)

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.count_sensors", return_value=(5, True))
    @patch("cloud_probe.signed_v2_call")
    def test_existing_session_avoids_second_login(self, call, count, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": 0, "result": {
                "serviceUrls": {"nbu.iot-app-server.app": "https://app.tplinknbu.com"}
            }},
        ]
        services, status = discover_iot_services("user", "pass", "test-terminal", "v1-token")
        self.assertEqual(services, ("nbu.iot-app-server.app",))
        self.assertEqual(status, "sensores T310/T315: 5 (lista completa)")
        self.assertEqual(call.call_count, 2)
        self.assertEqual(count.call_args.args[1], "v1-token")

    def test_regional_url_rejects_untrusted_hosts_and_userinfo(self):
        for url in ("https://tplinkcloud.com.evil.example", "https://u@a.tplinkcloud.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                checked_host(url)

    @patch("cloud_probe.get_json")
    def test_sensor_count_uses_pagination_and_does_not_read_device_ids(self, get):
        get.side_effect = [
            {"total": 2, "data": [{"deviceModel": "T310"}]},
            {"total": 2, "data": [{"model": "T315"}]},
        ]
        count, complete = count_sensors("app.tplinknbu.com", "test-token", "terminal", "app", None)
        self.assertEqual((count, complete), (2, True))
        self.assertEqual(get.call_count, 2)
        self.assertIn("page=1", get.call_args.args[1])

    @patch("cloud_probe.getpass.getpass", return_value="123456")
    @patch("cloud_probe.signed_v2_call")
    def test_email_mfa_sends_once_then_verifies_once(self, call, _input):
        call.side_effect = [
            {"error_code": 0},
            {"error_code": 0, "result": {"token": "v2-token"}},
        ]
        result, status = verify_mfa(
            "host", "user", "password", "terminal", ("app", "key", "secret"), None,
            {"MFAProcessId": "process", "supportedMFATypes": [2]},
        )
        self.assertEqual(result, {"token": "v2-token"})
        self.assertEqual(status, "ok")
        self.assertEqual(call.call_count, 2)
        self.assertTrue(call.call_args_list[0].args[1].endswith("getEmailVC4TerminalMFA"))
        verification = call.call_args_list[1].args[2]
        self.assertEqual(verification["MFAType"], 2)
        self.assertEqual(verification["MFAProcessId"], "process")
        self.assertNotIn("mfaProcessId", verification)
        self.assertFalse(verification["terminalBindEnabled"])

    @patch("cloud_probe.getpass.getpass", return_value="not-a-code")
    @patch("cloud_probe.signed_v2_call", return_value={"error_code": 0})
    def test_invalid_mfa_code_is_not_submitted(self, call, _input):
        result, status = verify_mfa(
            "host", "user", "password", "terminal", ("app", "key", "secret"), None,
            {"mfaProcessId": "process", "supportedMFATypes": [2]},
        )
        self.assertIsNone(result)
        self.assertIn("no se ha enviado", status)
        self.assertEqual(call.call_count, 1)

    @patch("cloud_probe.getpass.getpass", return_value="123456")
    @patch("cloud_probe.signed_v2_call")
    def test_missing_mfa_methods_offers_email_like_tapo_app(self, call, _input):
        call.side_effect = [{"error_code": 0}, {"error_code": 0, "result": {"token": "t"}}]
        result, status = verify_mfa(
            "host", "user", "password", "terminal", ("app", "key", "secret"), None,
            {"mfaProcessId": "process"},
        )
        self.assertEqual((result, status), ({"token": "t"}, "ok"))
        self.assertEqual(call.call_count, 2)

    @patch("cloud_probe.signed_v2_call")
    def test_missing_mfa_process_id_does_not_request_email(self, call):
        result, status = verify_mfa(
            "host", "user", "password", "terminal", ("app", "key", "secret"), None,
            {"supportedMFATypes": [2]},
        )
        self.assertIsNone(result)
        self.assertIn("falta el identificador", status)
        call.assert_not_called()

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.signed_v2_call")
    def test_missing_id_reports_only_whitelisted_field_states(self, call, _context, _identity):
        call.side_effect = [
            {"error_code": 0, "result": {"appServerUrl": "https://region.tplinkcloud.com"}},
            {"error_code": -20590},
            {"error_code": 0, "result": {"errorCode": "-20677", "mfaEmail": "private@example.invalid",
                                        "token": "private-token", "supportedMFATypes": []}},
        ]
        result, status = discover_iot_services("user", "password", "terminal", "v1-token")
        self.assertIsNone(result)
        self.assertIn("id MFA en resultado: ausente", status)
        self.assertIn("métodos: lista", status)
        self.assertIn("correo MFA: texto", status)
        self.assertNotIn("private", status)
        self.assertEqual(call.call_count, 3)

    @patch("cloud_probe.app_identity", return_value=("test-app", "test-key", "test-secret"))
    @patch("cloud_probe.v2_context")
    @patch("cloud_probe.count_sensors", return_value=(5, True))
    @patch("cloud_probe.getpass.getpass", return_value="123456")
    @patch("cloud_probe.signed_v2_call")
    def test_end_to_end_mfa_continues_to_sensor_discovery(
        self, call, _input, _count, _context, _identity
    ):
        call.side_effect = [
            {"error_code": 0, "result": {
                "appServerUrl": "https://region.tplinkcloud.com",
                "accountApiUrl": "https://account.tplinkcloud.com",
            }},
            {"error_code": -20590},
            {"error_code": 0, "result": {
                "errorCode": "-20677", "MFAProcessId": "process", "supportedMFATypes": [2],
            }},
            {"error_code": 0},
            {"error_code": 0, "result": {"token": "v2-token"}},
            {"error_code": 0, "result": {
                "serviceUrls": {"nbu.iot-app-server.app": "https://app.tplinknbu.com"}
            }},
        ]
        services, status = discover_iot_services("user", "password", "terminal", "v1-token")
        self.assertEqual(services, ("nbu.iot-app-server.app",))
        self.assertEqual(status, "sensores T310/T315: 5 (lista completa)")
        self.assertEqual(call.call_count, 6)
        self.assertEqual(call.call_args_list[3].args[0], "account.tplinkcloud.com")

    def test_process_id_aliases_and_conflicts(self):
        self.assertEqual(mfa_process_id({"MFAProcessId": "id"}), "id")
        self.assertEqual(mfa_process_id({"mfaProcessId": "id"}), "id")
        self.assertEqual(mfa_process_id({"MFAProcessId": "id", "mfaProcessId": "id"}), "id")
        self.assertIsNone(mfa_process_id({"MFAProcessId": "a", "mfaProcessId": "b"}))


if __name__ == "__main__":
    unittest.main()
