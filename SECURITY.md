# Seguridad y privacidad de IAula Virtual

## Alcance

IAula Virtual es una aplicación local para Windows que automatiza la consulta del
aula virtual de la ULEAM (Moodle) usando **tus propias credenciales**. No hay
servidores de IAula, ni cuentas centrales, ni telemetría.

## Qué se guarda y dónde

Instalado con el instalador, todo vive en `%LOCALAPPDATA%\IAulaVirtual`:

| Dato | Archivo | Protección |
|---|---|---|
| Usuario del aula | `config.local.toml` | texto plano (no es un secreto) |
| Contraseña del aula | `data/secrets.bin` | cifrado DPAPI por usuario |
| API key del Asistente | `data/secrets.bin` | cifrado DPAPI por usuario |
| Sesión del aula | `data/session.json` | cookies de sesión, permisos del usuario |
| Cursos, tareas, reportes | `data/` | datos de tu cuenta |
| Materiales descargados | `downloads/` | archivos del aula |
| Registro de errores | `data/logs/error.log` | sin credenciales |

DPAPI (`CryptProtectData`) liga el cifrado a tu usuario de Windows y a este equipo:
copiar la carpeta a otra PC no permite descifrar la clave. En Linux/Docker el
archivo se guarda con permisos `0600` y el diagnóstico lo marca como advertencia.

Desinstalar la app borra `%LOCALAPPDATA%\IAulaVirtual`, las descargas y el
navegador interno.

## Conexiones de red

IAula solo se conecta a:

- `https://aulavirtualmoodle.uleam.edu.ec` (y el dominio de Microsoft 365 para el login).
- El proveedor de IA que configures (por defecto `https://api.openai.com/v1`).
- NotebookLM/Google si usas esa función, mediante su CLI con tu sesión.
- `api.github.com` desde la **página web**, nunca desde la app.

No hay analítica, ni crash reporting remoto, ni actualizaciones automáticas
silenciosas.

## Superficie local

- El panel escucha **solo en `127.0.0.1`** en un puerto libre entre 7800 y 7811.
- Rechaza peticiones con `Host` ajeno (DNS rebinding) y con `Origin` externo.
- Aplica CSP, `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy: no-referrer`.
- Los secretos nunca se sirven por HTTP ni se escriben en logs.
- Los límites de cuerpo son 2 MB para JSON y 25 MB para audio.

## Lo que la app no hace

- No incluye ni distribuye ninguna API key.
- No instala servicios, drivers ni extensiones.
- No se ejecuta al iniciar Windows. Opcionalmente crea una tarea programada
  **visible y desinstalable** (`IAula-Check`) para revisar novedades a las 07:30.
- No descarga binarios sin informarlo: el navegador interno (~180 MB) se ofrece
  en el instalador y en el diagnóstico.

## Verificar el instalador

Cada build publica `SHA256SUMS.txt` junto al instalador. En PowerShell:

```powershell
Get-FileHash .\IAulaVirtual-Setup-1.2.0.exe -Algorithm SHA256
```

Compara el hash con el del archivo `SHA256SUMS.txt` de la misma release. Si no
coincide, no lo ejecutes.

## Aviso de Windows SmartScreen

El proyecto **todavía no tiene un certificado de firma de código**, así que
Windows puede mostrar "Windows protegió tu PC". Es esperable en ejecutables
nuevos y sin reputación. Puedes comprobar el hash y revisar el código fuente
antes de continuar. Cuando se adquiera un certificado, el build lo firmará
automáticamente (ver `packaging/SIGNING.md`).

## Reportar un problema de seguridad

Abre un aviso privado en el repositorio (`Security` → `Report a vulnerability`)
o escribe al autor. Incluye versión, pasos para reproducir y el impacto. No
publiques credenciales ni claves en un issue público.

## Versiones con soporte

Solo la última release recibe correcciones de seguridad.
