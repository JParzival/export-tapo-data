"""Desktop interface for the experimental Tapo export workflow."""

from __future__ import annotations

import calendar
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime
from tkinter import messagebox, simpledialog, ttk
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import cloud_probe
import export_tapo

BG = "#0c0247"
PANEL = "#170c5c"
FIELD = "#281b70"
TEXT = "#f4f4f4"
MUTED = "#d0cbe3"
TEAL = "#64d99a"
CYAN = "#41ddff"
AMBER = "#ffd326"

MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


class DatePicker(tk.Button):
    """Read-only date selector backed by a keyboard-accessible calendar dialog."""

    def __init__(self, parent: tk.Misc, initial: date) -> None:
        self.selected = initial
        self.popup: tk.Toplevel | None = None
        super().__init__(parent, command=self.open_calendar, anchor="w", relief="flat",
                         bg=FIELD, fg=TEXT, disabledforeground=MUTED,
                         activebackground="#3a2a83", activeforeground=TEXT,
                         highlightthickness=1, highlightbackground=FIELD,
                         highlightcolor=CYAN, font=("Segoe UI", 12), padx=12, pady=9)
        self.set_date(initial)

    def get(self) -> str:
        return self.selected.isoformat()

    def set_date(self, value: date) -> None:
        self.selected = value
        self.configure(text=f"{value:%d/%m/%Y}     ▾")

    def open_calendar(self) -> None:
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return
        popup = tk.Toplevel(self)
        self.popup = popup
        popup.title("Seleccionar fecha")
        popup.configure(bg=PANEL, padx=16, pady=14)
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.grab_set()
        self.year, self.month = self.selected.year, self.selected.month
        self.calendar_body = tk.Frame(popup, bg=PANEL)
        self.calendar_body.pack()
        popup.bind("<Escape>", lambda _event: popup.destroy())
        self.render_calendar()
        popup.update_idletasks()
        owner = self.winfo_toplevel()
        x = owner.winfo_rootx() + (owner.winfo_width() - popup.winfo_reqwidth()) // 2
        y = owner.winfo_rooty() + (owner.winfo_height() - popup.winfo_reqheight()) // 2
        x = max(0, min(x, popup.winfo_screenwidth() - popup.winfo_reqwidth()))
        y = max(0, min(y, popup.winfo_screenheight() - popup.winfo_reqheight()))
        popup.geometry(f"+{x}+{y}")
        popup.focus_set()

    def change_month(self, offset: int) -> None:
        month_index = (self.year - 1) * 12 + self.month - 1 + offset
        if not 0 <= month_index < 9999 * 12:
            return
        self.year, month_zero = divmod(month_index, 12)
        self.year += 1
        self.month = month_zero + 1
        self.render_calendar()

    def choose_day(self, day: int) -> None:
        self.set_date(date(self.year, self.month, day))
        if self.popup is not None:
            self.popup.destroy()
        self.focus_set()

    def render_calendar(self) -> None:
        for child in self.calendar_body.winfo_children():
            child.destroy()
        header = tk.Frame(self.calendar_body, bg=PANEL)
        header.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 8))
        for text, offset, side in (("‹", -1, "left"), ("›", 1, "right")):
            tk.Button(header, text=text, command=lambda n=offset: self.change_month(n),
                      bg=FIELD, fg=TEXT, relief="flat", font=("Segoe UI", 12, "bold"),
                      padx=12).pack(side=side)
        tk.Label(header, text=f"{MONTHS[self.month - 1].capitalize()} {self.year}",
                 bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(expand=True)
        for column, name in enumerate(("L", "M", "X", "J", "V", "S", "D")):
            tk.Label(self.calendar_body, text=name, bg=PANEL, fg=CYAN,
                     font=("Segoe UI", 9, "bold"), width=4).grid(row=1, column=column, pady=3)
        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), 2):
            for column, day in enumerate(week):
                if day:
                    selected = date(self.year, self.month, day) == self.selected
                    tk.Button(self.calendar_body, text=str(day), width=3, relief="flat",
                              bg=TEAL if selected else FIELD, fg=BG if selected else TEXT,
                              activebackground=CYAN, activeforeground=BG,
                              font=("Segoe UI", 10), highlightthickness=1,
                              highlightbackground=PANEL, highlightcolor=CYAN,
                              command=lambda n=day: self.choose_day(n)).grid(
                                  row=row, column=column, padx=2, pady=2, sticky="nsew")


