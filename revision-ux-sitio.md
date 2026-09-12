# Revisión de usabilidad y diseño — docs/ (sitio público)

Probado en Chrome contra `python3 -m http.server --directory docs`, en claro y oscuro, a 1440×900
y en angosto (559 px de viewport real, y 390 px de ancho de columna como cruce). Cada hallazgo lleva la medición que lo
sostiene. Las buenas prácticas citadas salen de fuentes primarias (NN/g, W3C, web.dev, MDN,
Sarah Higley, MLH, Devpost), no de listicles.

**Nada de esto es un bug del producto.** Los 393 tests pasan, el gate del demo está limpio, el
ledger tamperea y restaura bien, no hay overflow horizontal, el CLS de carga es 0 y el click de
tamper bloquea 5 ms. El sitio está sano; lo que sigue es sobre si un jurado frío lo entiende.

---

## Lo que ya está bien (y conviene no tocar)

| Verificado | Medición |
|---|---|
| Contraste AA en los dos temas | claro: `.src` 5.60 · hash 4.51 · check rojo 6.10 — oscuro: 6.60 / 5.01 / 10.43 |
| Sin layout shift en la carga | CLS = 0 en carga limpia de `#ledger` |
| Respuesta al tamper | 5 ms de bloqueo sincrónico; sin riesgo de INP (umbral 200 ms) |
| Vistas ocultas con `hidden` | los 3 `<h1>` no colisionan: solo uno está en el árbol de accesibilidad |
| `aria-current="page"` en el nav | presente y correcto |
| Error del fetch del ledger | manejado, con mensaje que apunta al archivo committeado |
| Objetivos táctiles principales | `.nav-link` 76×44 · `.btn-icon` 44×44 |

---

## P0 — Rompen la demo

### 1. En pantalla angosta, el botón principal está a más de una pantalla de su propio efecto

Medido en `#ledger`, por dos caminos independientes:

```
a 559 px de viewport real     distancia 870 px  = 1,24 pantallas
a 390 px de ancho de columna  distancia 1116 px = 1,59 pantallas de celular

Tamper with the verdict → [2 párrafos densos + los 8 registros] → exit 0 / exit 40
```

Un jurado con el teléfono toca el botón que es **toda la tesis del proyecto** y no ve cambiar
nada. Tiene que scrollear a ciegas para descubrir que funcionó. En desktop no pasa porque las dos
columnas están lado a lado; en angosto se apilan y el veredicto queda al fondo.

**Fix (una línea, y resuelve también el punto 2):** al tamperear o restaurar, llevar el panel de
veredicto al viewport y darle foco.

```js
verdict.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
```

Es exactamente el patrón "pull revelation" que NN/g respalda: la respuesta aparece donde y cuando
el usuario tocó la funcionalidad, no antes y no en otro lado.
<https://www.nngroup.com/articles/onboarding-tutorials/>

### 2. El cambio de veredicto no se anuncia: cero regiones vivas en todo el sitio

```js
document.querySelectorAll('[aria-live],[role=status],[role=alert]').length  // → 0
```

`setUpLedger` reescribe `#ledger-verdict` y la lista de checks, y un lector de pantalla no recibe
nada. Es la interacción central del sitio. WCAG 4.1.3 Status Messages (AA).

**Fix:** `role="status"` en el contenedor del veredicto. Con eso, más el `scrollIntoView` del
punto 1, la misma corrección sirve para vista y para audio.

### 3. Los hashes copiables son invisibles como control

```
tag: BUTTON · 102×14 px · border 0 · background transparent
color rgb(132,136,155) = el mismo gris del texto estático
sin aria-label → se anuncia "sha256 dos puntos 34e473c…, botón"
title: "sha256:…\n\nClick to copy."  ← no existe en táctil
```

La única pista de que se puede hacer clic es `cursor:pointer`, que en un teléfono no existe. La
feature que se agregó para sostener el "no me creas, verificalo" es indescubrible salvo que pases
el mouse justo por encima.

**Fix mínimo:** `aria-label="Copy the full hash of record N"` y una señal visual permanente —
subrayado punteado o un icono de copiar de 24×24 al lado. WCAG 2.2 SC 2.5.8 pide **24×24 CSS px**
(el AA es 24, no 44 — 44 es 2.5.5 AAA); 14 px de alto zafa solo por la excepción de espaciado.
<https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html>

