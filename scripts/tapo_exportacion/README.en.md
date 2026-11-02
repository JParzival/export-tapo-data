# Tapo export prototype

[Español](README.md) · **English** · [← Back to the project](../../README.en.md)

A guide to running the simulation, checking access, and requesting an experimental report from the console. Console prompts are currently in Spanish.

> [!IMPORTANT]
> Cloud access, sensor discovery, and an export from the application have been tested with a real account. The user confirms that the file exported correctly and arrived by email. Tapo's internal API may change.

## 1. Local simulation

The simulation starts a temporary server on `127.0.0.1`, prepares one full day at one-minute resolution, sends a simulated request, and checks the response. It needs no account or internet access, sends no email, and does not read or modify historical data.

From the repository root, using the project environment:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

The flow, model fields, and endpoint path come from static analysis of Tapo 3.22.105 using REA. Acceptance by the simulated server does not prove Tapo will accept a request. The `.invalid` address and sensor identifier are fictional.

The user has confirmed a real export from the application and correct receipt of the file. This test does not establish behavior for all possible requests.

## 2. Experimental export request

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

The program signs in, asks for additional verification when required, and lists T310/T315 sensors. Select a sensor and up to 31 inclusive calendar dates. Today is allowed, so its data may be incomplete. The default time zone is `Europe/Madrid`; choose the sensor's zone if different. The requested resolution is 60 seconds. The 31-day limit is a prototype restriction, not a verified server limit.

The request is addressed to the account's own email only after typing `SI`. The client sends at most one request and never retries automatically; if the connection fails, receipt by Tapo is uncertain. Acceptance does not confirm email delivery or a complete file. Check your email before trying again. Attachments are not automatically downloaded or saved.

## 3. Check access from your computer

Run in your own terminal from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\cloud_probe.py
```

The program asks for the email and password in the console, hides the password, and does not save credentials or tokens. It connects to TP-Link over HTTPS without following redirects or retrying. Alongside the basic device list, it attempts region discovery, V2 authentication, and a count of T310/T315 sensors through the app's IoT query. Regional servers are checked against TP-Link domains; TLS certificates and signing configuration are read from the verified APK, with signing configuration kept in memory. Output is limited to counts, service names, and error codes, without service addresses, identifiers, or tokens. This command does not request exports and does not establish that the export API is available.

The service may require additional verification or reject this non-public protocol. If email verification is supported, the program requests a code and prompts for it once; it is neither displayed nor saved. If TOTP is offered, it asks for the authenticator app code. It does not register the computer as trusted or retry incorrect codes.

The program recognizes `MFAProcessId` and `mfaProcessId` and sends `MFAProcessId` and `MFAType` as in the Tapo CLI client. If no identifier is found, it stops before requesting a code and reports only the presence and type of predefined fields, not their values.

The IoT query uses `nbu.*` service identifiers from the APK. Any alternative regional application server returned by login is domain-validated. The verified APK is read from `assets/tapo/tapo-3.22.105.apk` at the project root, and its fingerprint is checked before use. The APK is excluded from Git and must be obtained separately for other copies. Existing historical data is not modified.