@dataclass(repr=False)
class Session:
    """Keep the provider session and discovered sensors in memory only."""

    host: str
    token: str
    terminal: str
    app_type: str
    context: Any
    sensors: list[dict[str, Any]]


def discover(email: str, password: str, code_prompt: Any) -> tuple[Session | None, str]:
    """Sign in and collect a complete sensor list using the existing cloud client."""
    captured: list[Session] = []

    def connected(host: str, token: str, terminal: str, app_type: str, context: Any) -> None:
        sensors, complete = cloud_probe.sensor_list(host, token, terminal, app_type, context)
        if not complete:
            raise ValueError("La lista de sensores está incompleta. Vuelve a conectar.")
        captured.append(Session(host, token, terminal, app_type, context, sensors))

    _, _, status = cloud_probe.probe(email, password, connected, code_prompt)
    return (captured[0] if captured else None), status


def make_report(start: str, end: str, zone_name: str, email: str) -> dict[str, Any]:
    """Validate calendar inputs and prepare the existing report request."""
    try:
        zone = ZoneInfo(zone_name.strip())
        start_date, end_date = date.fromisoformat(start.strip()), date.fromisoformat(end.strip())
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Revisa las fechas (AAAA-MM-DD) y la zona horaria.") from exc
    return export_tapo.report_body(start_date, end_date, datetime.now(zone).date(), zone, email)


