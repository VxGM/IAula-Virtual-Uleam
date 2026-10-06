# IAula Virtual — guía para el agente

Portal: Moodle ULEAM (login Microsoft/OIDC). Ejecutar siempre desde la raíz del repo con
`.venv\Scripts\python -m iaula <cmd>`. Salida `--json` disponible en courses/tasks/check/materials.

| El usuario dice | Comando |
|---|---|
| "revisa mis cursos / hay novedades?" | `check --json` |
| "qué tareas tengo / cuándo entrego" | `tasks --days 30 --json` |
| "archivos o contexto de la tarea X" | `task <id> --json` (descripción + adjuntos); `--download` los baja a `downloads/<curso>/Tareas/<tarea>/`; para leer un PDF usa `extract "<ruta>"` |
| "qué materiales tiene X" | `materials --course X` |
| "bájame los PDFs de X" | `download --course X` (→ `downloads/<curso>/`) |
| "mándalo a NotebookLM" | `download --course X` y luego `nlm sync --course X` |
| "un cuaderno por materia con todos los archivos" | `download --all` y luego `nlm sync --all --no-wait` |
| "estado de NotebookLM" | `nlm status` |
| "abre el panel / la interfaz gráfica" | `gui` (http://127.0.0.1:7800) |
| "abre la app de escritorio" | `app` (ventana propia) |

Reglas:
- Si falla por sesión vencida y el re-login automático no basta: `login` (abre navegador visible).
- `nlm` usa la sesión de Google guardada; verificar con `nlm status`. Si caducó: probar `notebooklm auth refresh`; si sigue, cerrar Brave por completo y correr `.venv\Scripts\python scripts\refresh-google-session.py` (extrae la sesión del Brave), luego `nlm status`. En el panel hay un botón "Renovar sesión" (vista NotebookLM) que cierra Brave y corre el script solo.
- Asistente del panel: usa la API de OpenAI (key en `[chat] api_key` de `config.local.toml`; modelo en `[chat] model` de `config.toml`). El servidor inyecta cursos/tareas/materiales reales y, por cada tarea pendiente, su descripción y el contenido de sus adjuntos (cache ~15 min).
- Primer `check` = línea base (no reporta novedades). Las siguientes sí.
- Pedir confirmación antes de descargar/subir cursos completos sin que el usuario lo pida.
- Nunca imprimir ni commitear credenciales (`config.local.toml`, `data/`).
- Chequeo diario: `scripts\install-daily-task.ps1 -Time 07:30` (tarea `IAula-Check`).

## MCP (conectar cualquier agente IA)

Servidor MCP incluido: `.venv\Scripts\python -m iaula mcp` (stdio)
o `--sse` (HTTP en 127.0.0.1:7801). Requiere `pip install -e ".[mcp]"`.

Herramientas: `status`, `courses`, `check`, `tasks`, `task`
(descripción + adjuntos descargados + texto extraído de PDFs/CSVs),
`materials`, `download`, `extract`, `notebooklm_sync`,
`notebooklm_refresh` (renueva la sesión de Google; cierra Brave si hace
falta).

Para Claude Code: `claude mcp add iaula -- .venv\Scripts\python -m iaula mcp`.
Para Claude Desktop: `mcpServers.iaula` en `claude_desktop_config.json`
con command = el python del venv y args = `["-m", "iaula", "mcp"]`.
