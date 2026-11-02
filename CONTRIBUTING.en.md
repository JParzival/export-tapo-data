# Contributing

[Español](CONTRIBUTING.md) · **English** · [← Home](README.en.md)

Thank you for helping improve Export Tapo Data. The integration uses a non-public API. The user has confirmed a successful export and email delivery with a real account; this does not cover every scenario. Simulated tests do not establish service behavior.

## Set up the environment

With Python 3.12 or later and Tkinter, run from PowerShell at the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

Interface tests require a graphical session and working Tk; they may be skipped if unavailable. Tests require neither an account nor the APK. The Windows launcher is `launch_app.cmd`; see the [user guide](docs/USAGE.en.md) for its requirements and the APK needed for a real connection. Launchers for other systems have not been validated.

## Find your way around

| Path | Purpose |
| --- | --- |
| `scripts/tapo_exportacion/app.py` | Desktop interface and request flow. |
| `scripts/tapo_exportacion/i18n.py` | Spanish and English interface text. |
| `scripts/tapo_exportacion/cloud_probe.py` | Login, verification, and sensor discovery. |
| `scripts/tapo_exportacion/export_tapo.py` | Console request preparation and submission. |
| `scripts/tapo_exportacion/mock_tapo.py` | Local simulation without the real service. |
| `scripts/tapo_exportacion/test_*.py` | Unit, simulation, and interface tests. |

The [prototype guide](scripts/tapo_exportacion/README.en.md) explains the simulation and integration limits. `AGENTS.md` and `docs/agent-guides/` contain internal engineering instructions in English.

## Propose and verify changes

- Describe the problem, expected behavior, and reproduction steps using fictional data. Keep changes focused and update both documentation languages and interface text when applicable.
- Add tests for affected behavior and run the relevant checks; use the command above for the full suite. Run the simulation with `.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py`.
- Do not make real-account requests or share personal data without authorization. Never include passwords, codes, tokens, identifiers, exports, personal paths, or APKs in issues or contributions. Review ignored files too before publishing.
- Review the result and run `git diff --check`. State what could not be tested; distinguish simulation from real validation and avoid retries that could duplicate requests.

The project software is offered under the [PolyForm Noncommercial License 1.0.0](LICENSE); review its terms before using, modifying, or distributing the code. Contribute only material you have the right to provide under the project terms. Third-party materials, including the APK, have their own terms and are not covered by this license.
