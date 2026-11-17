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

## Publicar en GitHub Pages (recomendado)

El workflow [`.github/workflows/pages.yml`](../.github/workflows/pages.yml) publica
solo `landing/` (sin Docker, sin build) cada vez que cambia algo en esa carpeta.

1. En GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push a `main`. El workflow *Deploy landing to GitHub Pages* hace el resto.
3. La web queda en <https://vxgm.github.io/IAula-Virtual-Uleam/>.

No hay variables ni secretos que configurar. `landing/index.html` ya lleva el
canonical y las etiquetas Open Graph apuntando a esa URL. Si luego usas un dominio
propio, actualiza esas URLs y añade el dominio en **Settings → Pages → Custom domain**.

## Alternativa: Dokploy

Si prefieres servirla desde tu VPS con nginx y un dominio propio:

1. Sube el repositorio a GitHub (la landing viaja dentro del mismo repo).
2. En Dokploy: **Create Application** → **Git** → elige el repo y la rama `main`.
3. En **Build Type** elige **Dockerfile**.
4. Configura:
   - **Docker Context Path**: `landing`
   - **Docker File**: `Dockerfile`
   - **Port**: `80`
   - No hace falta ninguna variable de entorno.
5. En **Domains** añade tu dominio y activa **HTTPS** con Let's Encrypt. Antes,
   apunta el DNS (registro A) a la IP del VPS.
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

`index.html` referencia `assets/og.jpg` (1200×630) con la URL absoluta de GitHub
Pages. Si cambias a un dominio propio, actualiza `og:image`, `og:url` y el
`canonical`:

```html
<link rel="canonical" href="https://iaula.tudominio.com/" />
<meta property="og:url" content="https://iaula.tudominio.com/" />
<meta property="og:image" content="https://iaula.tudominio.com/assets/og.jpg" />
```

## Notas

- No hay cookies, analítica ni fuentes externas; la CSP no necesita excepciones.
- `assets/screens/*.png` son capturas reales de la app con una cuenta de ejemplo.
  No contienen datos de nadie.
- Si añades imágenes o secciones, mantén el contraste AA sobre el vidrio y revisa
  los cinco breakpoints (1280 / 1024 / 768 / 640 / 380).