---

## P1 — Accesibilidad verificada en el navegador

### 4. El tablist declara `role="tab"` pero no implementa el teclado

```js
tabs[0].focus();
tabs[0].dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight', bubbles:true}));
// aria-selected → ["true","false","false"]  — sin cambios
// los 3 tabs tienen tabindex 0 (falta roving tabindex)
```

Declarar el rol sin el contrato de teclado es peor que no declararlo: el lector de pantalla
anuncia "pestaña 1 de 3" y las flechas no hacen nada.

**Fix:** o se agregan flechas + roving tabindex, o se bajan a botones comunes y se borra el ARIA.
La segunda opción es más barata y honesta.

### 5. `prefers-reduced-motion` solo cubre el puntito del logo

`nocturne.css:278` apaga la animación de `.dot` y nada más. El replay es un `setInterval` de
`STEP_MS` que repinta paso a paso y **ignora la preferencia**.

**Fix:** `if (matchMedia('(prefers-reduced-motion: reduce)').matches) { paintStep(total); return; }`

### 6. La preferencia de tamaño de fuente del usuario no hace absolutamente nada

```
font-size declarados: 106   (14 en nocturne.css + 92 inline en index.html)
que usan rem:           0
```

Comprobado: con `html { font-size: 24px }`, el párrafo del run sigue midiendo **15 px**. Un
usuario con baja visión que subió el tamaño por defecto del navegador ve el sitio idéntico. El
zoom de página sí funciona, pero es la otra accommodation.

Y el sitio ya vive cerca del piso: hay texto a 11 px, 11,5 px y 12 px.

**Fix:** `rem` en los extremos de los `clamp()` y en los tamaños fijos. Es un find/replace
mecánico (÷16), no un rediseño. Ver F94 y Roselli sobre tipografía responsive y zoom.
<https://www.w3.org/WAI/WCAG21/Techniques/failures/F94.html> ·
<https://adrianroselli.com/2019/12/responsive-type-and-zoom.html>

### 7. La vista del ledger no tiene `h1` y sus columnas no son encabezados

```js
// dentro de #ledger: ["H2: The chain closes cleanly. The check still fails."]
// "The records" y "verify — recomputed in your browser" → div.kicker
```

`#ledger` es un deep link que un jurado puede recibir directo. Quien navega por encabezados
encuentra uno solo en toda la vista, y `exit 0 — the ledger verifies` —el resultado— tampoco lo es.

**Fix:** `h1` para el título de la vista, `<h3 class="kicker">` para las dos columnas. Cero CSS.

### 8. Los 67 tooltips `title` no funcionan donde más falta hacen

El consenso de accesibilidad es unánime y vale la pena leerlo antes de defender la decisión:

- MDN enumera a quién deja afuera: táctil, teclado, lectores de pantalla, magnificadores,
  motricidad fina. <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/title>
- Higley: *"do not use the `title` attribute to create a tooltip"*. Solo hover, anuncio
  inconsistente, imposible de leer con magnificación. <https://sarahmhigley.com/writing/tooltips-in-wcag-21/>
- WebAIM: no se lee por defecto en la mayoría de las combinaciones navegador/AT; nunca información
  vital. <https://webaim.org/articles/label-name/>
- El patrón Tooltip de la APG sigue marcado *work in progress, sin consenso*. No es norma citable.
  <https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/>

La regla que se usó al escribirlos ("explican, no informan") es la que salva la situación: nadie
pierde información. Pero entonces **son 67 atributos que no llegan a ninguna de las personas que
más necesitan la explicación**.

**Recomendación, y es la barata:** no construir un tooltip custom con las tres propiedades de WCAG
1.4.13 (dismissible, hoverable, persistent). Higley propone lo contrario — preguntarse *"¿dónde
más podría ir este texto?"*. Para los 5 tipos de registro del ledger y los 3 símbolos de
verificación, la respuesta es **una leyenda visible de una línea arriba de la lista**. Se ve en
teléfono, se lee con lector de pantalla, y borra 8 `title` de una.

---

## P2 — Los primeros 10 segundos

