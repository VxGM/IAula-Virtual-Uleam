# Product

## Register

product

## Users

Un solo usuario: el estudiante dueño del proyecto (ULEAM, Manta), en su PC con Windows,
en sesiones cortas entre clases o al final del día. Contexto: quiere saber en segundos
qué hay nuevo en su aula virtual y qué se entrega pronto, y lanzar acciones (revisar,
descargar, sincronizar con NotebookLM) sin abrir la terminal ni recordar comandos.

## Product Purpose

Panel local que resume la actividad del aula virtual (Moodle ULEAM) y ejecuta el toolkit
`iaula` con progreso visible: revisar novedades, descargar materiales, sincronizar con
NotebookLM y vigilar entregas. Éxito = saber en menos de diez segundos qué requiere
atención y actuar con un clic.

## Brand Personality

Frutiger Aero fiel al periodo 2004–2013: optimista, luminoso, "el futuro que nos
prometieron". Vidrio, agua, cielo y naturaleza idealizada. Voz cercana y clara en
español; el espectáculo visual es parte de la personalidad, no un extra.

## Anti-references

- Dashboard SaaS genérico: morado/glass plano, rejillas de cards idénticas, badges por todos lados.
- Minimalismo flat post-2013 que apaga el brillo.
- Modo oscuro por defecto.
- Decoración falsa: métricas inventadas, botones muertos, captions ornamentales.

## Design Principles

1. **El futuro es brillante.** Vidrio, agua y luz como lenguaje base; fidelidad al
   vocabulario Aero construido en casa (paleta, tipos y motivos de los proyectos
   frutiger del propio usuario, más su banner de cielo/colinas/gotas).
2. **Espectáculo con propósito.** Las burbujas, orbes, peces y destellos mantienen la
   escena viva; el movimiento también comunica estado (carga, éxito, error).
3. **Un vistazo basta.** Lo urgente primero (entregas y novedades); densidad de
   herramienta sin ruido; cada acción real a un clic.
4. **Todo real.** Cada botón ejecuta lo que dice; los estados vacíos enseñan; nada de
   métricas o textos de relleno.
5. **Una voz, tokens compartidos.** Segoe UI como voz única (la fuente real de la era),
   Nunito solo como display cuando esté disponible; la variedad viene de composición y color.

## Accessibility & Inclusion

- Contraste de texto AA sobre los paneles de vidrio (tinta oscura sobre glass claro).
- Foco visible en todo control interactivo; navegación completa por teclado.
- Sin gating de `prefers-reduced-motion`: el usuario pidió explícitamente que las
  animaciones siempre corran en sus propios assets (trade-off aceptado).
- Fallback `prefers-reduced-transparency`: el vidrio se vuelve sólido.
