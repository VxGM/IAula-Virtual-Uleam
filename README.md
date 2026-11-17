# IAula Virtual

Monitor del aula virtual de la **ULEAM** (Moodle) con panel visual estilo **Windows 7 / Frutiger Aero**.
Detecta materiales nuevos, tareas próximas, descarga documentos y los sincroniza con NotebookLM.
Trae un **Asistente** que conoce tus cursos, tus tareas y el contenido de sus archivos.

Licencia **MIT**. Hecho por y para estudiantes.

---

## Para estudiantes (no necesitas saber nada de tecnología)

1. Descarga **`IAulaVirtual-Setup-1.2.0.exe`** desde la página de descargas del proyecto.
2. Doble clic → *Siguiente, siguiente, instalar* → se abre solo.
3. Primera pantalla: escribe tu **usuario y contraseña de la ULEAM**. Se guardan **solo en tu PC**.
4. Se abrirá una ventana de Microsoft: inicia sesión **una vez**. Ya está.

**Qué puedes hacer:**

- **Resumen** — novedades y próximas entregas de un vistazo.
- **Cursos** — materiales de cada materia, descargarlos, abrir el aula.
- **Tareas** — línea de tiempo con vencimientos y cuenta regresiva.
- **Asistente** — pregúntale por tus cursos, tareas o el enunciado de un taller.
  Funciona con **tu propia API key** de OpenAI o de cualquier proveedor compatible
  (Groq, OpenRouter, Together, un modelo local). Si no tienes una, la app funciona
  igual sin el Asistente. También va **por voz**: el micrófono pasa tu voz a texto
  y, si preguntaste hablando, la respuesta se escucha.
- **NotebookLM** *(opcional, avanzado)* — sube los archivos de cada materia a **tus propios**
  cuadernos. En la primera configuración eliges el navegador (detecta Brave, Chrome, Edge
  y Firefox; Brave por defecto).
- **Ajustes** — cambia tu cuenta, tu proveedor de IA y el navegador cuando quieras.
- **Diagnóstico** — comprueba que todo lo necesario esté instalado y repara lo que falte.

**Desinstalar:** Configuración → Aplicaciones → IAula Virtual.
El desinstalador es **profundo**: borra tus datos locales, descargas y el navegador interno.

> ¿Algo no funciona? Abre **Diagnóstico** desde el menú de inicio. El botón
> **Revisar ahora** también vuelve a comprobar el aula.

---

## Seguridad y privacidad

- **Sin API keys incluidas**: cada persona pone la suya y se guarda cifrada con
  DPAPI en su equipo. El proyecto ya no distribuye ninguna clave.
- **Datos solo locales**: no hay servidores de IAula, ni telemetría, ni cuentas centrales.
- **Solo escucha en `127.0.0.1`**, con CSP, validación de `Host`/`Origin` y sin exponer secretos.
- **Código abierto**: puedes revisar cada línea antes de ejecutar el instalador.
- **Hashes públicos**: cada release incluye `SHA256SUMS.txt`.

El detalle completo está en [`SECURITY.md`](SECURITY.md). Si Windows muestra un aviso
de SmartScreen es porque el instalador aún no está firmado; la firma está preparada
en el build (ver [`packaging/SIGNING.md`](packaging/SIGNING.md)).

> **Actualizar desde 1.1.x:** la clave que traía el instalador antiguo se mueve a la
> bóveda cifrada y el archivo `bundled_key.txt` se borra al instalar o al abrir la app.
> No tienes que volver a configurar el Asistente.

---

## Primer inicio y diagnóstico

Al abrir la app se ejecuta un **preflight** de dependencias: WebView2, navegador,
paquetes de Python, sesión del aula, red, espacio en disco y API key. Si algo
impide funcionar, muestra un panel "Prepara IAula" con el problema y un botón
**Reparar**. Los avisos menores aparecen como una franja descartable.

Desde la terminal también puedes ejecutar el mismo escaneo:

```bash
python -m iaula doctor [--json] [--no-network] [--repair]
```

---

## Conectar con cualquier agente IA (MCP)

IAula trae un servidor **MCP** (Model Context Protocol): cualquier agente
(Claude Desktop, Claude Code, Cursor, …) puede ver tus cursos, tareas y
**descargar los PDFs y archivos de cada tarea con su contenido extraído**
para tener contexto sólido. Corre desde el repo (no desde el instalador):

```bash
pip install -e ".[mcp]"     # una vez (SDK de MCP)
python -m iaula mcp         # servidor por stdio (local)
python -m iaula mcp --sse   # por HTTP en 127.0.0.1:7801
```

**Claude Code** (desde el repo):

```bash
claude mcp add iaula -- .venv\Scripts\python -m iaula mcp
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "iaula": {
      "command": "C:\\Users\\ASUS\\IAula Virtual\\.venv\\Scripts\\python.exe",
      "args": ["-m", "iaula", "mcp"],
      "cwd": "C:\\Users\\ASUS\\IAula Virtual"
    }
  }
}
```

**Cursor:** Settings → MCP → Add server (Command): `.venv\Scripts\python`,
Arguments: `-m iaula mcp`.

**Herramientas:** `status`, `courses`, `check` (novedades), `tasks` (entregas
próximas), `task` (descripción + adjuntos descargados + texto extraído),
`upload_task` (sube uno o varios archivos a una tarea y la entrega; con
`submit=false` solo los adjunta), `materials`, `download`, `extract`,
`notebooklm_sync`, `notebooklm_refresh` (renueva la sesión de Google; cierra
Brave si hace falta).

