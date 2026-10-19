# Competidores — CALL-E (Local Atlas, ganador Most Practical Use Case)

| | |
|---|---|
| Fecha | 2026-10-19 |
| Modo | hackathon |
| Evaluados | 1 (`omarmiri/Local-atlas`) · clonados 1 (borrado) · **nada se ejecuto** |
| Ventana | submissions 2026-07-23 → 2026-09-14 (ficha publicada 2026-09-10) |

## En criollo

- **Que se miro:** el repo, la ficha de Devpost y la web en vivo de Local Atlas, contra Ringdown con las mismas sondas.
- **Quien es la amenaza:** Local Atlas es la mas fuerte que vimos. Su tesis (guardar la respuesta y no volver a llamar) esta en el codigo, no solo en la ficha [3].
- **Como estamos:** en rigor tecnico y en prueba de evidencia estamos arriba; en producto e impacto estamos abajo.
- **Que conviene hacer:** cuantificar impacto con numeros reales y mostrar la reutilizacion de respuestas. Es lo que mas pesa y lo que mas nos separa.

**Pesos del jurado** (`docs/judging.tsv`: los cuatro criterios "equally weighted"):

| Criterio | Peso | Secciones que lo responden |
|---|---:|---|
| Real World Impact | 25 | 1, 6 |
| Quality of the Idea | 25 | 7, 4 |
| Technical Implementation | 25 | 4, 5, 6, 10 |
| Product Experience & Demo | 25 | 1, 8 |

**Lo que no se pudo ver** — el margen de error de todo lo que sigue:

- No se ejecuto nada: que el cache de respuestas funcione en vivo, y que los tests pasen, quedan como lectura de codigo [3][5].
- Cuantas llamadas reales hizo y cuantas respuestas se reutilizaron: sin evidencia (no hay ledger ni contador publico).
- El video de Devpost (`youtu.be/VHswi1U5qkE`): existe, su contenido no se vio.

---

## Tabla comparativa

Escala: `fuerte` · `cumple` · `flojo` · `ausente` (se miro y no esta) · `sin evidencia` (no se pudo ver).

| Proyecto | Nicho | Real World Impact | Quality of the Idea | Technical Implementation | Product Experience & Demo | Nota | Amenaza |
|---|---|---|---|---|---|---:|---|
| `omarmiri/Local-atlas` | guia local con mapa que llama para verificar hechos | cumple | fuerte | fuerte | fuerte | 9/10 | alta |
| `gmassello/ringdown` (tuyo) | escalada de guardia con llamada verificada | flojo | fuerte | fuerte | cumple | 8/10 | — |

**Amenaza** es contra *tu* entrada, no calidad absoluta: alta porque comparte el nucleo (llamar, citar lo que dijo la persona, no inventar) y suma producto.

---

## `omarmiri/Local-atlas` — Local Atlas (Ask the Place)

<!-- ficha -->

**Que hace:** un mapa de cualquier pueblo de EE.UU./Canada donde, si falta un dato de un comercio, una IA llama una sola vez y la respuesta queda guardada, fechada y citada para el que pregunte despues.

| | |
|---|---|
| Repo | https://github.com/omarmiri/Local-atlas · creado 2026-07-19 · JavaScript · MIT [1] |
| Demo | https://local-atlas-api.onrender.com · `curl` 200 en 0.57 s, llamadas reales activas [2] |
| Devpost | `local-atlas-with-1st-party-faqs` · video si · ficha 2363 palabras [4] |
| Equipo | 1 contribuyente (159 de 159 commits) [5] |
| Historial | primer commit 2026-07-19 · 159 commits · previos a la apertura (2026-07-23): **si, 74**; el modulo de llamadas `calle.js` aparece recien el 2026-08-09 [5][6] |

