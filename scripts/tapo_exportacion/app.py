"""Desktop interface for the experimental Tapo export workflow."""

from __future__ import annotations

import calendar
import base64
import queue
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from datetime import date, datetime
from tkinter import messagebox, ttk
from typing import Any
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import cloud_probe
import export_tapo
import i18n

BG = "#0b0a25"
PANEL = "#121136"
FIELD = "#201e48"
TEXT = "#f4f4f4"
MUTED = "#b7b3d0"
TEAL = "#64d99a"
CYAN = "#41ddff"
AMBER = "#ffd326"

MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def rounded(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
            radius: int, fill: str, outline: str = "") -> int:
    """Draw a rounded surface using the native canvas."""
    points = (x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1)
    return canvas.create_polygon(points, smooth=True, splinesteps=20, fill=fill, outline=outline)


class ActionButton(tk.Frame):
    """A rounded surface with a native focusable button inside."""

    def __init__(self, parent: tk.Misc, text: str, command: Any, primary: bool) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        color = TEAL if primary else FIELD
        font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        width = font.measure(text) + 58
        height = font.metrics("linespace") + 24
        canvas = tk.Canvas(self, width=width, height=height, bd=0, highlightthickness=0,
                           bg=parent.cget("bg"))
        canvas.pack()
        rounded(canvas, 1, 1, width - 1, height - 1, 14, color)
        self.button = tk.Button(canvas, text=text, command=command, relief="flat", bd=0,
                                cursor="hand2", bg=color, fg=BG if primary else TEXT,
                                activebackground=color, activeforeground=BG if primary else TEXT,
                                disabledforeground="#35655b" if primary else MUTED,
                                font=font, highlightthickness=1, highlightbackground=color,
                                highlightcolor=CYAN)
        self.button.place(x=10, y=5, width=width - 20, height=height - 10)
        self.button._action_font = font

    def config(self, cnf: Any = None, **kwargs: Any) -> Any:
        if "state" in kwargs:
            self.button.config(state=kwargs.pop("state"))
        return super().config(cnf, **kwargs) if cnf or kwargs else None

    def __getitem__(self, key: str) -> Any:
        return self.button[key] if key == "state" else super().__getitem__(key)

    def invoke(self) -> Any:
        return self.button.invoke()