---

## Para desarrolladores

Requiere **Python 3.11+** en Windows.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,mcp]"
playwright install chromium
python -m iaula login      # sesión del aula (una vez)
python -m iaula app        # app de escritorio (ventana propia)
python -m iaula gui        # o el panel en el navegador
python -m iaula mcp        # o el servidor MCP para agentes IA
```

### Comandos

```bash
python -m iaula login                             # sesión del portal (Microsoft)
python -m iaula check [--json] [--notify]         # novedades + tareas
python -m iaula tasks --days 30 [--json]          # próximas entregas
python -m iaula task 584517 [--download] [--json] # descripción + archivos de una tarea
python -m iaula extract "ruta.pdf"                # texto de un PDF/archivo (contexto)
python -m iaula materials --course inteligencia
python -m iaula download --course X | --all
python -m iaula nlm sync --course X | --all [--no-wait]
python -m iaula nlm status
python -m iaula doctor [--json] [--repair]        # diagnóstico de dependencias
python -m iaula app                               # app de escritorio
python -m iaula gui                               # panel en el navegador
python -m iaula mcp [--sse] [--port 7801]         # servidor MCP para agentes IA
```

- **Datos en desarrollo:** `config.toml` + `config.local.toml` (credenciales, gitignored)
  y `data/`, `downloads/`.
- **Datos instalado:** `%LOCALAPPDATA%\IAulaVirtual`.
- **Secretos:** en desarrollo puedes usar `config.local.toml`; al arrancar el panel se
  migran a `data/secrets.bin` (DPAPI) y se eliminan del TOML. También valen las variables
  `IAULA_USERNAME`, `IAULA_PASSWORD`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.
- **NotebookLM:** el CLI `notebooklm` con tu sesión de Google. Si caduca: botón *Renovar
  sesión* en el panel (lee las cookies de tu navegador preferido; lo cierra un momento), o
  el CLI `notebooklm auth refresh` → `python scripts\refresh-google-session.py`.

### Asistente y proveedores compatibles

El Asistente usa la API de OpenAI o cualquier endpoint compatible. Se configura en
**Ajustes → Asistente IA** (URL, modelo y key), y la app prueba la conexión antes de
guardar. Precedencia de la clave: `config.toml` → `config.local.toml` → bóveda DPAPI →
variable de entorno `OPENAI_API_KEY` (Docker).

Modelos de voz (`stt_model`, `tts_model`, `tts_voice`) se ajustan en `config.toml`,
sección `[chat]`. Solo están disponibles si el proveedor expone los endpoints de audio.

### Navegador (login y Playwright)

IAula usa tu navegador instalado (**Brave > Chrome > Edge**) para el login del
aula. La elección se guarda en `config.local.toml` (`[browser] default`) y se
cambia en **Ajustes → Navegador preferido** (o en el primer arranque).
Si no encuentra ninguno, descarga el Chromium interno como respaldo.

> En la app empaquetada, `PLAYWRIGHT_BROWSERS_PATH` apunta a
> `%LOCALAPPDATA%\ms-playwright`; Playwright en modo *frozen* buscaba los
> navegadores dentro de `_internal` y fallaba con *Executable doesn't exist*.

### Compilar el instalador

Requiere **Inno Setup 6** (`winget install JRSoftware.InnoSetup`).

```powershell
python packaging\make_icon.py
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -Version 1.2.0

# Resultado:
#   packaging\Output\IAulaVirtual-Setup-1.2.0.exe
#   packaging\Output\SHA256SUMS.txt
```

El instalador **verifica e instala las dependencias**:

- **WebView2 Runtime** — se baja e instala solo si no está (necesario para la ventana).
- **Navegador interno (Playwright Chromium, ~180 MB)** — casilla opcional en
  *Componentes opcionales*; si no se marca, se descarga en el primer inicio de sesión.
- **Recordatorio diario (07:30)** — casilla opcional que crea la tarea `IAula-Check`.

No se incluye ninguna API key en el instalador. Publica el `.exe` y `SHA256SUMS.txt`
en una **Release** de GitHub (los instaladores no van al repositorio).

Para firmar el binario cuando tengas certificado: `build.ps1 -Sign ruta\al.pfx`
(ver [`packaging/SIGNING.md`](packaging/SIGNING.md)).

---

## Por Docker (sin instalar nada)

```bash
git clone https://github.com/VxGM/IAula-Virtual-Uleam.git
cd IAula-Virtual-Uleam

# Opcional: inyectar tu API key para no configurarla en el panel
printf 'OPENAI_API_KEY=sk-...\n' > .env

docker compose -f packaging/docker/docker-compose.yml up -d
# Abre http://localhost:7800
```

- Primera vez → asistente (usuario/clave ULEAM y, si no la inyectaste, la API key).
- Datos persistentes en el volumen `iaula-data` (`docker compose down -v` los borra).
- Requiere Docker Desktop / Engine. Ni Python ni Playwright en el host.
- NotebookLM: sesión de Google propia de cada uno.

---

## Página web

La landing (qué hace, cómo se instala, seguridad y FAQ) vive en [`landing/`](landing/)
y está lista para desplegarse en Dokploy con un contenedor nginx. Instrucciones en
[`landing/README.md`](landing/README.md).
