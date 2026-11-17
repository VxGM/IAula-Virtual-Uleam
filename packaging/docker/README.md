# IAula Virtual — Docker

Ejecuta IAula Virtual en un contenedor sin instalar nada en el equipo.

## Uso rápido

```bash
# 1) Clona el repo (si no lo tienes)
git clone https://github.com/VxGM/IAula-Virtual-Uleam.git
cd IAula-Virtual-Uleam

# 2) (Opcional) Variables de entorno
printf 'OPENAI_API_KEY=sk-...\n' > .env

# 3) Levanta
docker compose -f packaging/docker/docker-compose.yml up -d

# 4) Abre http://localhost:7800
#    Si no definiste las variables, el panel pide usuario/clave de la ULEAM
#    y tu API key en Ajustes.

# 5) Para parar y borrar los datos del contenedor
docker compose -f packaging/docker/docker-compose.yml down -v
```

> **Nota:** Docker no incluye ventana de escritorio propia. La interfaz se abre
> en tu navegador (`http://localhost:7800`).

No hay ninguna API key incluida en la imagen: cada persona pone la suya.

## Variables de entorno (`docker-compose.yml`)

| Variable | Qué es | Por defecto |
|---|---|---|
| `OPENAI_API_KEY` | Tu clave del proveedor de IA | vacía (el panel pide una) |
| `OPENAI_BASE_URL` | URL compatible con OpenAI | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Modelo del Asistente | `gpt-5.4-mini` |
| `PORTAL_BASE_URL` | URL del aula virtual | `https://aulavirtualmoodle.uleam.edu.ec` |
| `PORTAL_USERNAME` | Usuario ULEAM (opcional) | vacío (pide el asistente) |
| `PORTAL_PASSWORD` | Clave del aula (opcional) | vacía (pide el asistente) |
| `WEB_PORT` | Puerto del panel | `7800` |

Si defines `OPENAI_API_KEY` en el entorno, la app la muestra como gestionada por
el servidor y no permite cambiarla desde el panel.

## Datos persistentes

- El volumen `iaula-data` guarda `config.local.toml`, `data/`, `downloads/`.
- Así no pierdes cursos/descargas al reiniciar el contenedor.
- En Linux el vault de secretos usa permisos `0600` en lugar de DPAPI; el
  diagnóstico lo marca como advertencia.

## NotebookLM

Dentro del contenedor se usa el CLI `notebooklm` con la sesión de Google del
contenedor. Si es tu primer vez, entra al panel → NotebookLM → Renovar sesión.

## Requisitos del host

- Docker Desktop o Docker Engine instalado.
- Windows 10/11 / macOS / Linux.
- No se necesita Python ni Playwright instalados.
