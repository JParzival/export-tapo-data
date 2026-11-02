# Contribuir

**Español** · [English](CONTRIBUTING.en.md) · [← Inicio](README.md)

Gracias por ayudar a mejorar Export Tapo Data. La integración utiliza una API no pública. La persona usuaria ha confirmado una exportación correcta y la recepción del archivo por correo con una cuenta real; esto no cubre todos los escenarios. Las pruebas simuladas no demuestran el comportamiento del servicio.

## Preparar el entorno

Con Python 3.12 o posterior y Tkinter, desde PowerShell en la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

Las pruebas de interfaz requieren una sesión gráfica y Tk operativo; pueden omitirse si no están disponibles. No necesitan cuenta ni APK. El lanzador de Windows es `launch_app.cmd`; consulta la [guía de uso](docs/USAGE.md) para sus requisitos y la APK necesaria para conexión real. No se han validado lanzadores para otros sistemas.

## Orientarse en el código

| Ruta | Función |
| --- | --- |
| `scripts/tapo_exportacion/app.py` | Interfaz de escritorio y flujo de solicitudes. |
| `scripts/tapo_exportacion/i18n.py` | Textos de la interfaz en español e inglés. |
| `scripts/tapo_exportacion/cloud_probe.py` | Acceso, verificación y descubrimiento de sensores. |
| `scripts/tapo_exportacion/export_tapo.py` | Preparación y envío de solicitudes desde consola. |
| `scripts/tapo_exportacion/mock_tapo.py` | Simulación local sin servicio real. |
| `scripts/tapo_exportacion/test_*.py` | Pruebas unitarias, de simulación y de interfaz. |

La [guía del prototipo](scripts/tapo_exportacion/README.md) describe la simulación y los límites de la integración. `AGENTS.md` y `docs/agent-guides/` contienen instrucciones internas de ingeniería en inglés.

## Proponer y verificar cambios

- Describe el problema, el comportamiento esperado y la forma de reproducirlo con datos ficticios. Mantén los cambios centrados y actualiza ambas versiones de la documentación y los textos de interfaz cuando corresponda.
- Añade pruebas que comprueben el comportamiento afectado y ejecuta las relevantes; usa el comando de la sección anterior para el conjunto completo. La simulación se puede ejecutar con `.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py`.
- No realices solicitudes a una cuenta real ni compartas datos personales sin autorización. Nunca incluyas contraseñas, códigos, tokens, identificadores, exportaciones, rutas personales ni APK en incidencias o contribuciones. Los archivos ignorados también deben revisarse antes de publicar.
- Revisa el resultado y ejecuta `git diff --check`. Si algo no se ha podido probar, indícalo; distingue una prueba simulada de una validación real y evita reintentos que puedan duplicar solicitudes.

El software del proyecto se ofrece bajo la [PolyForm Noncommercial License 1.0.0](LICENSE); revisa sus condiciones antes de usar, modificar o compartir el código. Contribuye únicamente con material que tengas derecho a aportar bajo las condiciones del proyecto. Los materiales de terceros, incluida la APK, tienen sus propias condiciones y no quedan cubiertos por esta licencia.
