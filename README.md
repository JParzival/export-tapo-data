<div align="center">

# Export Tapo Data

**Tus sensores, tus datos. Una forma más sencilla de exportarlos.**

Una aplicación de escritorio experimental para exportar datos de sensores TP-Link Tapo,
construida sobre un prototipo en Python.

**Español** · [English](README.en.md)

[Estado](#estado-del-proyecto) · [Primeros pasos](#primeros-pasos) · [Documentación](#documentación)

</div>

> [!IMPORTANT]
> **Proyecto experimental.** Se han probado el acceso, la detección de sensores y la exportación con una cuenta real. La persona usuaria confirma que el archivo se exportó correctamente y llegó a su correo. La integración depende de una API no pública que puede cambiar.

## De los sensores a tus datos

La aplicación guía la conexión, la selección de uno o varios sensores **T310 o T315** y la solicitud de informes de temperatura y humedad por correo. También se conserva el prototipo de consola. Todavía no descarga los archivos adjuntos automáticamente.

La integración utiliza una API interna de Tapo y una versión concreta de su APK; ambas pueden cambiar.

## Estado del proyecto

| Paso | Estado |
| --- | --- |
| Acceso a la nube y detección de sensores | Probados con una cuenta real |
| Simulación y pruebas locales | Disponibles |
| Solicitud de exportación y archivo recibido | Funcionamiento confirmado |
| Aplicación de escritorio | Disponible; exportación real probada |
| Descarga automática de adjuntos | Aún no implementada |

Esta comprobación confirma el caso probado, no todos los sensores, rangos o escenarios. Las credenciales y los datos personales deben mantenerse fuera del repositorio.

## Primeros pasos

En Windows, haz doble clic en **`launch_app.cmd`**, en la carpeta del proyecto. Necesitas **Python 3.12 o posterior**, Tkinter y datos de zonas horarias. El lanzador utiliza `.venv` si existe o, en su defecto, el Python del sistema; muestra un aviso si falta algún requisito. La ventana de comandos permanece abierta mientras se usa la aplicación.

Para conectar con Tapo, coloca la APK de Tapo 3.22.105 en `assets/tapo/tapo-3.22.105.apk`; el programa comprueba su huella SHA-256. La APK no se distribuye con el repositorio. Consulta la [guía de uso](docs/USAGE.md) para preparar el entorno, comprobar la APK y resolver problemas. La simulación y las pruebas no necesitan APK ni cuenta.

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

### Pruébalo sin conexión

La simulación crea un servidor local y no envía correos ni modifica históricos:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py
```

### Abre la aplicación

La interfaz permite elegir español o inglés con el selector **ES / EN** y no guarda la contraseña ni los códigos de verificación. El idioma se mantiene durante la sesión.
El icono puede cargarse de un archivo local o extraerse de la APK comprobada; estos recursos no se distribuyen con el repositorio. La aplicación es independiente y no está afiliada a Tapo ni a TP-Link.
En el paso de exportación, selecciona las fechas inicial y final en sus calendarios; la fecha final está incluida.
Puedes seleccionar varios sensores: se solicita un informe por cada uno, secuencialmente y con las mismas fechas y zona horaria. Se muestra el resultado individual. Si no puede confirmarse una solicitud, el proceso se detiene y señala los sensores que aún no se han enviado; comprueba el correo antes de volver a solicitar el informe incierto. Al volver a la selección solo se marcan automáticamente los sensores aún no enviados.
Para ejecutar también las pruebas de la interfaz, es necesaria una sesión gráfica y una instalación operativa de Tk; sin ella, esas pruebas se omiten.

### Solicita un informe experimental

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

El programa solicita las credenciales y, si corresponde, un código de verificación sin guardarlos. Permite elegir sensor, zona horaria y hasta 31 fechas inclusivas; si eliges hoy, sus datos pueden estar incompletos. Solo envía la solicitud al escribir `SI` y no la reintenta automáticamente.

> [!CAUTION]
> Si se pierde la conexión durante el envío, **comprueba el correo antes de repetir**: Tapo podría haber recibido la solicitud. Una aceptación tampoco garantiza que el correo llegue o que el archivo esté completo.

## Documentación

- [Guía de uso](docs/USAGE.md): instalación, aplicación, privacidad y solución de problemas.
- [Guía para contribuir](CONTRIBUTING.md): estructura, desarrollo y pruebas.
- [Guía del prototipo](scripts/tapo_exportacion/README.md): simulación, acceso, solicitud real y limitaciones.
- `scripts/tapo_exportacion/`: código de consola y pruebas.
- `AGENTS.md` y `docs/agent-guides/`: instrucciones internas de trabajo, en inglés.
- `pyproject.toml` y `requirements.txt`: metadatos, configuración y dependencia de zonas horarias para Windows.

## Licencia

El software del proyecto se ofrece bajo la [PolyForm Noncommercial License 1.0.0](LICENSE). Permite usarlo, modificarlo y compartirlo para los fines permitidos por la licencia, que incluyen usos no comerciales; el texto también contempla determinadas entidades y usos expresamente permitidos. Para fines comerciales no cubiertos, se necesita una autorización independiente de los titulares de los derechos correspondientes.

Es software de código disponible, pero no *open source* según la definición de la Open Source Initiative debido a la restricción comercial. La licencia del proyecto no concede derechos sobre la APK, las marcas ni otros materiales de Tapo o de terceros. El texto original en inglés de `LICENSE` prevalece sobre este resumen.