class App(tk.Tk):
    """A small, non-blocking desktop wizard for discovery and export."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Tapo Data · Exportación de sensores")
        self.geometry("1080x740")
        self.minsize(900, 680)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.pending_code: tuple[threading.Event, list[str]] | None = None
        self.session: Session | None = None
        self.email = ""
        self.busy = False
        self.view = "connect"
        self.poll_job: str | None = None
        self.build_shell()
        self.show_connect()
        self.poll_job = self.after(100, self.poll_events)

    def build_shell(self) -> None:
        sidebar = tk.Frame(self, bg=PANEL, width=225, padx=25, pady=30)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="●  TAPO DATA", bg=PANEL, fg=TEAL,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="SENSOR EXPORT", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 55))
        self.steps: list[tk.Label] = []
        for text in ("01   Conectar", "02   Sensores", "03   Exportar"):
            label = tk.Label(sidebar, text=text, bg=PANEL, fg=MUTED,
                             font=("Segoe UI", 11, "bold"), pady=12)
            label.pack(anchor="w")
            self.steps.append(label)
        tk.Label(sidebar, text="EXPERIMENTAL", bg=PANEL, fg=AMBER,
                 font=("Segoe UI", 9, "bold")).pack(side="bottom", anchor="w")
        self.main = tk.Frame(self, bg=BG, padx=55, pady=35)
        self.main.pack(side="left", fill="both", expand=True)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEAL, borderwidth=0, padding=9)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", TEXT)])

    def clear(self, step: int) -> None:
        for child in self.main.winfo_children():
            child.destroy()
        for i, label in enumerate(self.steps):
            label.configure(fg=TEAL if i == step else MUTED)

    def label(self, parent: tk.Misc, text: str, size: int = 11, color: str = TEXT,
              bold: bool = False, bg: str = BG, **kwargs: Any) -> tk.Label:
        return tk.Label(parent, text=text, bg=bg, fg=color, anchor="w", justify="left",
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)

    def heading(self, eyebrow: str, title: str, subtitle: str) -> None:
        self.label(self.main, eyebrow.upper(), 10, TEAL, True).pack(anchor="w", pady=(0, 12))
        self.label(self.main, title, 27, bold=True).pack(anchor="w")
        self.label(self.main, subtitle, 11, MUTED, wraplength=590).pack(anchor="w", pady=(8, 26))

    def entry(self, parent: tk.Misc, label: str, value: str = "", secret: bool = False) -> tk.Entry:
        self.label(parent, label, 10, MUTED, True).pack(anchor="w", pady=(11, 6))
        entry = tk.Entry(parent, bg=FIELD, fg=TEXT, insertbackground=TEAL, relief="flat",
                         disabledbackground=FIELD, disabledforeground=MUTED,
                         font=("Segoe UI", 12), show="•" if secret else "",
                         highlightthickness=1, highlightbackground=FIELD,
                         highlightcolor=TEAL)
        entry.insert(0, value)
        entry.pack(fill="x", ipady=10)
        return entry

    def button(self, parent: tk.Misc, text: str, command: Any, primary: bool = True) -> tk.Button:
        return tk.Button(parent, text=text, command=command, relief="flat", cursor="hand2",
                         bg=TEAL if primary else FIELD, fg=BG if primary else TEXT,
                         activebackground=CYAN if primary else "#3a2a83",
                         activeforeground=BG if primary else TEXT, padx=22, pady=11,
                         font=("Segoe UI", 10, "bold"), highlightthickness=1,
                         highlightbackground=TEAL if primary else FIELD)

    def status_line(self, text: str = "") -> None:
        self.status = self.label(self.main, text, 10, AMBER, wraplength=590)
        self.status.pack(anchor="w", pady=(16, 0))

    def show_connect(self) -> None:
        if self.busy:
            return
        self.view = "connect"
        self.session = None
        self.clear(0)
        self.heading("01 / conexión", "Conecta tu cuenta", "Todo empieza con tu cuenta Tapo. "
                     "Las credenciales se usan solo para esta sesión y no se guardan.")
        form = tk.Frame(self.main, bg=BG)
        form.pack(fill="x")
        self.email_entry = self.entry(form, "CORREO DE TAPO", self.email)
        self.password_entry = self.entry(form, "CONTRASEÑA", secret=True)
        self.action = self.button(self.main, "Conectar y buscar sensores  →", self.connect)
        self.busy_controls = [self.action, self.email_entry, self.password_entry]
        self.action.pack(anchor="w", pady=(28, 0))
        self.status_line("Puede solicitarse un código de verificación de Tapo.")
        self.email_entry.focus_set()

    def connect(self) -> None:
        if self.busy:
            return
        email, password = self.email_entry.get().strip(), self.password_entry.get()
        if not email or "@" not in email or not password:
            self.status.config(text="Introduce el correo de Tapo y tu contraseña.")
            return
        self.email = email
        self.password_entry.delete(0, tk.END)
        self.set_busy("Conectando y buscando sensores…")
        self.run_worker("connected", lambda: discover(email, password, self.ask_code))

    def show_sensors(self) -> None:
        if self.busy:
            return
        assert self.session is not None
        self.view = "sensors"
        self.clear(1)
        self.heading("02 / discovery", "Elige tu sensor", "Selecciona el dispositivo del que "
                     "quieres solicitar los datos de temperatura y humedad.")
        labels = [f"{i + 1}.  {export_tapo.display_name(s.get('nickname'))}  ·  "
                  f"{cloud_probe.safe_label(s.get('deviceModel') or s.get('model'))}"
                  for i, s in enumerate(self.session.sensors)]
        count_label = "SENSOR ENCONTRADO" if len(labels) == 1 else "SENSORES ENCONTRADOS"
        self.label(self.main, f"{len(labels)} {count_label}", 10, TEAL, True).pack(anchor="w")
        if labels:
            self.sensor_choice = ttk.Combobox(self.main, values=labels, state="readonly",
                                              font=("Segoe UI", 12))
            self.sensor_choice.current(0)
            self.sensor_choice.pack(fill="x", pady=(14, 8))
            self.action = self.button(self.main, "Continuar  →", self.show_export)
            self.action.pack(anchor="w", pady=(22, 0))
        else:
            self.label(self.main, "No se encontraron sensores T310 o T315.", 11, MUTED,
                       wraplength=570).pack(anchor="w", pady=20)
        self.button(self.main, "←  Cambiar de cuenta", self.show_connect, False).pack(
            anchor="w", pady=(15, 0))

    def show_export(self) -> None:
        if self.session is None:
            return
        index = self.sensor_choice.current()
        if not 0 <= index < len(self.session.sensors):
            return
        self.sensor = self.session.sensors[index]
        self.sensor_label = self.sensor_choice.get()
        self.view = "export"
        self.clear(2)
        self.heading("03 / exportación", "Prepara tu informe", "Tapo enviaría el informe al "
                     "correo de tu cuenta. La descarga del archivo aún no es automática.")
        self.label(self.main, self.sensor_label, 12, TEAL, True).pack(anchor="w", pady=(0, 5))
        today = date.today()
        self.label(self.main, "DESDE", 10, MUTED, True).pack(anchor="w", pady=(11, 6))
        self.start_entry = DatePicker(self.main, today)
        self.start_entry.pack(fill="x")
        self.label(self.main, "HASTA · INCLUIDO", 10, MUTED, True).pack(anchor="w", pady=(11, 6))
        self.end_entry = DatePicker(self.main, today)
        self.end_entry.pack(fill="x")
        self.zone_entry = self.entry(self.main, "ZONA HORARIA DEL SENSOR", "Europe/Madrid")
        self.label(self.main, "Máximo 31 días · Intervalos de 1 minuto · Hoy puede estar incompleto",
                   9, MUTED, wraplength=590).pack(anchor="w", pady=(12, 0))
        actions = tk.Frame(self.main, bg=BG)
        actions.pack(anchor="w", pady=(18, 0))
        self.action = self.button(actions, "Solicitar informe  →", self.submit)
        self.action.pack(side="left")
        back = self.button(actions, "←  Sensores", self.show_sensors, False)
        back.pack(side="left", padx=10)
        self.busy_controls = [self.action, back, self.start_entry, self.end_entry, self.zone_entry]
        self.status_line()

    def submit(self) -> None:
        if self.busy or self.session is None:
            return
        try:
            body = make_report(self.start_entry.get(), self.end_entry.get(),
                               self.zone_entry.get(), self.email)
        except ValueError as exc:
            self.status.config(text=str(exc))
            return
        if not messagebox.askyesno("Confirmar solicitud", f"Sensor: {self.sensor_label}\n"
                                   f"Fechas: {self.start_entry.get()} a {self.end_entry.get()}\n"
                                   f"Zona: {self.zone_entry.get()}\n\n"
                                   "Tapo intentará enviar el informe al correo de tu cuenta. "
                                   "¿Continuar?",
                                   parent=self):
            return
        session, sensor = self.session, self.sensor
        self.set_busy("Enviando una única solicitud a Tapo…")
        self.run_worker("exported", lambda: export_tapo.request_report(
            sensor, session.host, session.token, session.terminal, session.app_type,
            body, session.context))

    def set_busy(self, text: str) -> None:
        self.busy = True
        for widget in self.busy_controls:
            widget.config(state="disabled")
        self.status.config(text=text)

    def finish_busy(self) -> None:
        self.busy = False
        for widget in self.busy_controls:
            widget.config(state="normal")

    def run_worker(self, kind: str, operation: Any) -> None:
        def run() -> None:
            try:
                self.events.put((kind, operation()))
            except Exception:
                self.events.put(("error", kind))
        threading.Thread(target=run, daemon=True).start()

    def ask_code(self, mfa_type: int) -> str:
        event = threading.Event()
        result = [""]
        self.events.put(("mfa", (mfa_type, event, result)))
        event.wait()
        return result[0]

    def poll_events(self) -> None:
        if self.poll_job is not None:
            self.after_cancel(self.poll_job)
            self.poll_job = None
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "mfa":
                    mfa_type, event, result = value
                    self.pending_code = (event, result)
                    source = "tu correo" if mfa_type == 2 else "tu aplicación de autenticación"
                    code = simpledialog.askstring("Verificación Tapo", f"Introduce el código de {source}:",
                                                  show="•", parent=self)
                    result[0] = code or ""
                    self.pending_code = None
                    event.set()
                elif kind == "connected":
                    self.finish_busy()
                    session, status = value
                    if session is None:
                        self.status.config(text=f"No se pudo completar la conexión: {status}")
                    else:
                        self.session = session
                        self.show_sensors()
                elif kind == "exported":
                    self.finish_busy()
                    if value == 0:
                        self.status.config(text="Solicitud aceptada. Comprueba tu correo; "
                                           "la recepción y el contenido aún no están verificados.")
                    else:
                        self.status.config(text=f"Tapo rechazó la solicitud (código {value}).")
                elif kind == "error":
                    self.finish_busy()
                    if value == "exported":
                        self.status.config(text="Resultado desconocido: comprueba el correo antes "
                                           "de volver a enviar; Tapo podría haberla recibido.")
                    else:
                        self.status.config(text="No se pudo conectar o completar la lista de sensores. "
                                           "Comprueba tu cuenta, la APK y la conexión.")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.poll_job = self.after(100, self.poll_events)

    def close(self) -> None:
        if self.busy and self.view == "export" and not messagebox.askyesno(
            "Solicitud en curso", "Tapo podría recibir la solicitud aunque cierres la ventana. "
            "Comprueba el correo antes de volver a enviarla. ¿Cerrar?", parent=self
        ):
            return
        if self.pending_code is not None:
            self.pending_code[1][0] = ""
            self.pending_code[0].set()
        self.session = None
        if self.poll_job is not None:
            self.after_cancel(self.poll_job)
            self.poll_job = None
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
