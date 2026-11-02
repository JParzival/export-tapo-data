<div align="center">

# Export Tapo Data

**Tus sensores, tus datos. Una forma más sencilla de exportarlos.**

Una aplicación de escritorio experimental para exportar datos de sensores TP-Link Tapo,
construida sobre un prototipo en Python.

**Español** · [English](README.en.md)

[Estado](#estado-del-proyecto) · [Primeros pasos](#primeros-pasos) · [Documentación](#documentación)

</div>

> [!IMPORTANT]
> **Proyecto experimental.** Se han probado el acceso a la nube y la detección de sensores con una cuenta real, pero **la solicitud de exportación y el contenido del archivo aún no se han validado en el servicio real**. Las pruebas locales no sustituyen esa validación.

## De los sensores a tus datos

La aplicación guía la conexión, la selección de uno o varios sensores **T310 o T315** y la solicitud de informes de temperatura y humedad por correo. También se conserva el prototipo de consola. Todavía no descarga los archivos adjuntos automáticamente.

La integración utiliza una API interna de Tapo y una versión concreta de su APK; ambas pueden cambiar.

## Estado del proyecto

| Paso | Estado |
| --- | --- |
| Acceso a la nube y detección de sensores | Probados con una cuenta real |
| Simulación y pruebas locales | Disponibles |
| Solicitud de exportación y archivo recibido | Pendientes de validación real |
| Aplicación de escritorio | Disponible, flujo real de exportación pendiente de validación |
| Descarga automática de adjuntos | Aún no implementada |

El siguiente hito técnico es validar una exportación real y comparar el archivo recibido con una descarga manual. Las credenciales y los datos personales deben mantenerse fuera del repositorio.

## Primeros pasos

Necesitas **Python 3.12 o posterior**. Para conectar con los servicios IoT de Tapo, coloca la APK verificada de Tapo 3.22.105 en `assets/tapo/tapo-3.22.105.apk`; el prototipo comprueba su huella SHA-256 antes de usarla. La APK queda excluida de Git y no se incluye al clonar el repositorio. La simulación y las pruebas no necesitan APK ni cuenta.

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

En Windows, haz doble clic en **`Abrir Tapo Data.cmd`**, en la carpeta del proyecto. Usa el entorno `.venv` si existe y, si no, el Python disponible en el sistema. Necesita Python 3.12 o posterior, Tkinter y la base de zonas horarias; si falta algún requisito, muestra un aviso. La ventana de comandos permanece abierta mientras se usa la aplicación.

La interfaz permite elegir español o inglés con el selector **ES / EN** y no guarda la contraseña ni los códigos de verificación. El idioma se mantiene durante la sesión.
El icono de Tapo se obtiene de la APK local verificada; la aplicación es independiente y no está afiliada a Tapo ni a TP-Link.
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

- [Guía del prototipo](scripts/tapo_exportacion/README.md): simulación, acceso, solicitud real y limitaciones.
- `scripts/tapo_exportacion/`: código de consola y pruebas.
- `AGENTS.md` y `docs/agent-guides/`: instrucciones de trabajo para el repositorio.
- `pyproject.toml` y `requirements.txt`: metadatos, configuración y dependencia de zonas horarias para Windows.
