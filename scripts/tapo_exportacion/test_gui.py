"""Exercise desktop interactions with a fake provider, without network access."""

import gc
import tkinter as tk
import time
import unittest
from datetime import date
from unittest.mock import patch

import app


class DesktopWorkflowTest(unittest.TestCase):
    def setUp(self):
        try:
            self.window = app.App()
            self.window.withdraw()
            self.window.update()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")

    def tearDown(self):
        if hasattr(self, "window") and self.window.winfo_exists():
            self.window.busy = False
            self.window.close()
            self.window = None
            gc.collect()

    def test_discovery_export_confirmation_and_uncertain_result(self):
        window = self.window
        window.email_entry.insert(0, "user@example.invalid")
        window.password_entry.insert(0, "fake-password")
        captured = []
        with patch.object(window, "run_worker", side_effect=lambda kind, job: captured.append((kind, job))):
            window.connect()
            window.connect()
        self.assertEqual(len(captured), 1)
        self.assertEqual(window.password_entry.get(), "")
        self.assertEqual(str(window.action["state"]), "disabled")
        self.assertEqual(str(window.email_entry["state"]), "disabled")

        session = app.Session("host", "token", "terminal", "app", None,
                              [{"thingName": "fake", "model": "T310", "nickname": "Sensor"}])
        window.events.put(("connected", (session, "ok")))
        window.poll_events()
        self.assertEqual(window.view, "sensors")
        window.show_export()
        self.assertEqual(window.view, "export")
        window.start_entry.set_date(date(2026, 1, 1))
        window.end_entry.set_date(date(2026, 1, 1))

        with patch.object(app.messagebox, "askyesno", return_value=False), patch.object(
            window, "run_worker"
        ) as worker:
            window.submit()
            worker.assert_not_called()
        with patch.object(app.messagebox, "askyesno", return_value=True), patch.object(
            window, "run_worker", side_effect=lambda kind, job: captured.append((kind, job))
        ):
            window.submit()
            window.submit()
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[-1][0], "exported")
        self.assertEqual(str(window.start_entry["state"]), "disabled")
        self.assertEqual(str(window.end_entry["state"]), "disabled")
        self.assertEqual(str(window.zone_entry["state"]), "disabled")
        window.show_sensors()
        self.assertEqual(window.view, "export")
        window.events.put(("error", "exported"))
        window.poll_events()
        self.assertIn("comprueba el correo", window.status.cget("text"))
        self.assertEqual(str(window.action["state"]), "normal")
        self.assertEqual(str(window.start_entry["state"]), "normal")

    def test_empty_sensor_list_has_recovery(self):
        self.window.session = app.Session("host", "token", "terminal", "app", None, [])
        self.window.show_sensors()
        self.assertEqual(self.window.view, "sensors")
        self.window.show_connect()
        self.assertIsNone(self.window.session)

    def test_connection_failure_allows_retry(self):
        window = self.window
        window.email_entry.insert(0, "user@example.invalid")
        window.password_entry.insert(0, "fake-password")
        with patch.object(window, "run_worker"):
            window.connect()
        window.events.put(("connected", (None, "APK verificada ausente")))
        window.poll_events()
        self.assertEqual(window.view, "connect")
        self.assertIn("APK verificada ausente", window.status.cget("text"))
        self.assertEqual(str(window.action["state"]), "normal")

    def test_rejected_export_is_not_reported_as_accepted(self):
        window = self.window
        window.email = "user@example.invalid"
        window.session = app.Session("host", "token", "terminal", "app", None,
                                     [{"thingName": "fake", "model": "T310"}])
        window.show_sensors()
        window.show_export()
        window.set_busy("Enviando")
        window.events.put(("exported", -1))
        window.poll_events()
        self.assertIn("rechazó", window.status.cget("text"))
        self.assertNotIn("aceptada", window.status.cget("text"))

    def test_export_controls_fit_minimum_window(self):
        window = self.window
        window.geometry("900x680")
        window.session = app.Session("host", "token", "terminal", "app", None,
                                     [{"thingName": "fake", "model": "T310"}])
        window.show_sensors()
        window.show_export()
        window.status.config(text="Resultado desconocido: comprueba el correo antes de volver "
                             "a enviar; Tapo podría haberla recibido.")
        window.update_idletasks()
        bottom = window.main.winfo_rooty() + window.main.winfo_height()
        for widget in (window.start_entry, window.end_entry, window.zone_entry,
                       window.action, window.status):
            with self.subTest(widget=widget):
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)

    def test_worker_flow_acceptance_without_real_network(self):
        window = self.window
        session = app.Session("host", "token", "terminal", "app", None,
                              [{"thingName": "fake", "model": "T310", "nickname": "Sensor"}])

        def wait_for(predicate):
            deadline = time.monotonic() + 3
            while not predicate() and time.monotonic() < deadline:
                window.update()
                time.sleep(0.01)
            self.assertTrue(predicate(), "The interface did not finish the operation")

        window.email_entry.insert(0, "user@example.invalid")
        window.password_entry.insert(0, "fake-password")
        with patch.object(app, "discover", return_value=(session, "ok")) as discovery:
            window.connect()
            wait_for(lambda: window.view == "sensors")
            discovery.assert_called_once()
        window.show_export()
        window.start_entry.set_date(date(2026, 1, 1))
        window.end_entry.set_date(date(2026, 1, 1))
        with patch.object(app.messagebox, "askyesno", return_value=True), patch.object(
            app.export_tapo, "request_report", return_value=0
        ) as request:
            window.submit()
            wait_for(lambda: not window.busy)
            request.assert_called_once()
        self.assertIn("Solicitud aceptada", window.status.cget("text"))
        self.assertIn("aún no están verificados", window.status.cget("text"))

    def test_date_picker_calendar_changes_month_and_selects_leap_day(self):
        picker = app.DatePicker(self.window.main, date(2024, 1, 31))
        picker.pack()
        picker.invoke()
        self.assertTrue(picker.popup.winfo_exists())
        picker.change_month(1)
        self.assertEqual((picker.year, picker.month), (2024, 2))
        picker.choose_day(29)
        self.assertEqual(picker.get(), "2024-02-29")
        self.assertFalse(picker.popup.winfo_exists())
        picker.config(state="disabled")
        picker.invoke()
        self.assertFalse(picker.popup.winfo_exists())


if __name__ == "__main__":
    unittest.main()
