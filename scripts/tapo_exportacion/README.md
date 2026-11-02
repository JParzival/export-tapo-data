# Prototipo de exportación Tapo

**Español** · [English](README.en.md) · [← Volver al proyecto](../../README.md)

Una guía para probar la simulación, comprobar el acceso y solicitar un informe experimental desde la consola.

> [!IMPORTANT]
> La conexión, la detección de sensores y una exportación desde la aplicación se han probado con una cuenta real. La persona usuaria confirma que el archivo se exportó correctamente y llegó por correo. La API interna de Tapo puede cambiar.

## 1. Simulación local

La prueba crea un servidor temporal en `127.0.0.1`, prepara un día completo a resolución de un minuto, envía una petición simulada y comprueba la respuesta. No requiere cuenta ni acceso a Internet, no envía correos ni lee o modifica históricos.

Desde la raíz de este repositorio, usa el entorno del proyecto:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\mock_tapo.py
.\.venv\Scripts\python.exe -m unittest discover -s scripts\tapo_exportacion -v
```

El recorrido, los campos del modelo y la ruta proceden del análisis estático de Tapo 3.22.105 mediante REA. El servidor de este prototipo es una simulación: aceptar una petición aquí no demuestra que Tapo la acepte. La dirección `.invalid` y el identificador del sensor son ficticios.

La persona usuaria ha comprobado una exportación real desde la aplicación y la recepción correcta del archivo. Esta prueba no establece el comportamiento para todas las solicitudes posibles.

## 2. Solicitud experimental de exportación

Desde la raíz del repositorio, ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\export_tapo.py
```

El programa inicia sesión, solicita la verificación adicional cuando corresponde y presenta los sensores T310/T315. Se elige un sensor y un rango de fechas inclusivas de hasta 31 días. Se admite la fecha actual, cuyos datos pueden estar incompletos; el rango solicitado abarca los días naturales seleccionados. La zona predeterminada es `Europe/Madrid` y se puede cambiar por la zona del sensor. Se solicita una resolución de 60 segundos. El límite de 31 días es una restricción de este prototipo, no una conclusión sobre el límite del servidor.

La solicitud se dirige al correo de la propia cuenta solo al escribir `SI`. El cliente envía como máximo una solicitud y no la repite automáticamente; si la conexión falla, no puede saberse si Tapo la recibió. Un código de aceptación no confirma que haya llegado correo ni que el archivo esté completo. Comprueba el correo antes de repetir. No se descargan ni guardan automáticamente los adjuntos: ese paso queda pendiente.

## 3. Comprobación de acceso desde el ordenador

Ejecuta en una terminal propia, desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe scripts\tapo_exportacion\cloud_probe.py
```

Solicita el correo y la contraseña por consola; no muestra la contraseña ni guarda credenciales ni tokens. Conecta por HTTPS a TP-Link, sin seguir redirecciones ni reintentar. Además de la lista básica de dispositivos, intenta descubrir la región, autenticarse en el servicio V2 y contar sensores T310/T315 con la consulta IoT de la aplicación. Comprueba que los servidores regionales pertenecen a dominios de TP-Link y usa los certificados TLS extraídos de la APK verificada. La configuración de firma se obtiene de la misma APK y permanece en memoria. Solo muestra recuentos, nombres de servicios o códigos de error, sin direcciones de servicio, identificadores ni tokens. No solicita exportaciones. El servicio puede exigir una verificación adicional o rechazar este protocolo no público. Esta prueba no demuestra que la API de exportación esté disponible.

Si la cuenta requiere verificación adicional y admite correo, el programa solicita un código a Tapo y lo pide una vez en la terminal; el código tampoco se muestra ni se guarda. Si se ofrece TOTP como alternativa, solicita el código de la aplicación de autenticación. No registra el ordenador como dispositivo de confianza ni reintenta códigos incorrectos.

El programa reconoce el identificador con los nombres `MFAProcessId` y `mfaProcessId`, y envía los parámetros `MFAProcessId` y `MFAType` como en el cliente Tapo CLI. Si no encuentra un identificador, detiene la verificación antes de solicitar un código y muestra únicamente la presencia y el tipo de campos predefinidos, sin sus valores. El acceso con verificación y el listado de sensores se han comprobado.

La consulta IoT usa los identificadores de servicio `nbu.*` presentes en la APK. Si la respuesta de acceso proporciona otro servidor regional de aplicación, se valida su dominio antes de usarlo. La APK verificada se lee desde `assets/tapo/tapo-3.22.105.apk` en la raíz del proyecto y el programa comprueba su huella antes de usarla. La APK está excluida de Git y debe obtenerse por separado en otras copias. No modifica los históricos existentes.
