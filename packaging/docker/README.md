# IAula Virtual — Docker

Ejecuta IAula Virtual en un contenedor sin instalar nada en el equipo.

## Uso rápido

```powershell
# 1) Clona el repo (si no lo tienes)
git clone https://github.com/VxGM/IAula-Virtual-Uleam.git
cd IAula-Virtual-Uleam

# 2) Sube tu clave de OpenAI (opcional si usas la incluida)
copy NUL docker-openai.env
notepad docker-openai.env   # pega: OPENAI_API_KEY=sk-...

# 3) Levanta
docker compose up -d

# 4) Abre http://localhost:7800  (o el puerto que configures)
#    Verás el asistente: usuario/clave de la ULEAM y la clave de OpenAI.

# 5) Para parar y limpiar datos del contenedor
docker compose down -v
```

> **Nota:** Docker no incluye ventana de escritorio propia — la interfaz se
> abre en tu navegador (`http://localhost:7800`).

## Variables de entorno (docker-compose.yml)

| Variable | Qué es | Por defecto |
|---|---|---|
| `OPENAI_API_KEY` | Clave de OpenAI | vacía (el asistente pide una) |
| `OPENAI_MODEL` | Modelo | `gpt-5.4-mini` |
| `PORTAL_BASE_URL` | URL del aula virtual | `https://aulavirtualmoodle.uleam.edu.ec` |
| `PORTAL_USERNAME` | Usuario ULEAM (opcional) | vacío (pide el asistente) |
| `PORTAL_PASSWORD` | Clave del aula (opcional) | vacía (pide el asistente) |
| `WEB_PORT` | Puerto del panel | `7800` |
| `DATA_DIR` | Donde se guardan datos/descargas dentro del contenedor | `/app/data` |

## Datos persistentes

- El volumen `iaula-data` guarda `config.local.toml`, `data/`, `downloads/`, `reports/`.
- Así no pierdes cursos/descargas al reiniciar el contenedor.
- **No sube la clave de OpenAI al repo** — va en `docker-openai.env` (gitignored).

## NotebookLM

Dentro del contenedor se usa el CLI `notebooklm` con la sesión que tengas en
`~/.notebooklm` del host (montado en `/root/.notebooklm`). Si es tu primer vez:
entra al panel → NotebookLM → Renovar sesión.

## Requisitos del host

- Docker Desktop o Docker Engine instalado.
- Windows 10/11 / macOS / Linux.
- No se necesita Python ni Playwright instalados.

## Nota sobre credenciales

El asistente guarda credenciales en `config.local.toml` dentro del volumen.
`docker compose down -v` las borra.