class SensorChoice(tk.Frame):
    """Scrollable multi-select sensor cards with keyboard and mouse support."""

    def __init__(self, parent: tk.Misc, labels: list[str]) -> None:
        super().__init__(parent, bg=BG)
        self.labels = labels
        self.selected: set[int] = set()
        self.active = 0
        self.row_height = 60
        self.access_list: tk.Listbox | None = None
        self.scroll: ttk.Scrollbar | None = None
        self.canvas = tk.Canvas(self, bg=BG, height=min(4, len(labels)) * self.row_height,
                                highlightthickness=0, bd=0, takefocus=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        style = ttk.Style(self)
        style.configure("Tapo.Vertical.TScrollbar", background="#504c78", troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED, lightcolor="#504c78",
                        darkcolor="#504c78")
        if len(labels) > 4:
            scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                   style="Tapo.Vertical.TScrollbar")
            scroll.pack(side="right", fill="y", padx=(8, 0))
            self.scroll = scroll
            self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.configure(scrollregion=(0, 0, 0, len(labels) * self.row_height))
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<Button-1>", self.click_row)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", lambda _event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda _event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Down>", lambda _event: self.move(1))
        self.canvas.bind("<Up>", lambda _event: self.move(-1))
        self.canvas.bind("<space>", lambda _event: self.toggle(self.active))
        self.canvas.bind("<Return>", lambda _event: self.toggle(self.active))
        self.canvas.bind("<FocusIn>", lambda _event: self.redraw())
        self.canvas.bind("<FocusOut>", lambda _event: self.redraw())

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 200)
        self.canvas.configure(scrollregion=(0, 0, width, len(self.labels) * self.row_height))
        for index, label in enumerate(self.labels):
            top = index * self.row_height + 3
            selected = index in self.selected
            focused = self.canvas.focus_get() == self.canvas and index == self.active
            rounded(self.canvas, 2, top, width - 3, top + 52, 13,
                    "#223e49" if selected else FIELD, CYAN if focused else "")
            self.canvas.create_oval(17, top + 14, 41, top + 38,
                                    fill=TEAL if selected else "#37345e",
                                    outline=TEAL if selected else "#7c789a", width=1)
            if selected:
                self.canvas.create_text(29, top + 26, text="✓", fill=BG,
                                        font=("Segoe UI", 10, "bold"))
            self.canvas.create_text(55, top + 26, text=label, fill=TEXT, anchor="w",
                                    width=max(100, width - 70), font=("Segoe UI", 10))

    def click_row(self, event: tk.Event) -> None:
        index = int(self.canvas.canvasy(event.y) // self.row_height)
        if 0 <= index < len(self.labels):
            self.canvas.focus_set()
            self.active = index
            self.toggle(index)

    def toggle(self, index: int) -> None:
        if index in self.selected:
            self.selected.remove(index)
        else:
            self.selected.add(index)
        self.redraw()

    def move(self, offset: int) -> str:
        self.active = max(0, min(len(self.labels) - 1, self.active + offset))
        self.canvas.yview_moveto(max(0, (self.active - 1) / max(1, len(self.labels))))
        self.redraw()
        return "break"

    def wheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(-int(event.delta / 120), "units")

    def curselection(self) -> tuple[int, ...]:
        if self.access_list is not None:
            return tuple(int(index) for index in self.access_list.curselection())
        return tuple(sorted(self.selected))

    def get(self, index: int) -> str:
        return self.labels[index]

    def selection_set(self, first: int, last: int | None = None) -> None:
        stop = first if last is None else last
        self.selected.update(range(first, min(stop + 1, len(self.labels))))
        if self.access_list is not None:
            self.access_list.selection_set(first, stop)
        self.redraw()

    def selection_clear(self, first: int, last: int | str | None = None) -> None:
        stop = len(self.labels) - 1 if last == tk.END else (first if last is None else last)
        self.selected.difference_update(range(first, int(stop) + 1))
        if self.access_list is not None:
            self.access_list.selection_clear(first, stop)
        self.redraw()

    def use_accessible_list(self) -> None:
        """Offer native list semantics to assistive technologies."""
        if self.access_list is not None:
            return
        selected = self.curselection()
        self.canvas.pack_forget()
        self.access_list = tk.Listbox(self, selectmode="multiple", exportselection=False,
                                     bg=FIELD, fg=TEXT, selectbackground=TEAL,
                                     selectforeground=BG, font=("Segoe UI", 11),
                                     height=min(6, len(self.labels)), activestyle="dotbox")
        for label in self.labels:
            self.access_list.insert(tk.END, label)
        for index in selected:
            self.access_list.selection_set(index)
        if self.scroll is not None:
            self.scroll.configure(command=self.access_list.yview)
            self.access_list.configure(yscrollcommand=self.scroll.set)
        self.access_list.pack(side="left", fill="both", expand=True)
        self.access_list.focus_set()


class DatePicker(tk.Button):
    """Read-only date selector backed by a keyboard-accessible calendar dialog."""

    def __init__(self, parent: tk.Misc, initial: date, language: str = "es") -> None:
        self.selected = initial
        self.language = language
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
        shown = (f"{value.day:02d} {i18n.MONTHS_EN[value.month - 1][:3]} {value.year}"
                 if self.language == "en" else f"{value:%d/%m/%Y}")
        self.configure(text=f"{shown}     ▾")

    def open_calendar(self) -> None:
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return
        popup = tk.Toplevel(self)
        self.popup = popup
        popup.title(i18n.translate(self.language, "Seleccionar fecha"))
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
        months = i18n.MONTHS_EN if self.language == "en" else MONTHS
        tk.Label(header, text=f"{months[self.month - 1].capitalize()} {self.year}",
                 bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(expand=True)
        days = ("M", "T", "W", "T", "F", "S", "S") if self.language == "en" else (
            "L", "M", "X", "J", "V", "S", "D")
        for column, name in enumerate(days):
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


def send_reports(session: Session, sensors: list[dict[str, Any]], body: dict[str, Any],
                 progress: Any) -> list[tuple[str, int | None]]:
    """Send once per sensor, stopping on an uncertain result to avoid duplicates."""
    outcomes: list[tuple[str, int | None]] = []
    for index, sensor in enumerate(sensors):
        progress(index + 1, len(sensors))
        try:
            code = export_tapo.request_report(sensor, session.host, session.token,
                                              session.terminal, session.app_type,
                                              body.copy(), session.context)
        except Exception:
            outcomes.append(("unknown", None))
            outcomes.extend(("not_sent", None) for _ in sensors[index + 1:])
            break
        outcomes.append(("accepted" if code == 0 else "rejected", code))
    return outcomes


class App(tk.Tk):
    """A small, non-blocking desktop wizard for discovery and export."""

    def __init__(self) -> None:
        super().__init__()
        self.language = "es"
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
        self.selection_indices: list[int] | None = None
        self.report_form: tuple[date, date, str] | None = None
        self.build_shell()
        self.show_connect()
        self.poll_job = self.after(100, self.poll_events)

    def build_shell(self) -> None:
        sidebar = tk.Frame(self, bg=PANEL, width=228, padx=26, pady=32)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.logo = self.load_tapo_logo()
        if self.logo is not None:
            tk.Label(sidebar, image=self.logo, bg=PANEL).pack(anchor="w")
        tk.Label(sidebar, text="tapo data", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(sidebar, text="SENSOR STUDIO", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(1, 55))
        self.steps: list[tk.Label] = []
        for text in ("01    Conexión", "02    Sensores", "03    Exportación"):
            label = tk.Label(sidebar, text=text, bg=PANEL, fg=MUTED,
                             font=("Segoe UI", 11, "bold"), pady=12)
            label.pack(anchor="w")
            self.steps.append(label)
        self.disclaimer = tk.Label(sidebar, text=self.tr("No estamos asociados ni afiliados a Tapo o TP-Link."),
                                   bg=PANEL, fg=MUTED, wraplength=170, justify="left", anchor="w",
                                   font=("Segoe UI", 8))
        self.disclaimer.pack(side="bottom", anchor="w")
        language_frame = tk.Frame(sidebar, bg=PANEL)
        language_frame.pack(side="bottom", anchor="w", pady=(0, 16))
        self.language_buttons = []
        for language, label in (("es", "ES"), ("en", "EN")):
            button = tk.Button(language_frame, text=label, command=lambda code=language: self.change_language(code),
                               bg=FIELD, fg=TEXT, relief="flat", padx=9, pady=5,
                               font=("Segoe UI", 9, "bold"), activebackground=TEAL)
            button.pack(side="left", padx=(0, 6))
            self.language_buttons.append(button)
        self.language_buttons[0].config(bg=TEAL, fg=BG)
        self.main = tk.Frame(self, bg=BG, padx=54, pady=31)
        self.main.pack(side="left", fill="both", expand=True)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEAL, borderwidth=0, padding=9)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", TEXT)])
        style.configure("Tapo.Horizontal.TProgressbar", troughcolor=FIELD,
                        background=TEAL, bordercolor=BG, lightcolor=TEAL,
                        darkcolor=TEAL, thickness=4)

    def load_tapo_logo(self) -> tk.PhotoImage | None:
        """Load the local icon or the PNG icon embedded in the verified APK."""
        try:
            path = Path(__file__).resolve().parents[2] / "assets" / "tapo" / "tapo-logo.png"
            if path.is_file():
                return tk.PhotoImage(file=str(path)).subsample(2, 2)
            with ZipFile(cloud_probe.apk_path()) as archive:
                data = archive.read("res/drawable-xxhdpi-v4/widget_tapo_icon.png")
            return tk.PhotoImage(data=base64.b64encode(data)).subsample(2, 2)
        except (OSError, ValueError, KeyError, BadZipFile, tk.TclError):
            return None

    def tr(self, text: str) -> str:
        return i18n.translate(self.language, text)

    def change_language(self, language: str) -> None:
        if language == self.language or self.busy:
            return
        view = self.view
        email = self.email_entry.get() if view == "connect" else None
        password = self.password_entry.get() if view == "connect" else None
        if view == "sensors" and self.session and self.session.sensors:
            self.selection_indices = list(self.sensor_choice.curselection())
        if view == "export":
            self.report_form = (date.fromisoformat(self.start_entry.get()),
                                date.fromisoformat(self.end_entry.get()), self.zone_entry.get())
        self.language = language
        self.title("Tapo Data · Sensor export" if language == "en" else "Tapo Data · Exportación de sensores")
        for button, code in zip(self.language_buttons, ("es", "en")):
            button.config(bg=TEAL if code == language else FIELD, fg=BG if code == language else TEXT)
        self.disclaimer.config(text=self.tr("No estamos asociados ni afiliados a Tapo o TP-Link."))
        names = ("01    Connection", "02    Sensors", "03    Export") if language == "en" else (
            "01    Conexión", "02    Sensores", "03    Exportación")
        for label, text in zip(self.steps, names):
            label.config(text=text)
        if view == "connect":
            self.email = email or ""
            self.show_connect()
            self.password_entry.insert(0, password or "")
        elif view == "sensors":
            self.show_sensors()
        elif view == "export":
            self.show_sensors()
            self.show_export()
        elif view == "results":
            selected = self.selection_indices
            if self.report_form is not None:
                start, end, zone = self.report_form
                separator = "to" if self.language == "en" else "a"
                self.report_range = f"{start.isoformat()} {separator} {end.isoformat()} · {zone}"
            self.show_results(self.last_outcomes)
            self.selection_indices = selected

    def clear(self, step: int) -> None:
        for child in self.main.winfo_children():
            child.destroy()
        for i, label in enumerate(self.steps):
            label.configure(fg=TEAL if i == step else MUTED)

    def label(self, parent: tk.Misc, text: str, size: int = 11, color: str = TEXT,
              bold: bool = False, bg: str = BG, **kwargs: Any) -> tk.Label:
        return tk.Label(parent, text=self.tr(text), bg=bg, fg=color, anchor="w", justify="left",
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)

    def heading(self, eyebrow: str, title: str, subtitle: str) -> None:
        self.label(self.main, self.tr(eyebrow).upper(), 9, TEAL, True).pack(anchor="w", pady=(0, 12))
        self.label(self.main, title, 27, bold=True).pack(anchor="w")
        self.label(self.main, subtitle, 11, MUTED, wraplength=590).pack(anchor="w", pady=(8, 22))

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

    def button(self, parent: tk.Misc, text: str, command: Any, primary: bool = True) -> ActionButton:
        return ActionButton(parent, self.tr(text), command, primary)

    def status_line(self, text: str = "") -> None:
        self.status = self.label(self.main, text, 10, MUTED, wraplength=590)
        self.status.pack(anchor="w", pady=(16, 0))
        self.progress = ttk.Progressbar(self.main, mode="indeterminate", length=250,
                                        style="Tapo.Horizontal.TProgressbar")

    def show_connect(self) -> None:
        if self.busy:
            return
        self.view = "connect"
        self.session = None
        self.selection_indices = None
        self.report_form = None
        self.clear(0)
        self.heading("01  /  BIENVENIDO", "Tus sensores, más cerca.", "Conecta tu cuenta Tapo "
                     "para encontrar tus sensores y preparar tus informes.")
        form = tk.Frame(self.main, bg=BG)
        form.pack(fill="x")
        self.email_entry = self.entry(form, "CORREO DE TAPO", self.email)
        self.password_entry = self.entry(form, "CONTRASEÑA", secret=True)
        self.action = self.button(self.main, "Encontrar mis sensores   →", self.connect)
        self.busy_controls = [self.action, self.email_entry, self.password_entry]
        self.action.pack(anchor="w", pady=(28, 0))
        self.status_line("Tus credenciales no se guardan. Tapo puede solicitar un código de verificación.")
        self.email_entry.focus_set()

    def connect(self) -> None:
        if self.busy:
            return
        email, password = self.email_entry.get().strip(), self.password_entry.get()
        if not email or "@" not in email or not password:
            self.status.config(text=self.tr("Introduce el correo de Tapo y tu contraseña."), fg=AMBER)
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
        self.heading("02 / discovery", "Elige tus sensores", "Selecciona uno o varios sensores. "
                     "Todos utilizarán las mismas fechas y zona horaria.")
        labels = [f"{i + 1}.  {self.tr(export_tapo.display_name(s.get('nickname')))}  ·  "
                  f"{self.tr(cloud_probe.safe_label(s.get('deviceModel') or s.get('model')))}"
                  for i, s in enumerate(self.session.sensors)]
        count_label = self.tr("SENSOR ENCONTRADO" if len(labels) == 1 else "SENSORES ENCONTRADOS")
        self.label(self.main, f"{len(labels)} {count_label}", 10, TEAL, True).pack(anchor="w")
        if labels:
            self.sensor_choice = SensorChoice(self.main, labels)
            self.sensor_choice.pack(fill="x", pady=(12, 6))
            for index in self.selection_indices if self.selection_indices is not None else [0]:
                if index < len(labels):
                    self.sensor_choice.selection_set(index)
            self.label(self.main, "Selecciona las tarjetas que quieras incluir.",
                       10, MUTED).pack(anchor="w", pady=(0, 4))
            self.button(self.main, "Selector accesible", self.sensor_choice.use_accessible_list,
                        False).pack(anchor="w", pady=(2, 0))
            self.selection_status = self.label(self.main, "", 10, AMBER)
            self.selection_status.pack(anchor="w")
            self.action = self.button(self.main, "Continuar  →", self.show_export)
            self.action.pack(anchor="w", pady=(10, 0))
        else:
            self.label(self.main, "No se encontraron sensores T310 o T315.", 11, MUTED,
                       wraplength=570).pack(anchor="w", pady=20)
        self.account_back = self.button(self.main, "←  Cambiar de cuenta", self.show_connect, False)
        self.account_back.pack(anchor="w", pady=(15, 0))

    def show_export(self) -> None:
        if self.session is None:
            return
        indices = list(self.sensor_choice.curselection())
        if not indices:
            self.selection_status.config(text=self.tr("Selecciona al menos un sensor para continuar."))
            return
        self.selection_indices = indices
        self.sensors = [self.session.sensors[i] for i in indices]
        self.sensor_labels = [self.sensor_choice.get(i) for i in indices]
        identifiers = [sensor.get("thingName") for sensor in self.sensors]
        if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)
               for value in identifiers) or (
            len(set(identifiers)) != len(identifiers)
        ):
            self.selection_status.config(text=self.tr("La selección contiene sensores sin identificador válido "
                                         "o duplicados. No se enviará ninguna solicitud."))
            return
        self.view = "export"
        self.clear(2)
        self.heading("03 / exportación", "Prepara tu informe", "Tapo enviaría el informe al "
                     "correo de tu cuenta. La descarga del archivo aún no es automática.")
        count = len(self.sensors)
        if self.language == "en":
            selection_summary = "1 sensor selected" if count == 1 else f"{count} sensors selected"
        else:
            selection_summary = "1 sensor seleccionado" if count == 1 else f"{count} sensores seleccionados"
        self.label(self.main, "●  " + selection_summary, 11, TEAL, True).pack(anchor="w", pady=(0, 5))
        self.label(self.main, "Puedes revisar o cambiar tu selección antes de enviar.",
                   9, MUTED).pack(anchor="w")
        today = date.today()
        start, end, zone = self.report_form or (today, today, "Europe/Madrid")
        self.label(self.main, "DESDE", 10, MUTED, True).pack(anchor="w", pady=(11, 6))
        self.start_entry = DatePicker(self.main, start, self.language)
        self.start_entry.pack(fill="x")
        self.label(self.main, "HASTA · INCLUIDO", 10, MUTED, True).pack(anchor="w", pady=(11, 6))
        self.end_entry = DatePicker(self.main, end, self.language)
        self.end_entry.pack(fill="x")
        self.zone_entry = self.entry(self.main, "ZONA HORARIA DEL SENSOR", zone)
        self.label(self.main, "Máximo 31 días · Intervalos de 1 minuto · Hoy puede estar incompleto",
                   9, MUTED, wraplength=590).pack(anchor="w", pady=(12, 0))
        actions = tk.Frame(self.main, bg=BG)
        actions.pack(anchor="w", pady=(18, 0))
        self.action = self.button(actions, "Solicitar informes  →", self.submit)
        self.action.pack(side="left")
        back = self.button(actions, "←  Sensores", self.back_to_sensors, False)
        back.pack(side="left", padx=10)
        self.busy_controls = [self.action, back, self.start_entry, self.end_entry, self.zone_entry]
        self.status_line()

    def back_to_sensors(self) -> None:
        if self.busy:
            return
        self.report_form = (date.fromisoformat(self.start_entry.get()),
                            date.fromisoformat(self.end_entry.get()), self.zone_entry.get())
        self.show_sensors()

    def submit(self) -> None:
        if self.busy or self.session is None:
            return
        try:
            body = make_report(self.start_entry.get(), self.end_entry.get(),
                               self.zone_entry.get(), self.email)
        except ValueError as exc:
            self.status.config(text=self.tr(str(exc)), fg=AMBER)
            return
        sensor_summary = "\n".join(self.sensor_labels)
        sensor_word = "Sensors" if self.language == "en" else "Sensores"
        date_word = "Dates" if self.language == "en" else "Fechas"
        zone_word = "Zone" if self.language == "en" else "Zona"
        to_word = "to" if self.language == "en" else "a"
        if not self.confirm_requests(f"{sensor_word} ({len(self.sensors)}):\n"
                                     f"{sensor_summary}\n"
                                     f"{date_word}: {self.start_entry.get()} {to_word} {self.end_entry.get()}\n"
                                     f"{zone_word}: {self.zone_entry.get()}"):
            return
        session, sensors = self.session, list(self.sensors)
        self.report_form = (date.fromisoformat(self.start_entry.get()),
                            date.fromisoformat(self.end_entry.get()), self.zone_entry.get())
        self.report_range = f"{self.start_entry.get()} {to_word} {self.end_entry.get()} · {self.zone_entry.get()}"
        self.set_busy("Preparando solicitudes…")
        self.run_worker("exported", lambda: send_reports(
            session, sensors, body, lambda current, total:
            self.events.put(("progress", (current, total)))))

    def confirm_requests(self, summary: str) -> bool:
        """Confirm the complete batch before any request is sent."""
        dialog = tk.Toplevel(self)
        dialog.title(self.tr("Confirmar solicitudes"))
        dialog.configure(bg=PANEL, padx=28, pady=24)
        dialog.transient(self)
        dialog.resizable(False, False)
        accepted = [False]
        self.label(dialog, "ÚLTIMO PASO", 9, TEAL, True, bg=PANEL).pack(anchor="w")
        self.label(dialog, "¿Todo listo?", 22, TEXT, True, bg=PANEL).pack(anchor="w", pady=(6, 8))
        self.label(dialog, "Se enviará una solicitud por sensor, una a una.",
                   10, MUTED, bg=PANEL, wraplength=440).pack(anchor="w", pady=(0, 14))
        detail_frame = tk.Frame(dialog, bg=FIELD)
        detail_frame.pack(fill="x")
        line_count = len(summary.splitlines())
        details = tk.Text(detail_frame, bg=FIELD, fg=TEXT, wrap="word", relief="flat",
                          height=max(4, min(7, line_count)),
                          width=52, padx=12, pady=10, font=("Segoe UI", 10))
        detail_scroll = ttk.Scrollbar(detail_frame, command=details.yview,
                                      style="Tapo.Vertical.TScrollbar")
        details.configure(yscrollcommand=detail_scroll.set)
        details.insert("1.0", summary)
        details.configure(state="disabled")
        if line_count > 7 or any(len(line) > 45 for line in summary.splitlines()):
            detail_scroll.pack(side="right", fill="y")
        details.pack(side="left", fill="both", expand=True)
        self.label(dialog, "Tapo intentará enviar los informes al correo de tu cuenta.",
                   10, MUTED, bg=PANEL, wraplength=440).pack(anchor="w", pady=(14, 4))
        buttons = tk.Frame(dialog, bg=PANEL)
        buttons.pack(anchor="w", pady=(14, 0))

        def accept() -> None:
            accepted[0] = True
            dialog.destroy()

        self.button(buttons, "Enviar solicitudes  →", accept).pack(side="left", padx=(0, 8))
        cancel = self.button(buttons, "Cancelar", dialog.destroy, False)
        cancel.pack(side="left")
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = max(0, self.winfo_rootx() + (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = max(0, self.winfo_rooty() + (self.winfo_height() - dialog.winfo_reqheight()) // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        cancel.focus_set()
        self.wait_window(dialog)
        return accepted[0]

    def show_results(self, outcomes: list[tuple[str, int | None]]) -> None:
        self.last_outcomes = outcomes
        previous_indices = self.selection_indices or []
        self.selection_indices = [index for index, (state, _) in zip(previous_indices, outcomes)
                                  if state == "not_sent"]
        self.view = "results"
        self.clear(2)
        self.heading("03 / resultado", "Resultado de solicitudes", "Revisa el resultado de cada sensor. "
                     "La aceptación no confirma la recepción ni el contenido del archivo.")
        self.label(self.main, self.report_range, 10, TEAL, True).pack(anchor="w", pady=(0, 10))
        container = tk.Frame(self.main, bg=BG)
        container.pack(fill="both", expand=True)
        results = tk.Text(container, bg=FIELD, fg=TEXT, wrap="word", relief="flat",
                          font=("Segoe UI", 11), padx=12, pady=12, height=8)
        scroll = tk.Scrollbar(container, command=results.yview)
        results.configure(yscrollcommand=scroll.set)
        results.tag_configure("accepted", foreground=TEAL)
        results.tag_configure("rejected", foreground=AMBER)
        results.tag_configure("unknown", foreground=AMBER)
        results.tag_configure("not_sent", foreground=MUTED)
        scroll.pack(side="right", fill="y")
        results.pack(side="left", fill="both", expand=True)
        descriptions = {"accepted": "Aceptada · comprueba el correo",
                        "unknown": "Resultado desconocido · comprueba el correo antes de repetir",
                        "not_sent": "No enviada · se detuvo el proceso",
                        "rejected": "Rechazada"}
        for label, (state, code) in zip(self.sensor_labels, outcomes):
            detail = self.tr(descriptions[state])
            if state == "rejected":
                detail += f" ({'code' if self.language == 'en' else 'código'} {code})"
            results.insert(tk.END, f"{label}\n")
            results.insert(tk.END, f"{detail}\n\n", state)
        results.configure(state="disabled")
        self.results = results
        self.label(self.main, "Al volver se marcan solo los no enviados. Si un resultado es "
                   "desconocido, comprueba el correo antes de repetir.",
                   10, AMBER, wraplength=590).pack(anchor="w", pady=(12, 0))
        self.button(self.main, "←  Volver a sensores", self.show_sensors, False).pack(
            anchor="w", pady=(12, 0))

    def set_busy(self, text: str) -> None:
        self.busy = True
        for button in self.language_buttons:
            button.config(state="disabled")
        for widget in self.busy_controls:
            widget.config(state="disabled")
        self.status.config(text=self.tr(text), fg=TEAL)
        self.progress.pack(anchor="w", pady=(8, 0))
        self.progress.start(15)

    def finish_busy(self) -> None:
        self.busy = False
        for button in self.language_buttons:
            button.config(state="normal")
        self.progress.stop()
        self.progress.pack_forget()
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

    def prompt_verification(self, mfa_type: int) -> str:
        """Prompt for the one-time code without displaying or storing it."""
        dialog = tk.Toplevel(self)
        dialog.title(self.tr("Verificación Tapo"))
        dialog.configure(bg=PANEL, padx=28, pady=24)
        dialog.transient(self)
        dialog.resizable(False, False)
        result = [""]
        self.label(dialog, "CONEXIÓN SEGURA", 9, TEAL, True, bg=PANEL).pack(anchor="w")
        self.label(dialog, "Verifica tu cuenta", 22, TEXT, True, bg=PANEL).pack(anchor="w", pady=(6, 8))
        source = "tu correo" if mfa_type == 2 else "tu aplicación de autenticación"
        prompt = ("Enter the code from your email." if mfa_type == 2 else
                  "Enter the code from your authenticator app.") if self.language == "en" else f"Introduce el código de {source}."
        self.label(dialog, prompt, 10, MUTED,
                   bg=PANEL, wraplength=440).pack(anchor="w", pady=(0, 10))
        code = tk.Entry(dialog, bg=FIELD, fg=TEXT, insertbackground=TEAL, show="•", relief="flat",
                        font=("Segoe UI", 14), width=30, highlightthickness=1,
                        highlightbackground=FIELD, highlightcolor=CYAN)
        code.pack(fill="x", ipady=10)
        buttons = tk.Frame(dialog, bg=PANEL)
        buttons.pack(anchor="w", pady=(20, 0))

        def accept() -> None:
            result[0] = code.get()
            code.delete(0, tk.END)
            dialog.destroy()

        self.button(buttons, "Continuar  →", accept).pack(side="left", padx=(0, 8))
        self.button(buttons, "Cancelar", dialog.destroy, False).pack(side="left")
        dialog.bind("<Return>", lambda _event: accept())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = max(0, self.winfo_rootx() + (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = max(0, self.winfo_rooty() + (self.winfo_height() - dialog.winfo_reqheight()) // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        code.focus_set()
        self.wait_window(dialog)
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
                    code = self.prompt_verification(mfa_type)
                    result[0] = code or ""
                    self.pending_code = None
                    event.set()
                elif kind == "connected":
                    self.finish_busy()
                    session, status = value
                    if session is None:
                        message = ("Could not complete the connection. Check your account, "
                                   "verification code, APK and connection.") if self.language == "en" else f"No se pudo completar la conexión: {status}"
                        self.status.config(text=message, fg=AMBER)
                    else:
                        self.session = session
                        self.show_sensors()
                elif kind == "progress":
                    current, total = value
                    message = (f"Sending request {current} of {total}…" if self.language == "en" else
                               f"Enviando solicitud {current} de {total}…")
                    self.status.config(text=message, fg=TEAL)
                elif kind == "exported":
                    self.finish_busy()
                    self.show_results(value)
                elif kind == "error":
                    self.finish_busy()
                    if value == "exported":
                        self.status.config(text=self.tr("Resultado desconocido: comprueba el correo antes "
                                           "de volver a enviar; Tapo podría haberla recibido."), fg=AMBER)
                    else:
                        self.status.config(text=self.tr("No se pudo conectar o completar la lista de sensores. "
                                           "Comprueba tu cuenta, la APK y la conexión."), fg=AMBER)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.poll_job = self.after(100, self.poll_events)

    def close(self) -> None:
        if self.busy and self.view == "export" and not messagebox.askyesno(
            self.tr("Solicitud en curso"), self.tr("Tapo podría recibir la solicitud aunque cierres la ventana. "
            "Comprueba el correo antes de volver a enviarla. ¿Cerrar?"), parent=self
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
