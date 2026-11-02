# Guía de uso

**Español** · [English](USAGE.en.md) · [← Inicio](../README.md)

Esta guía explica cómo poner en marcha la aplicación experimental en Windows y solicitar informes de sensores T310/T315. La persona usuaria ha confirmado una exportación correcta y la recepción del archivo por correo con una cuenta real. La aplicación no descarga adjuntos automáticamente.

## 1. Prepara el proyecto

Necesitas Python 3.12 o posterior, Tkinter y la base de datos de zonas horarias. Desde PowerShell, dentro de la carpeta del proyecto, puedes crear un entorno e instalar la dependencia declarada para Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

El lanzador utiliza `.venv` si existe, o el comando `python` del sistema si no existe. Si no encuentra algún requisito, muestra un mensaje. Tkinter debe estar disponible en la instalación de Python; instalar las dependencias del proyecto no lo añade. Este repositorio incluye un lanzador para Windows; no se han verificado lanzadores para macOS o Linux.

## 2. Prepara la APK para la conexión real

Coloca una copia de la APK de Tapo **3.22.105**, obtenida por tus propios medios y con autorización, en:

```text
assets/tapo/tapo-3.22.105.apk
```

Crea las carpetas si no existen. La APK no se incluye en el repositorio. El programa exige que su SHA-256 sea:

```text
a01fd475f378687d4be684741161df0f5e3daa274acb15303c44c0198b37b88f
```

Puedes comprobarla desde la raíz del proyecto con `Get-FileHash .\assets\tapo\tapo-3.22.105.apk -Algorithm SHA256`. La coincidencia identifica el archivo esperado por este prototipo, pero no acredita por sí sola su origen ni concede derechos de distribución. La simulación y las pruebas no necesitan la APK.

## 3. Abre la aplicación y solicita un informe

1. Haz doble clic en `launch_app.cmd` y mantén abierta su ventana de comandos. El selector **ES / EN** cambia el idioma de la interfaz durante la sesión.
2. Introduce el correo y la contraseña de tu cuenta Tapo. Si el servicio lo solicita, introduce el código de verificación.
3. Selecciona uno o varios sensores T310/T315. Elige las fechas en los calendarios y la zona horaria del sensor; la zona predeterminada es `Europe/Madrid`.
4. Revisa el rango y envía la solicitud. El rango incluye ambos días y admite hasta 31 fechas; los datos de hoy pueden estar incompletos. Se pide una resolución de 60 segundos. El límite de fechas es del prototipo, no un límite confirmado de Tapo.
5. Comprueba el resultado individual y el correo de la cuenta, también la carpeta de correo no deseado. Una aceptación no garantiza la llegada del correo ni que el archivo esté completo.

Las solicitudes para varios sensores se envían secuencialmente con las mismas fechas y zona. Si una queda sin confirmar, el proceso se detiene y señala las que aún no se han enviado. **Comprueba el correo antes de repetir una solicitud incierta**, ya que Tapo podría haberla recibido. Al volver a la selección se marcan automáticamente los sensores aún no enviados.

## Privacidad y solución de problemas

La aplicación no guarda credenciales ni códigos de verificación en archivos. El correo y el token de sesión permanecen en memoria durante el uso; la contraseña se utiliza para iniciar sesión y se borra del campo visible al conectar. Los datos se envían a los servicios de TP-Link mediante HTTPS. Esto no controla lo que el sistema operativo u otros programas puedan conservar.

- **El lanzador indica que faltan requisitos:** comprueba la versión de Python, que `import tkinter` funcione y que hayas instalado `requirements.txt` en el Python elegido. Si existe `.venv`, el lanzador lo usará aunque haya otro Python en el sistema.
- **La APK falta o su huella no coincide:** revisa el nombre, la ruta, la versión y el hash. No cambies la comprobación para aceptar un archivo diferente.
- **No aparecen sensores o falla el acceso:** comprueba la cuenta, la conexión y la verificación adicional. Esta integración usa una API no pública que puede cambiar; la detección no demuestra que funcione la exportación.
- **No llega un informe:** revisa el correo y su carpeta de spam. Si hubo un error de conexión, el resultado puede ser incierto; no repitas a ciegas.

Para pedir ayuda, describe los pasos, la versión de Python y el mensaje de error sin incluir contraseñas, códigos, tokens, correo, identificadores de dispositivos ni datos de sensores. Consulta la [guía de consola](../scripts/tapo_exportacion/README.md) para la simulación y los comandos de diagnóstico.
