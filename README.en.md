<div align="center">

# Export Tapo Data

**Your sensors, your data. A simpler way to export it.**

An experimental desktop application for exporting data from TP-Link Tapo sensors,
built on a Python prototype.

[Español](README.md) · **English**

[Status](#project-status) · [Getting started](#getting-started) · [Documentation](#documentation)

</div>

## From sensors to your data

The application guides you through connection, selection of one or more **T310 or T315** sensors, and email report requests for temperature and humidity data. The console prototype is also available. Attachments are not downloaded automatically yet.

The integration uses an internal Tapo API and a specific APK version; either may change.

## Project status

| Step | Status |
| --- | --- |
| Cloud login and sensor discovery | Tested with a real account |
| Local simulation and tests | Available |
| Export request and received file | Confirmed |
| Desktop application | Available; real export tested |
| Automatic attachment download | Not yet implemented |

This confirms the tested case, not every sensor, date range, or scenario. Credentials and personal data must stay out of the repository.

## Getting started

On Windows, double-click **`launch_app.cmd`** in the project folder. You need **Python 3.12 or later**, Tkinter, and time-zone data. The launcher uses `.venv` if present or the system Python otherwise, and displays a message if a requirement is missing. The command window stays open while the application runs.

To connect to Tapo, place the Tapo 3.22.105 APK at `assets/tapo/tapo-3.22.105.apk`; the program checks its SHA-256 fingerprint. The APK is not distributed with the repository. See the [user guide](docs/USAGE.en.md) for environment setup, APK verification, and troubleshooting. The simulation and tests need neither an APK nor an account.

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

The interface supports Spanish and English via the **ES / EN** selector and does not save passwords or verification codes. The language remains selected during the session.
The icon may be loaded from a local file or extracted from the checked APK; these assets are not distributed with the repository. This application is independent and is not affiliated with Tapo or TP-Link.
In the export step, select the start and end dates from the calendars; the end date is inclusive.
You can select several sensors: one report is requested per sensor, sequentially, using the same dates and time zone. Results are displayed individually. If a request cannot be confirmed, the process stops and identifies sensors not yet sent; check your email before requesting the uncertain report again. Returning to selection automatically marks only sensors that have not yet been sent.
Running the interface tests also requires a graphical session and a working Tk installation; those tests are skipped when Tk is unavailable.

### Request an experimental report

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

The program asks for credentials and, when needed, a verification code without saving them. Choose a sensor, time zone, and up to 31 inclusive dates; today's data may be incomplete. The request is sent only when you type `SI` and is not retried automatically. The console prompts are currently in Spanish.

> [!CAUTION]
> If the connection fails during submission, **check your email before trying again**: Tapo may have received the request. Acceptance does not guarantee email delivery or a complete file.

## Documentation

- [User guide](docs/USAGE.en.md): setup, the application, privacy, and troubleshooting.
- [Contributing guide](CONTRIBUTING.en.md): structure, development, and tests.
- [Prototype guide](scripts/tapo_exportacion/README.en.md): simulation, access, real requests, and limitations.
- `scripts/tapo_exportacion/`: console code and tests.
- `AGENTS.md` and `docs/agent-guides/`: internal repository working instructions, in English.
- `pyproject.toml` and `requirements.txt`: metadata, configuration, and the Windows time-zone dependency.

## License

The project software is offered under the [PolyForm Noncommercial License 1.0.0](LICENSE). It permits use, modification, and distribution for purposes allowed by the license, including noncommercial purposes; the text also expressly permits certain organizations and uses. Commercial purposes outside its permissions require separate authorization from the relevant rights holders.

The software is source-available, but its commercial restriction means it is not open source under the Open Source Initiative definition. The project license does not grant rights to the Tapo APK, trademarks, or other third-party materials. The original English text in `LICENSE` governs over this summary.
