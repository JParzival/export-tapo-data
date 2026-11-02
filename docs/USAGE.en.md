# User guide

[Español](USAGE.md) · **English** · [← Home](../README.en.md)

This guide covers running the experimental Windows application and requesting T310/T315 sensor reports. The user has confirmed a successful export and email delivery with a real account. The application does not download attachments automatically.

## 1. Prepare the project

You need Python 3.12 or later, Tkinter, and time-zone data. In PowerShell, from the project folder, you can create an environment and install the declared Windows dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The launcher uses `.venv` if present or the system `python` command otherwise. It displays a message if a requirement is missing. Tkinter must be available in the Python installation; installing project dependencies does not add it. This repository includes a Windows launcher; launchers for macOS and Linux have not been verified.

## 2. Prepare the APK for a real connection

Place a copy of the Tapo **3.22.105** APK, obtained separately and with authorization, at:

```text
assets/tapo/tapo-3.22.105.apk
```

Create the folders if necessary. The APK is not included in the repository. The program requires this SHA-256:

```text
a01fd475f378687d4be684741161df0f5e3daa274acb15303c44c0198b37b88f
```

From the project root, check it with `Get-FileHash .\assets\tapo\tapo-3.22.105.apk -Algorithm SHA256`. A match identifies the file expected by this prototype; it does not by itself establish provenance or grant distribution rights. The simulation and tests do not require the APK.

## 3. Open the application and request a report

1. Double-click `launch_app.cmd` and keep its command window open. The **ES / EN** selector changes the interface language for the session.
2. Enter your Tapo account email and password. If requested by the service, enter the verification code.
3. Select one or more T310/T315 sensors. Choose dates using the calendars and the sensor's time zone; the default is `Europe/Madrid`.
4. Review the range and submit the request. Both dates are included, with a maximum of 31 dates; today's data may be incomplete. The requested resolution is 60 seconds. The date limit belongs to this prototype and is not a confirmed Tapo limit.
5. Check each result and your account email, including the spam folder. Acceptance does not guarantee delivery or a complete file.

Requests for multiple sensors run sequentially with the same dates and time zone. If one cannot be confirmed, the process stops and identifies those not yet sent. **Check your email before repeating an uncertain request**, as Tapo may have received it. Returning to selection automatically marks the sensors not yet sent.

## Privacy and troubleshooting

The application does not save credentials or verification codes to files. Email and the session token remain in memory during use; the password is used to sign in and cleared from the visible field on connection. Data is sent to TP-Link services over HTTPS. This does not control what the operating system or other programs may retain.

- **The launcher reports missing requirements:** check your Python version, that `import tkinter` works, and that `requirements.txt` was installed in the selected Python. If `.venv` exists, the launcher uses it even if another Python is installed.
- **The APK is missing or its hash differs:** check its name, path, version, and hash. Do not alter the check to accept a different file.
- **No sensors appear or login fails:** check the account, connection, and additional verification. This integration uses a non-public API that may change; discovery does not prove export works.
- **A report does not arrive:** check your email and spam folder. A connection error can leave the result uncertain; do not retry blindly.

When asking for help, describe the steps, Python version, and error message without passwords, codes, tokens, email addresses, device identifiers, or sensor data. See the [console guide](../scripts/tapo_exportacion/README.en.md) for the simulation and diagnostic commands.
