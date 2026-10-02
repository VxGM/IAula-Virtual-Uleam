# IAula Virtual

Monitor del aula virtual: novedades de materiales y tareas próximas; descarga de documentos y subida a NotebookLM bajo demanda.

Funcional: login (Microsoft/OIDC), cursos, materiales, tareas, novedades, descargas, NotebookLM y chequeo diario con aviso.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Comandos

```bash
python -m iaula login                             # sesión del portal (Microsoft)
python -m iaula check [--json]                    # novedades + tareas (--notify: toast)
python -m iaula tasks --days 30 [--json]
python -m iaula materials --course inteligencia
python -m iaula download --course inteligencia    # → downloads/<curso>/
python -m iaula nlm sync --course inteligencia    # sube los archivos al notebook del curso
python -m iaula nlm status
```

## Panel visual

```bash
python -m iaula gui            # abre el panel en el navegador (http://127.0.0.1:7800)
```

O doble clic en `Panel.bat` (misma cosa, sin escribir comandos). Deja la ventana abierta
mientras usas el panel; ciérrala (o Ctrl+C) para apagarlo.

Vistas: Resumen · Cursos · Tareas · NotebookLM · Asistente. Botones para revisar, descargar y
sincronizar con ventana de progreso en vivo, y un chat de estudio (OpenAI: key en
`[chat] api_key` de `config.local.toml`, modelo en `config.toml`).
Tema Frutiger Aero (cielo, vidrio, burbujas).

## NotebookLM

Usa el CLI `notebooklm` con la sesión de Google guardada en `~/.notebooklm`. Si la sesión caduca:

```bash
notebooklm auth refresh                  # 1) reintento ligero (rotación de tokens)
# si sigue vencida:
# 2) cerrar Brave por completo
python scripts\refresh-google-session.py
# 3) verificar
python -m iaula nlm status
```

## Aviso diario

```powershell
scripts\install-daily-task.ps1 -Time 07:30   # registra la tarea IAula-Check (check + toast)
```

## Configuración

- `config.toml` — valores no secretos.
- `config.local.toml` — credenciales del portal (copiar de `config.local.toml.example`). Gitignored.
