# Landing de IAula Virtual

Sitio estático de una sola página con el mismo sistema visual del panel (Frutiger Aero,
vidrio, cielo y Windows 7). No tiene build de JavaScript, ni dependencias, ni secretos.

## Estructura

```
landing/
  index.html
  styles/tokens.css     # mismos tokens que la app
  styles/landing.css
  js/landing.js         # escena, reveals, copiar comandos, release de GitHub
  assets/
    favicon.svg
    sky-banner.jpg
    screens/            # capturas reales de la app
  Dockerfile            # nginx:alpine
  nginx.conf            # seguridad, gzip y cache
  docker-compose.yml
```

## Ver en local

```powershell
# Opción 1: servidor estático de Python
python -m http.server 8080 --directory landing

# Opción 2: Docker
docker compose -f landing/docker-compose.yml up --build
# http://localhost:8088
```

> Abrir `index.html` con doble clic también funciona, pero el botón de descarga
> necesita red para resolver la última release.

## Desplegar en Dokploy

1. Sube el repositorio a GitHub (la landing viaja dentro del mismo repo).
2. En Dokploy: **Create Application** → **Git** → elige el repo y la rama `main`.
3. En **Build Type** elige **Dockerfile**.
4. Configura:
   - **Docker Context Path**: `landing`
   - **Docker File**: `Dockerfile`
   - **Port**: `80`
   - No hace falta ninguna variable de entorno.
5. En **Domains** añade tu dominio (por ejemplo `iaula.tudominio.com`) y activa
   **HTTPS** con Let's Encrypt. Antes, apunta el DNS (registro A) a la IP del VPS.
6. Activa **Auto Deploy** si quieres que cada push a `main` publique la web.
7. Despliega y abre el dominio. Comprueba que responde `/healthz` con `ok`.

Si tu versión de Dokploy pide la ruta del Dockerfile relativa al repo, usa
`landing/Dockerfile` y deja el contexto en `landing`.

### Comprobar cabeceras

```bash
curl -I https://iaula.tudominio.com
```

Debe devolver `Content-Security-Policy`, `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff` y `Strict-Transport-Security`.

## Actualizar la descarga

El botón resuelve en tiempo real la última release de GitHub mediante
`https://api.github.com/repos/VxGM/IAula-Virtual-Uleam/releases/latest` y toma el
asset `IAulaVirtual-Setup-*.exe`. Si la API falla, cae a la página de releases.

Para cambiar de repositorio o la versión de respaldo, edita `CONFIG` al inicio de
`js/landing.js`.

## Imagen para compartir (Open Graph)

`index.html` referencia `assets/og.jpg` (1200×630). Cuando tengas dominio, cambia
esa ruta por la URL absoluta para que las redes sociales la muestren bien:

```html
<meta property="og:image" content="https://iaula.tudominio.com/assets/og.jpg" />
```

Puedes generar la imagen abriendo la landing en 1200×630 y capturando la portada,
o reutilizando una de las capturas de `assets/screens/`.

## Notas

- No hay cookies, analítica ni fuentes externas; la CSP no necesita excepciones.
- `assets/screens/*.png` son capturas reales de la app con una cuenta de ejemplo.
  No contienen datos de nadie.
- Si añades imágenes o secciones, mantén el contraste AA sobre el vidrio y revisa
  los cinco breakpoints (1280 / 1024 / 768 / 640 / 380).