NN/g: la decisión de quedarse o irse se toma en ~10 s; quien pasa de 30 s suele quedarse más de
2 minutos. <https://www.nngroup.com/articles/how-long-do-users-stay-on-web-pages/>
Contexto de jurado: MLH presupuesta **4 minutos por proyecto** y ≥3 jurados distintos.
<https://guide.mlh.com/general-information/judging-and-submissions/judging-plan>

### 9. Las tres CTAs caen debajo del pliegue en un portátil estándar

A 1440×900 (viewport real 1440×731 con el chrome del navegador):

```
"Watch the demo · 2:50"    y = 757   ← fuera
"See a verified run"       y = 757   ← fuera
"Tamper with the ledger"   y = 757   ← fuera
```

Causa: 192 px de padding superior antes del `h1`, más un `h1` que a 1440 satura el `clamp` en
**104 px** y ocupa 212 px él solo.

Además, las tres tienen el mismo peso tipográfico y el mismo tamaño. El estudio de 100+ landings
de devtools (2025) documenta **dos** CTAs en el hero: una primaria con lenguaje específico del
producto y una secundaria visualmente subordinada. NN/g empuja a **una** sola acción prioritaria.
**Ninguna fuente respalda tres.**
<https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025> ·
<https://www.nngroup.com/articles/homepage-design-principles/>

**Fix:** bajar el `clamp` del `h1` a ~76 px de máximo y recortar el padding superior. Con eso las
CTAs entran. Y degradar "Tamper with the ledger" a link de texto — el nav ya lleva a esa vista.

### 10. El hero no muestra el producto, y tiene 622 px de columna vacía al lado

El párrafo del hero está capado a 558 px dentro de un shell de 1180 px. Los 622 px restantes están
vacíos en las tres vistas.

El patrón estándar para landings de librería/SDK/infra es **un bloque de código o salida de
terminal arriba del pliegue** — y acá el activo es literalmente eso: ocho líneas de
`ledger.example.jsonl`, o el bloque `exit 0 · 8 records · head sha256:9d33…`. Hoy hay que hacer
dos clics para ver la única cosa que nadie más tiene.
<https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025>

Devpost lo dice desde el otro lado: *si no podés explicar cómo se usa en una o dos oraciones, es
demasiado complicado*. Un `exit 0` con su hash al lado del titular es esa oración.
<https://info.devpost.com/blog/understanding-hackathon-submission-and-judging-criteria>

### 11. El header se parte en dos filas entre ~420 y ~600 px

```
760 px de ancho → header 80 px, una fila
559 px de ancho → header 141 px = 20 % del viewport
                  fila 2: el botón GitHub, solo
```

El arreglo anterior apuntó a 320 px; la rotura vive en la franja de 420–600 px, que es donde caen
los teléfonos en horizontal, las tablets chicas y una ventana partida al medio. Causa: el header
es un único `flex-wrap` con los estilos **inline en el HTML** (por eso las reglas del CSS no lo
tocan) y sin ninguna regla sobre qué cede primero.

**Fix:** en esa franja, el botón GitHub pasa a `.btn-icon` (solo el octocat, 44×44) — deja de ser
el elemento más ancho y la fila cierra sin esconder el link al repo.

### 12. Cambiar de escenario mueve la página 672 px

Alturas de los tres paneles: **1016 / 1509 / 1688 px**. Quien está mirando la transcripción y
cambia de pestaña ve saltar todo lo que tiene debajo. No cuenta para CLS (hay input reciente),
pero se siente igual.

**Fix:** `min-height` en el contenedor de paneles igual al más alto, o una transición de opacidad.

---

## P3 — Distribución (barato, alto retorno para un hackathon)

### 13. El link compartido llega pelado

```
og:*        → 0
twitter:*   → 0
rel=icon    → 0
theme-color → 0
```

El proyecto se comparte en Slack, Discord y Devpost. Hoy la preview es una caja gris con la URL.
Cuatro etiquetas `og:` y una imagen de 1200×630 es el cambio de mayor retorno por línea de todo
este documento — sobre todo dado que MLH deja el video de 2 minutos como material de deliberación.

