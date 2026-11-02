# export-tapo-data
Proyecto para construir una aplicación que facilite la exportación de datos de sensores TP-Link Tapo, a partir del prototipo existente en Python.

Prototipo en Python para solicitar por correo informes de temperatura y humedad de sensores Tapo T310/T315. La conexión a la nube y la detección de sensores se han probado con una cuenta real; **la solicitud de exportación y el contenido del archivo aún están pendientes de validación real**. No descarga los adjuntos automáticamente.

## Estado y próximos pasos

- La aplicación todavía no está implementada. Los scripts actuales son una base experimental de consola, no una aplicación terminada.
- Las pruebas locales comprueban la lógica y una simulación; no confirman el funcionamiento del servicio real ni la recepción o integridad de los datos.
- Antes de dar por completado el flujo, hay que validar una exportación real y comparar su archivo con una descarga manual, sin incluir credenciales ni datos privados en el repositorio.
- El tipo de aplicación, sus funcionalidades concretas, el tratamiento de los archivos y la distribución deben definirse con los requisitos de la conversación anterior, que no están recogidos aquí. No se presupone una tecnología ni automatización adicional.
- La integración actual depende de una API interna de Tapo y de una APK concreta; su disponibilidad y compatibilidad pueden cambiar.

## Preparación en Windows

Requiere Python 3.12 o posterior. Para conectarse a Tapo también necesita la APK de Tapo 3.22.105 previamente verificada: el prototipo la lee desde `%USERPROFILE%\.local\share\rea\targets\tapo-3.22.105\base.apk` y comprueba su huella SHA-256 antes de utilizarla. Las pruebas y la simulación locales no requieren la APK ni una cuenta.

Desde la raíz de este repositorio en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

Para probar la simulación local:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py
```

Para solicitar un informe real de un sensor por correo:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

El programa solicita las credenciales y, si corresponde, un código de verificación sin guardarlos. Permite elegir el sensor, un rango de hasta 31 fechas inclusivas y la zona horaria. Admite la fecha actual, por lo que sus datos pueden estar incompletos. Solo envía la solicitud al escribir `SI`. Si se pierde la conexión después del envío, comprueba el correo antes de repetirlo.

## Estructura

- `scripts/tapo_exportacion/`: prototipo, simulador y pruebas existentes.
- `docs/agent-guides/` y `AGENTS.md`: instrucciones para el trabajo en el repositorio.
- `pyproject.toml`: metadatos y configuración de análisis de código.
- `requirements.txt`: dependencia de zonas horarias en Windows.

Consulta [la documentación del prototipo](scripts/tapo_exportacion/README.md) para ver los detalles y las limitaciones.