| Criterio | Veredicto | Evidencia |
|---|---|---|
| Real World Impact 25% | cumple | App en vivo con llamadas reales activas [2]; **cero numeros de impacto** (ni llamadas, ni respuestas reutilizadas) en ficha ni README [4] |
| Quality of the Idea 25% | fuerte | Reuso en codigo: busca respuesta vigente por hash de pregunta y, si no, por similitud con Gemini, antes de marcar [3] |
| Technical Implementation 25% | fuerte | 98 tests, 200 asserts, 7 archivos, CI en Node 20 y 22 [5][7]; 7 chequeos antes de publicar un hecho [3] |
| Product Experience & Demo 25% | fuerte | PWA, 6229 lineas de `index.html`, 14 plantillas, vista previa de confirmacion antes de llamar [3][8] |
| Calidad de codigo | cumple | 2 dependencias; 0 tests sobre reuso, cupo diario o dedupe [3] |
| Seguridad | cumple | Sin `.env` en el historial [5]; `/api/health` publica la clave anonima de Supabase (publica por diseno, no se transcribe) [2] |

**Lo mas fuerte:** el producto: mapa, cuentas, plantillas, comparar 2-3 comercios en una llamada, borrar cuenta [3][8].
**Donde se cae:** no mide su propia tesis: ninguna cifra de aciertos de cache ni de llamadas evitadas [4]; y no hay registro a prueba de alteraciones.
**Sin evidencia:** el video, y si el cache funciona en la practica (no se ejecuto).

### Las cuatro preguntas del pedido

| # | Pregunta | Respuesta medida |
|---|---|---|
| 1 | El cache de llamadas, existe? | **Existe en el codigo**: respuesta vigente por hash de pregunta, luego por similitud semantica con Gemini, solo si falla el hash; un recheck lo saltea [3]. Ademas candado de 10 min por pregunta y `Idempotency-Key` [3]. Pero **0 tests** lo cubren, pese a que el README dice "cada regla esta testeada" [3] |
| 2 | Como guarda la evidencia? | Cada hecho lleva `evidenceQuote` (≤200 caracteres), `collectedAt`, `expiresAt`, `staffConfidence`, `source: first_party_phone`, `simulated` [3]. La cita debe ser un turno entero del personal o un fragmento de 12+ caracteres; si no, baja a `unclear` [3]. **No guarda quien contesto** (sin campo de nombre o rol) y **no hay cadena de hashes**: el hash solo ata la tarea enviada (`taskHash`) [3]. Ringdown sella cada veredicto en un ledger encadenado re-derivable offline [9] |
| 3 | Que tiene de producto que nosotros no? | PWA, mapa Leaflet con 18 pestanas, 14 plantillas por categoria, preguntas sugeridas por IA, rondas de 2-3 comercios, cuentas y borrado, vista previa de confirmacion [3][8]. Ringdown: una pagina y un demo [10] |
| 4 | Como demuestra impacto? | **No lo cuantifica**: sin llamadas hechas, sin tasa de reuso, sin costo evitado en ficha, README ni codigo [4]. La unica cifra es un caso de proveedores de mapas (64 lugares), ajeno al impacto [4] |

---

## Donde queda tu proyecto

| Criterio | tu proyecto | `omarmiri/Local-atlas` |
|---|---|---|
| Reuso/dedupe de respuestas | una llamada por escalon, clave de idempotencia; sin reuso entre usuarios [9] | si, exacto y semantico, 0 tests [3] |
| Evidencia por respuesta | ledger con hash encadenado, re-derivable offline [9] | cita + fecha + expiracion, sin cadena ni quien contesto [3] |
| Tests / asserts | 404 funciones de test en los dos paquetes, 738 asserts solo en Ringdown [11] | 98 tests, 200 asserts [5] |
| Commits | 102, primer commit 2026-08-09, 0 previos a la apertura [11] | 159, 74 previos a la apertura [5] |
| Producto en vivo | GitHub Pages 200 en 0.55 s; receptor `/demo` 200 en 0.76 s [10] | 200 en 0.57 s, app completa con cuentas [2] |
| Impacto cuantificado | sin cifras de uso; una llamada real fechada 2026-08-20 [10] | ninguna [4] |

### Sugerencias

