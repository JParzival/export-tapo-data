<div align="center">

# Export Tapo Data

**Your sensors, your data. A simpler way to export it.**

An experimental desktop application for exporting data from TP-Link Tapo sensors,
built on a Python prototype.

[Español](README.md) · **English**

[Status](#project-status) · [Getting started](#getting-started) · [Documentation](#documentation)

</div>

> [!IMPORTANT]
> **Experimental project.** Cloud login and sensor discovery have been tested with a real account, but **the export request and file contents have not yet been validated against the real service**. Local tests do not replace that validation.

## From sensors to your data

The application guides you through connection, selection of a **T310 or T315** sensor, and an email report request for temperature and humidity data. The console prototype is also available. Attachments are not downloaded automatically yet.

The integration uses an internal Tapo API and a specific APK version; either may change.

## Project status

| Step | Status |
| --- | --- |
| Cloud login and sensor discovery | Tested with a real account |
| Local simulation and tests | Available |
| Export request and received file | Real-world validation pending |
| Desktop application | Available; real export workflow awaits validation |
| Automatic attachment download | Not yet implemented |

The next technical milestone is to validate a real export and compare the received file with a manual download. Credentials and personal data must stay out of the repository.

## Getting started

You need **Python 3.12 or later**. To connect to Tapo's IoT services, place the verified Tapo 3.22.105 APK at `assets/tapo/tapo-3.22.105.apk`; the prototype checks its SHA-256 fingerprint before use. The APK is excluded from Git and is not included when cloning the repository. The local simulation and tests need neither an APK nor an account.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

### Try it offline

The simulation starts a local server and does not send email or modify historical data:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py
```

### Open the application

On Windows, double-click **`Abrir Tapo Data.cmd`** in the project folder. It uses the `.venv` environment if present, or the system Python otherwise. Python 3.12 or later, Tkinter and time-zone data are required; it displays a message if a requirement is missing. The command window stays open while the application is in use.

The interface is currently in Spanish and does not save passwords or verification codes.
In the export step, select the start and end dates from the calendars; the end date is inclusive.
Running the interface tests also requires a graphical session and a working Tk installation; those tests are skipped when Tk is unavailable.

### Request an experimental report

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

The program asks for credentials and, when needed, a verification code without saving them. Choose a sensor, time zone, and up to 31 inclusive dates; today's data may be incomplete. The request is sent only when you type `SI` and is not retried automatically. The console prompts are currently in Spanish.

> [!CAUTION]
> If the connection fails during submission, **check your email before trying again**: Tapo may have received the request. Acceptance does not guarantee email delivery or a complete file.

## Documentation

- [Prototype guide](scripts/tapo_exportacion/README.en.md): simulation, access, real requests, and limitations.
- `scripts/tapo_exportacion/`: console code and tests.
- `AGENTS.md` and `docs/agent-guides/`: repository working instructions.
- `pyproject.toml` and `requirements.txt`: metadata, configuration, and the Windows time-zone dependency.
