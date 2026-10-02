# IAula Virtual — guía para el agente

Portal: Moodle ULEAM (login Microsoft/OIDC). Ejecutar siempre desde la raíz del repo con
`.venv\Scripts\python -m iaula <cmd>`. Salida `--json` disponible en courses/tasks/check/materials.

| El usuario dice | Comando |
|---|---|
| "revisa mis cursos / hay novedades?" | `check --json` |
| "qué tareas tengo / cuándo entrego" | `tasks --days 30 --json` |
| "qué materiales tiene X" | `materials --course X` |
| "bájame los PDFs de X" | `download --course X` (→ `downloads/<curso>/`) |
| "mándalo a NotebookLM" | `download --course X` y luego `nlm sync --course X` |
| "estado de NotebookLM" | `nlm status` |
| "abre el panel / la interfaz gráfica" | `gui` (http://127.0.0.1:7800) |

Reglas:
- Si falla por sesión vencida y el re-login automático no basta: `login` (abre navegador visible).
- `nlm` usa la sesión de Google guardada; verificar con `nlm status`. Si caducó: probar `notebooklm auth refresh`; si sigue, cerrar Brave por completo y correr `.venv\Scripts\python scripts\refresh-google-session.py` (extrae la sesión del Brave), luego `nlm status`.
- Asistente del panel: usa la API de OpenAI (key en `[chat] api_key` de `config.local.toml`; modelo en `[chat] model` de `config.toml`). El servidor inyecta cursos/tareas/materiales reales como contexto.
- Primer `check` = línea base (no reporta novedades). Las siguientes sí.
- Pedir confirmación antes de descargar/subir cursos completos sin que el usuario lo pida.
- Nunca imprimir ni commitear credenciales (`config.local.toml`, `data/`).
- Chequeo diario: `scripts\install-daily-task.ps1 -Time 07:30` (tarea `IAula-Check`).
