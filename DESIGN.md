# Design

Sistema visual del panel IAula. Fuente: proyectos propios `frutiger`, `frutiger blog`
y `frutiger-aero` (paleta, motivos y componentes), más el banner propio
`frutiger-aero-banner-2688x1152.png` como fondo de cielo/colinas.

## Theme

Frutiger Aero (2004–2013): cielo luminoso, vidrio glossy, naturaleza idealizada,
optimismo tecnológico. Tema claro con sol; sin modo oscuro.

Escena: estudiante en su escritorio, de día, quiere una vista amable y brillante de su
semana universitaria; el panel se siente como una ventana de Windows Vista salida del
escritorio.

## Color

Tokens en OKLCH donde aporta; hex base heredados de los proyectos del usuario.

- `--sky-1 #8fd8ff` → `--sky-2 #4cc2ff` → `--sky-3 #0b6fbd`: gradiente de respaldo (fallback del banner).
- `--accent #0078d7` (azul Aero, theme-color) · `--accent-deep #01579b`
- `--grass #7ab800` · `--lime #a5d610` · `--aqua #00c8c8`
- `--ink #063a5e` · `--ink-soft rgba(6,58,94,.72)` (texto sobre vidrio)
- Semánticos: éxito `#2e9e4f`, alerta `#d68910`, error `#c0392b`, vencida `#c0392b`.
- Glass: `rgba(255,255,255,.40)` base, `--glass-brd rgba(255,255,255,.65)`, highlight `rgba(255,255,255,.75)`.

## Typography

- Body/UI: `"Segoe UI", Frutiger, "Nunito Sans", system-ui` — una sola voz (la fuente real de la era).
- Display ocasional (título del header): `"Nunito"` vía Google Fonts con fallback a Segoe UI; offline se degrada sin romper.
- Escala fija: 12 / 13 / 14 / 16 / 20 / 24 / 32 / clamp(2rem,5vw,3.4rem) para el título.
- Pesos: 400 / 600 / 700 / 800. Sin mayúsculas largas; micro-labels uppercase ≤4 palabras cuando aplica.

## Layout

- Header pill flotante (sticky) + contenedor `max-width 1180px`.
- Vistas por pestañas (hash router): Resumen · Cursos · Tareas · NotebookLM.
- Rejilla principal: 2 columnas en desktop (novedades | entregas), 1 en móvil.
- 5 breakpoints (1280 / 1024 / 768 / 640 / 380) siguiendo los proyectos previos.

## Components

- **Glass panel** (`.panel`): vidrio + brillo interior + cabecera-titlebar con degradado glossy y borde inferior.
- **Glossy button** (`.glossy-btn`, + `--ghost`, `--green`, `--danger`, `--sm`): píldora con brillo superior, hundimiento al click, estados loading/disabled.
- **Pill / chip**: categorías y contadores (contador con fondo blanco y acento).
- **Status dot**: sesión portal / NotebookLM (ok, vencida, error) con halo pulsante.
- **Timeline** de tareas: línea degradada + nodos glossy; agrupada en vencidas / hoy / semana / después.
- **Aero window** (`.aero-window`): ventana Vista para el registro de trabajos en vivo (arrastrable, botón cerrar real, sin botones falsos).
- **Toast** glass (éxito/alerta/error).
- **Skeletons** con shimmer para cargas; estados vacíos que enseñan y ofrecen la acción.
- **Chat (Asistente)**: burbujas glossy (usuario azul a la derecha, bot glass a la izquierda),
  indicador de escritura con puntos rebotando, chips de sugerencia y composer glass con textarea auto-creciente.

## Motion

Espectáculo continuo (sin gating reduced-motion, por preferencia explícita):
burbujas ascendentes, bokeh, orbes flotantes con parallax suave del mouse, pez nadando
por el cielo, lens flare que sigue al cursor, ripples al hacer clic, barrido de brillo
en cards al hover, gloss-text con sheen en el título, césped meciéndose al pie, toasts
con rebote. Eases del sistema: `bounce (0.34,1.56,0.64,1)`, `smooth (0.22,0.61,0.36,1)`,
`aero (0.22,1,0.36,1)`. Transiciones de estado 150–250 ms; reveals al entrar en viewport.

## Assets propios reutilizados

- `assets/sky-banner.png` (banner 2688×1152 del usuario): fondo fijo con cielo, colinas, gotas, sol y pez dorado.
- Pez betta SVG, orbes glossy, logo de burbujas, césped procedural de dos capas (generado por seed).
- Favicon de burbujas.

## Estados

- Cargando: skeletons glass con shimmer.
- Vacío: mensaje + botón que resuelve ("Correr primera revisión").
- Error: toast rojo glass + estado en línea del panel afectado.
- Acción en curso: botón en loading + ventana Aero con log en vivo; al terminar, toast y refresco de datos.