| # | Sugerencia | Por que importa | Criterio (peso) | Origen | Evidencia | Esfuerzo | Mueve nota |
|---|---|---|---|---|---|---|---|
| S-01 | Publicar numeros reales: llamadas hechas, veredictos, minutos de guardia ahorrados, por escrito en la ficha/README | El jurado premio a quien llamo "practico"; ninguno de los dos cuantifica | Real World Impact (25%) | hueco | Local Atlas y Ringdown sin cifras [4][10] | medio | si |
| S-02 | Mostrar en el demo una respuesta ya verificada que se vuelve a leer sin llamar de nuevo (o un re-chequeo que reusa el veredicto del ledger) | Su tesis "no llamar" es lo que gano; la nuestra hoy no se ve | Quality of the Idea (25%) | brecha | cache exacto + semantico en `calle.js` [3] vs una llamada por escalon [9] | medio | si |
| S-03 | Poner en primer plano que el ledger es re-derivable offline y que el de ellos no (cita sin cadena ni "quien contesto") | Es nuestra diferencia tecnica verificable | Technical Implementation (25%) | brecha | `taskHash` solo ata la tarea, no hay cadena [3] | bajo | si |
| S-04 | Cerrar el techo de verificacion en vivo (hoy una corrida real termina en salida 45) | Un demo real que no confirma resta a Impact y a Demo | Product Experience & Demo (25%) | brecha | Local Atlas: llamadas reales activas y hechos publicados [2][3]; techo propio documentado en CLAUDE.md [11] | alto | si |
| S-05 | Agregar mas pantallas/screenshots y una vista de producto (hoy 4 contra 14 del nicho) | Mas superficie de producto | Product Experience & Demo (25%) | brecha | `benchmark-call-e.md`: 4 screenshots, mediana 14 | bajo | **cosmetico** |

> Control de sesgo: Ringdown salio abajo en 2 de 4 criterios del jurado (Impact `flojo`, Product `cumple`) y se revisaron las celdas comodas (Technical y Idea): Technical se sostiene por 404 tests y capas verificadas por test [11], Idea se sostiene por el ledger [9]; pero Local Atlas tambien tiene tesis en codigo [3], asi que la diferencia en Idea es de enfoque, no de nivel.

---

## Apendice — como se midio

<!-- ficha -->

| Ref | Comando |
|---|---|
| [1] | `jq '{fork,created:.created_at,lang:.language,license:.license.spdx_id,homepage,archived}' Local-atlas.json` |
| [2] | `curl -s -o /dev/null -w '%{http_code} %{time_total}s' https://local-atlas-api.onrender.com/` y `curl -s https://local-atlas-api.onrender.com/api/health` (campo `calle.realCalls`) |
| [3] | Lectura de `README.md` y `calle.js` del clone superficial (`sed -n`, `grep -nE "reused\|Idempotency\|quoteBinds\|TEMPLATES\|createHash"`), lineas 545-580, 1109-1123, 1186-1214, 1341-1400 |
| [4] | `curl -A Mozilla/5.0 https://devpost.com/software/local-atlas-with-1st-party-faqs` → texto plano, busqueda de cifras de impacto y "Built With" |
| [5] | `gh api repos/omarmiri/Local-atlas/commits --paginate`, `git rev-list --count HEAD`, `grep -cE '^\s*(test\|it)\(' test/*.js` y `grep -cE 'assert\.'` |
| [6] | `gh api "repos/omarmiri/Local-atlas/commits?until=2026-07-23T00:00:00Z"` (74) y `commits?path=calle.js` (primero 2026-08-09) |
| [7] | `cat .github/workflows/test.yml` (matriz Node 20/22, corre `npm test`); `gh run list` → 1 corrida `tests` success 2026-09-10 |
| [8] | `wc -l` de `index.html` (6229), `server.js` (1972), `calle.js` (2527); README "Feature map" |
| [9] | Lectura de `apps/python/ringdown/ringdown/audit.py` (hash por registro, `prev`) y `CLAUDE.md` del proyecto propio |
| [10] | `curl` a `https://gmassello.github.io/ringdown/` y `https://calle-receiver.onrender.com/demo`; README propio (gif de llamada real 2026-08-20) |
| [11] | `git rev-list --count HEAD`, `git log --until=2026-07-23`, `grep -hE '^\s*(async )?def test_' apps/python/*/tests/*.py`, `grep -rhE '^\s*(assert\|self\.assert)'`; `.env` propio no trackeado (`git check-ignore`) |