### 14. Google Fonts bloqueante en un producto cuyo titular es "0 dependencies"

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600…">
```

Tres detalles:

1. Es una hoja de estilo de terceros que **bloquea el render**. En local el FCP es de 68 ms, pero
   desde GitHub Pages con una conexión de conferencia es la primera cosa que puede fallar.
2. Pide el **weight 600, que el sitio no usa en ningún lado** (solo 400 y 500). Se descarga una
   cara que nunca se pinta.
3. El estadístico del hero dice `0 dependencies — stdlib only`. Un jurado que abre devtools ve la
   página pidiéndole tipografías a Google. No es contradictorio (sitio ≠ producto), pero es un
   detalle gratis de regalar.

**Fix:** autohospedar los dos `.woff2` que se usan en `docs/`, o caer al stack del sistema. Suma
al argumento en vez de restarle.

### 15. El script de tema en el `<head>` — trade-off consciente, no best practice

web.dev es explícito en que "casi nunca es necesario agregar scripts síncronos al `<head>`" porque
bloquean el render. <https://web.dev/articles/optimize-lcp> Acá es la única forma de evitar el
flash de tema incorrecto, y el script ya hace lo mínimo (leer `localStorage`, estampar el
atributo). **No lo cambies.** Queda anotado para que sea una decisión y no un olvido: no encontré
ninguna fuente primaria que bendiga la excepción.

---

## Lo que revisé y decidí no reportar

- **"Replay the run" NO tira el foco al `<body>` — retractado.** Lo había reportado como medido y
  al reverificarlo sobre carga limpia no reproduce: `document.activeElement` sigue siendo el botón
  durante los 8 segundos del replay, y un `Tab` real aterriza en el índice 6 de 13 focusables, que
  es el propio botón, no al principio del documento. La lectura original fue un artefacto de una
  página que yo ya había manoseado, con un replay anterior todavía en vuelo. Deshabilitar un
  elemento enfocado sigue siendo un antipatrón conocido, pero acá no produce el daño que le
  atribuí, y sin medición que lo sostenga no es un hallazgo.

- **El `412` del badge y del stat tile.** Parece mal (ringdown da 393) pero es correcto: 393 +
  19 del receiver = 412, y CI corre los dos paquetes. La etiqueta dice "tests, green in CI", que
  es exacto. Único matiz: solo cierra si el lector ya sabe que hay dos paquetes.
- **`clamp()` y Core Web Vitals.** No hay ninguna fuente primaria que vincule `clamp()` a
  LCP/INP/CLS. El riesgo real de la tipografía fluida es de accesibilidad (punto 7), no de
  performance.
- **2.4.11 Focus Not Obscured.** Intenté reproducirlo con el header sticky y no pude: el foco
  aterrizó a 344 px con el header terminando en 141 px. No aplica.
- **Contraste.** Pasa AA en los dos temas, en todos los contextos que medí. El más ajustado es el
  hash del ledger en claro (4.51), pero pasa.
- **Performance del tamper.** 5 ms. Lejos del umbral de INP (200 ms). No hay nada que optimizar.
- **"refreshing every 5s"** en la vista Receiver es texto estático de una captura, no un poll real.
  La sección ya aclara "Demo infrastructure, not the product", así que lo dejo como nota.

---

## Orden sugerido, por retorno sobre esfuerzo

| | Cambio | Toca | Por qué primero |
|---|---|---|---|
| 1 | `scrollIntoView` + `role="status"` en el veredicto | `app.js` | Arregla la demo en teléfono y el anuncio a lector de pantalla con la misma corrección |
| 2 | Etiquetas `og:` + favicon | `index.html` | Cinco líneas; cambia cómo llega el link a cada jurado |
| 3 | `h1` + `h3` en la vista ledger | `index.html` | Cero CSS |
| 4 | `aria-label` y afordancia visible en los hashes | `app.js`, `nocturne.css` | Hace descubrible una feature que ya existe |
| 5 | `h1` más chico y CTAs arriba del pliegue | `index.html` | Los primeros 10 segundos |
| 6 | Leyenda visible del ledger en vez de 8 `title` | `index.html` | Menos markup, más gente alcanzada |
| 7 | `prefers-reduced-motion` en el replay | `app.js` | Una línea |
| 8 | `rem` en los tamaños de fuente | los tres archivos | Mecánico pero toca 106 lugares |
| 9 | GitHub como `.btn-icon` bajo 600 px | `nocturne.css` | Recupera 61 px de pantalla en la franja rota |
| 10 | Autohospedar Inter | `index.html`, `docs/` | Saca un tercero del camino crítico |
