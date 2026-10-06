# IAula Virtual

Monitor del aula virtual de la **ULEAM** (Moodle) con panel visual estilo **Windows 7 / Frutiger Aero**.
Detecta materiales nuevos, tareas próximas, descarga documentos y los sincroniza con NotebookLM.
Trae un **Asistente** que conoce tus cursos, tus tareas y el contenido de sus archivos.

Licencia **MIT**. Hecho por y para estudiantes.

---

## Para estudiantes (no necesitas saber nada de tecnología)

1. Descarga **`IAulaVirtual-Setup-1.1.0.exe`** desde la pestaña **Releases** de este repositorio.
2. Doble clic → *Siguiente, siguiente, instalar* → se abre solo.
3. Primera pantalla: escribe tu **usuario y contraseña de la ULEAM**. Se guardan **solo en tu PC**.
4. Se abrirá una ventana de Microsoft: inicia sesión **una vez**. Ya está.

**Qué puedes hacer:**
- **Resumen** — novedades y próximas entregas de un vistazo.
- **Cursos** — materiales de cada materia, descargarlos, abrir el aula.
- **Tareas** — línea de tiempo con vencimientos y cuenta regresiva.
- **Asistente** — pregúntale por tus cursos, tareas o el enunciado de un taller
  (la clave de IA viene incluida; no tienes que configurar nada).
- **NotebookLM** *(opcional, avanzado)* — sube los archivos de cada materia a **tus propios**
  cuadernos de NotebookLM. En la primera configuración elegís el navegador
  (detecta los instalados: Brave, Chrome, Edge, Firefox; Brave por defecto).

**Desinstalar:** Configuración → Aplicaciones → IAula Virtual.
El desinstalador es **profundo**: borra tus datos locales, descargas y el navegador interno.

> ¿Algo no funciona? En la vista NotebookLM está el botón **Renovar sesión**, y el botón
> **Revisar ahora** comprueba todo de nuevo.

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
`materials`, `download`, `extract`, `notebooklm_sync`,
`notebooklm_refresh` (renueva la sesión de Google; cierra Brave si hace
falta).

> Ejemplo para un agente: *"¿qué tareas tengo? descargame los archivos de
> la de Power BI y resúmeme el enunciado"* — el agente llama a `tasks` y
> `task` solo.

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
python -m iaula app                               # app de escritorio
python -m iaula gui                               # panel en el navegador
python -m iaula mcp [--sse] [--port 7801]         # servidor MCP para agentes IA
```

- **Datos en desarrollo:** `config.toml` + `config.local.toml` (credenciales, gitignored) y `data/`, `downloads/`.
- **Datos instalado:** `%LOCALAPPDATA%\IAulaVirtual`.
- **NotebookLM:** el CLI `notebooklm` con tu sesión de Google. Si caduca: botón *Renovar sesión*
  en el panel, o `notebooklm auth refresh` → `python scripts\refresh-google-session.py`.

### Compilar el instalador

Requiere **Inno Setup 6** (`winget install JRSoftware.InnoSetup`).

```powershell
# 1) (Opcional) tu clave de OpenAI para incluirla en el instalador — NO se sube a git
mkdir .build
"sk-tu-key" | Set-Content .build\author_key.txt

# 2) Icono + build + instalador
python packaging\make_icon.py
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -Version 1.1.0

# Resultado: packaging\Output\IAulaVirtual-Setup-1.1.0.exe
```

El instalador **verifica e instala las dependencias**:
- **WebView2 Runtime** — se baja e instala solo si no está (necesario para la ventana).
- **Navegador interno (Playwright Chromium, ~180 MB)** — casilla opcional en
  *Componentes opcionales*; si no se marca, se descarga en el primer inicio de sesión.

Publica el `.exe` en una **Release** de GitHub (los instaladores no van al repositorio).

> ⚠️ La clave de OpenAI incluida es **extraíble** del instalador público. Úsala con tope de gasto
> en tu cuenta de OpenAI, o distribuye el instalador **sin clave** (el Asistente pedirá una propia).

---

## Por Docker (sin instalar nada)

```powershell
git clone https://github.com/VxGM/IAula-Virtual-Uleam.git
cd IAula-Virtual-Uleam

# Opcional: inyectar tu clave de OpenAI para que no pida configurar una
copy NUL docker-openai.env
notepad docker-openai.env   # OPENAI_API_KEY=sk-...

docker compose -f packaging\docker\docker-compose.yml up -d
# Abre http://localhost:7800
```

- Primera vez → asistente (usuario/clave ULEAM + OpenAI si no la inyectaste).
- Datos persistentes en el volumen `iaula-data` (`docker compose down -v` los borra).
- Requiere Docker Desktop / Engine. Ni Python ni Playwright.
- NotebookLM: sesión de Google propia de cada uno (`notebooklm login` dentro del contenedor o en el host montado).

