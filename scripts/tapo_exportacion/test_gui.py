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

        with patch.object(window, "confirm_requests", return_value=False), patch.object(
            window, "run_worker"
        ) as worker:
            window.submit()
            worker.assert_not_called()
        with patch.object(window, "confirm_requests", return_value=True), patch.object(
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
        window.report_range = "2026-01-01 a 2026-01-01 · Europe/Madrid"
        window.set_busy("Enviando")
        window.events.put(("exported", [("rejected", -1)]))
        window.poll_events()
        self.assertIn("Rechazada", window.results.get("1.0", tk.END))
        self.assertNotIn("Aceptada", window.results.get("1.0", tk.END))

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

    def test_sensor_controls_fit_minimum_window(self):
        window = self.window
        window.geometry("900x680")
        sensors = [{"thingName": f"fake-{i}", "model": "T310"} for i in range(6)]
        window.session = app.Session("host", "token", "terminal", "app", None, sensors)
        window.show_sensors()
        window.update_idletasks()
        bottom = window.main.winfo_rooty() + window.main.winfo_height()
        self.assertLessEqual(window.action.winfo_rooty() + window.action.winfo_height(), bottom)
        self.assertLessEqual(window.account_back.winfo_rooty() + window.account_back.winfo_height(), bottom)

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
        with patch.object(window, "confirm_requests", return_value=True), patch.object(
            app.export_tapo, "request_report", return_value=0
        ) as request:
            window.submit()
            wait_for(lambda: not window.busy)
            request.assert_called_once()
        self.assertEqual(window.view, "results")
        self.assertIn("Aceptada", window.results.get("1.0", tk.END))

    def test_multiple_selection_and_confirmation(self):
        window = self.window
        window.email = "user@example.invalid"
        sensors = [{"thingName": f"fake-{n}", "model": "T310", "nickname": f"Sensor {n}"}
                   for n in range(3)]
        window.session = app.Session("host", "token", "terminal", "app", None, sensors)
        window.show_sensors()
        window.sensor_choice.selection_clear(0, tk.END)
        window.show_export()
        self.assertEqual(window.view, "sensors")
        self.assertIn("al menos", window.selection_status.cget("text"))
        window.sensor_choice.selection_set(0)
        window.sensor_choice.selection_set(2)
        window.show_export()
        self.assertEqual(window.sensors, [sensors[0], sensors[2]])
        window.start_entry.set_date(date(2026, 1, 1))
        window.end_entry.set_date(date(2026, 1, 1))
        window.back_to_sensors()
        self.assertEqual(window.sensor_choice.curselection(), (0, 2))
        window.show_export()
        self.assertEqual(window.start_entry.get(), "2026-01-01")
        self.assertEqual(window.end_entry.get(), "2026-01-01")
        with patch.object(window, "confirm_requests", return_value=False) as confirm:
            window.submit()
        self.assertIn("Sensores (2)", confirm.call_args.args[0])
        self.assertIn("Sensor 0", confirm.call_args.args[0])
        self.assertIn("Sensor 2", confirm.call_args.args[0])
        window.show_sensors()
        self.assertEqual(window.sensor_choice.curselection(), (0, 2))

    def test_after_partial_batch_only_unsent_sensors_are_preselected(self):
        window = self.window
        sensors = [{"thingName": f"fake-{n}", "model": "T310"} for n in range(4)]
        window.session = app.Session("host", "token", "terminal", "app", None, sensors)
        window.show_sensors()
        window.sensor_choice.selection_set(0, 3)
        window.show_export()
        window.report_range = "2026-01-01 a 2026-01-01 · Europe/Madrid"
        window.show_results([("accepted", 0), ("unknown", None),
                             ("not_sent", None), ("not_sent", None)])
        window.show_sensors()
        self.assertEqual(window.sensor_choice.curselection(), (2, 3))

    def test_after_completed_batch_no_sensor_is_automatically_reselected(self):
        window = self.window
        window.session = app.Session("host", "token", "terminal", "app", None,
                                     [{"thingName": "fake", "model": "T310"}])
        window.show_sensors()
        window.show_export()
        window.report_range = "2026-01-01 a 2026-01-01 · Europe/Madrid"
        window.show_results([("accepted", 0)])
        window.show_sensors()
        self.assertEqual(window.sensor_choice.curselection(), ())

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

    def test_sensor_cards_support_keyboard_selection(self):
        picker = app.SensorChoice(self.window.main, ["Sensor A", "Sensor B", "Sensor C"])
        picker.pack(fill="x")
        self.window.update()
        picker.move(1)
        picker.toggle(picker.active)
        self.assertEqual(picker.curselection(), (1,))
        picker.move(1)
        picker.toggle(picker.active)
        self.assertEqual(picker.curselection(), (1, 2))
        picker.move(-1)
        picker.toggle(picker.active)
        self.assertEqual(picker.curselection(), (2,))
        picker.use_accessible_list()
        self.assertEqual(picker.curselection(), (2,))
        picker.access_list.selection_set(0)
        self.assertEqual(picker.curselection(), (0, 2))

    def test_confirmation_and_verification_dialogs_can_be_cancelled(self):
        def close_dialog():
            dialogs = [widget for widget in self.window.winfo_children()
                       if isinstance(widget, tk.Toplevel)]
            self.assertEqual(len(dialogs), 1)
            dialogs[0].destroy()

        self.window.after(50, close_dialog)
        self.assertFalse(self.window.confirm_requests("Sensores (1):\nSensor de prueba"))
        self.window.after(50, close_dialog)
        self.assertEqual(self.window.prompt_verification(2), "")

    def test_language_switch_preserves_form_selection_and_results(self):
        window = self.window
        window.email_entry.insert(0, "user@example.invalid")
        window.password_entry.insert(0, "test-password")
        window.change_language("en")
        self.assertEqual(window.email_entry.get(), "user@example.invalid")
        self.assertEqual(window.password_entry.get(), "test-password")
        self.assertIn("not associated", window.disclaimer.cget("text"))
        window.session = app.Session("host", "token", "terminal", "app", None,
                                     [{"thingName": "a", "model": "T310"},
                                      {"thingName": "b", "model": "T315"}])
        window.show_sensors()
        window.sensor_choice.selection_set(1)
        window.change_language("es")
        self.assertEqual(window.sensor_choice.curselection(), (0, 1))
        window.show_export()
        window.start_entry.set_date(date(2026, 1, 1))
        window.end_entry.set_date(date(2026, 1, 10))
        window.change_language("en")
        self.assertEqual(window.view, "export")
        self.assertEqual(window.start_entry.get(), "2026-01-01")
        self.assertEqual(window.end_entry.get(), "2026-01-10")
        self.assertEqual(window.start_entry.language, "en")
        self.assertIn("Jan", window.start_entry.cget("text"))
        self.assertEqual(len(window.sensors), 2)
        window.start_entry.open_calendar()
        self.assertEqual(window.start_entry.popup.title(), "Select date")
        calendar_labels = [child.cget("text") for child in window.start_entry.calendar_body.winfo_children()
                           if isinstance(child, tk.Label)]
        self.assertIn("W", calendar_labels)
        window.start_entry.popup.destroy()
        window.report_range = "2026-01-01 to 2026-01-10 · Europe/Madrid"
        window.show_results([("accepted", 0), ("not_sent", None)])
        self.assertIn("Accepted", window.results.get("1.0", tk.END))
        selected = list(window.selection_indices)
        window.change_language("es")
        self.assertEqual(window.selection_indices, selected)
        self.assertIn("Aceptada", window.results.get("1.0", tk.END))

    def test_language_switch_is_ignored_while_busy(self):
        self.window.busy = True
        self.window.change_language("en")
        self.assertEqual(self.window.language, "es")


if __name__ == "__main__":
    unittest.main()
