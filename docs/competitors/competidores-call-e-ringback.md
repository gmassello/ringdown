# Competidores — CALL-E (call-e.devpost.com)

| | |
|---|---|
| Fecha | 2026-10-19 |
| Modo | hackathon |
| Evaluados | 1 · clonados 1 (rama `feat/ringback-app`, solo `apps/python/ringback/`, borrado al final) · **nada se ejecuto** |
| Ventana | submissions 2026-07-23 → 2026-09-14 [1] |

## En criollo

- **Que se miro:** RingBack (Honorable Mention, $1.000), el rival mas parecido: mismo lenguaje, cero dependencias, enmascara telefonos y prueba a quienes no se llamo.
- **Quien es la amenaza:** RingBack. Gana por producto visible: asistente de 3 pasos, agenda, pantallas, 1221 pruebas [6], y dice con la voz de un cliente a quien le sirve.
- **Como estamos:** ganamos en ingenieria de verificacion (cadena de hashes, capas forzadas por test); perdemos en superficie de producto y en demostrar una llamada real exitosa.
- **Que conviene hacer:** mostrar una pantalla operable (no solo un replay), nombrar el usuario y la plata en juego, y decir en voz alta que se recorto y por que.

**Pesos del jurado** (`docs/judging.tsv`: 4 criterios "equally weighted"):

| Criterio | Peso | Secciones que lo responden |
|---|---:|---|
| Real World Impact | 25% | 1, 6 |
| Quality of the Idea | 25% | 7, 4 |
| Technical Implementation | 25% | 4, 5, 10, 11 |
| Product Experience & Demo | 25% | 1, 6, 8 |

**Lo que no se pudo ver** — el margen de error:

- Las llamadas reales de RingBack: solo las afirma su ficha de Devpost [9]; no hay transcripcion ni linea de auditoria commiteada (`donnees/` no esta en el repo).
- Si sus 1221 pruebas pasan: no se ejecuto nada. El README dice "all green" [6].
- Que muestra el video (YouTube `S909yG8oZkU`, responde 200 [10]): no se vio el contenido, solo que existe.

---

## Tabla comparativa

Escala: `fuerte` · `cumple` · `flojo` · `ausente` (se miro y no esta) · `sin evidencia` (no se pudo ver).

| Proyecto | Nicho | Product Experience (25%) | Technical Implementation (25%) | Real World Impact (25%) | Quality of the Idea (25%) | Nota | Amenaza |
|---|---|---|---|---|---|---:|---|
| `Ludo321/awesome-phone-call-agents` (RingBack) | Citas: rellenar huecos de agenda llamando a una lista | fuerte | fuerte | cumple | cumple | 8/10 | alta |
| `gmassello/ringdown` (propio) | Escalamiento de guardia + verificacion independiente | flojo | fuerte | cumple | fuerte | 7/10 | — |

**Amenaza** es contra *tu* entrada: RingBack es alta porque comparte stack y garantias, y le gana en la columna mas visible para un jurado.

---

## `Ludo321/awesome-phone-call-agents` — RingBack

<!-- ficha -->

**Que hace:** una app web local para un profesional independiente: cuando se libera un turno, llama de a una persona hasta el primer "si" y actualiza la agenda sola.

| | |
|---|---|
| Repo | https://github.com/Ludo321/awesome-phone-call-agents · creado 2026-09-03 · fork del monorepo `CALLE-AI/awesome-phone-call-agents` (entrega via PR #297, abierto) · Python · MIT [2] |
| Demo | sin sitio publicado (`homepage` vacio); corre en la maquina de quien la baja [2] |
| Devpost | `ringback-sumnr6` · video si [10] |
| Equipo | 1 autor (6 de 6 commits del PR) [3] |
| Historial | primer commit del PR 2026-09-03, 6 commits, posterior a la apertura del 2026-07-23; el fork hereda el historial del monorepo (desde 2026-05-22) [3] |

| Criterio | Veredicto | Evidencia |
|---|---|---|
| Product Experience & Demo 25% | fuerte | Asistente de 3 pasos, agenda, lista de clientes, ajustes, EN/FR, claro/oscuro [4]; 33 menciones de pantalla/asistente/panel en el README contra 1 del propio [11]; reporte de banco de pruebas HTML commiteado [4] |
| Technical Implementation 25% | fuerte | Solo libreria estandar: unico `urllib.request` en `calle_client.py` [5]; 1221 funciones de prueba, 4917 lineas de asercion [6]; banco de punta a punta de 661 chequeos en 121 combinaciones (segun README) [6]; tres cerrojos para llamar de verdad [7] |
| Real World Impact 25% | cumple | Persona clara (fisio, peluquero, profesor de musica: "una silla vacia y el ingreso de un dia") [9]; sin cifras de plata propias, 4 menciones de dinero en el README [11] |
| Quality of the Idea 25% | cumple | Cascada "primer si" con 5 tipos de campana; recorta 3 tipos "porque sus respuestas no tenian donde ir" [8]; no es una idea invertida como la propia |
| Calidad de codigo | flojo | Archivos gigantes: `serveur.py` 11194 lineas, `test_ringback.py` 28894, `calle_client.py` 2853 [4]; sin linter ni config de estilo en el subdirectorio [12] |
| CI/CD | ausente | Sin workflows en la rama; el PR no reporta checks [13] (es "sin CI", no "CI roto") |
| Seguridad | cumple | Telefono enmascarado en 31 lugares del codigo [5]; clave API guardada solo si el usuario lo elige; 0 coincidencias de credenciales en el subdirectorio [14] |
| Trazabilidad | flojo | Auditoria `audit_appels_reels.jsonl` solo de llamadas reales, una linea con numero enmascarado y estado; sin cadena de hashes [7][15] |

**Lo mas fuerte:** prueba con contador que el numero "perdonado" nunca se marco, en orden: 3 marcados, el cuarto jamas [6]. Mas el asistente de 3 pasos.
**Donde se cae:** sin CI, sin linter, archivos de 11k y 29k lineas, auditoria sin integridad; la llamada real exitosa solo esta en palabras.
**Sin evidencia:** llamadas reales, contenido del video, que las pruebas pasen.

**Respuestas a las tres preguntas del pedido:**

- **Superficie:** asistente de 3 pasos (situacion, mensaje editable con vista previa, cargar gente), agenda/planificador que lanza campanas, lista de clientes, seguimientos programados, importacion pegada/CSV/ICS, primer arranque guiado con ✗/✓ [8][4].
  Se demuestra con un banco que levanta el producto en un puerto temporal y deja un reporte HTML identico byte a byte entre corridas.
- **Como prueba:** `ClientCompteur` registra cada numero marcado; asegura 3 marcados en orden y `assertNotIn` del cuarto [6].
  Un servidor falso local demuestra que con los cerrojos puestos no sale ninguna request de red (segun README, no ejecutado).
- **Que acoto y dice:** "tres tipos de campana se quitaron porque sus respuestas no tenian donde ir" [8]; ademas el aviso del 403 de CALL-E ("la cuenta no esta autorizada") y que el cupo por intento es 1 [15].

---

## Donde queda tu proyecto

| Criterio | tu proyecto | `RingBack` |
|---|---|---|
| Pantallas operables | sitio estatico con replay (`docs/index.html`, `app.js`, `demo.gif`) [16] | asistente + agenda + clientes + ajustes [4] |
| Pruebas (funciones `test_`) | 404 [16] | 1221 [6] |
| Contador de marcados | 28 menciones de marcado/llamada unica en pruebas [16] | `ClientCompteur` con `assertNotIn` [6] |
| Integridad del registro | cadena de hashes, verificacion por otro canal [16] | linea simple, solo llamadas reales [15] |
| CI | si (`ci.yml`, linter en raiz) [16] | ausente [13] |
| Llamada real exitosa documentada | no: una corrida real termina siempre en 45 (dato de nuestro README) [16] | afirmada en Devpost, sin artefacto [9] |
| Commits / equipo | 102 · 2026-08-09 → 2026-09-13 [16] | 6 en el PR · 1 autor [3] |
| Demo publicado | `render.yaml` + keepalive en verde [16] | ninguno [2] |

### Sugerencias

| # | Sugerencia | Por que importa | Criterio (peso) | Origen | Evidencia | Esfuerzo | Mueve nota |
|---|---|---|---|---|---|---|---|
| S-01 | Una pantalla que se pueda operar (elegir escenario, ver la escalera, el veredicto y el ledger), no solo un replay | Un jurado juzga lo que puede tocar | Product Experience (25%) | brecha | RingBack: asistente de 3 pasos, 33 vs 1 menciones [11][4] | alto | si |
| S-02 | Publicar una pagina "que recortamos y por que" con las 3 o 4 cosas dejadas fuera | RingBack convierte el recorte en argumento de diseno | Quality of the Idea (25%) | brecha | `README` de RingBack: 3 tipos quitados por "sin destino" [8] | bajo | si |
| S-03 | Ponerle numero a la plata/tiempo en juego (que cuesta una guardia sin respuesta) | Hoy el impacto no tiene cifra visible | Real World Impact (25%) | brecha | RingBack 4 menciones de dinero vs 0 propias [11] | bajo | si |
| S-04 | Exhibir un test con contador por escalon, titulado en la ficha, que pruebe "al tercero no se lo llamo" | El jurado debe ver la garantia sin leer el codigo | Technical Implementation (25%) | brecha | `ClientCompteur` en `test_ringback.py` [6] | bajo | si |
| S-05 | Documentar en un artefacto la corrida real (aunque termine en 45), con lo que se aprendio | RingBack afirma una llamada real; nadie del set tiene una auditada | Product Experience / Technical (25%) | hueco | ni el repo de RingBack tiene artefacto de llamada real [9][15] | medio | si |
| S-06 | Tapar la estrella o el tamano del README | Nadie lo pondera | — | — | — | bajo | **cosmetico** |

> Control de sesgo: el propio sale peor en Product Experience, Impact y pruebas, no mejor en todo; las celdas mas comodas revisadas fueron integridad del registro, CI y la mencion de la corrida real. La senal de regex sobre README es aproximada: cuenta palabras, no calidad.

---

## Apendice — como se midio

<!-- ficha -->

| Ref | Comando |
|---|---|
| [1] | `curl -A 'Mozilla/5.0' https://call-e.devpost.com/rules` y `/details/dates` (gana `/rules`: 23 jul → 14 sep 2026) |
| [2] | `gh api repos/Ludo321/awesome-phone-call-agents` y `jq '{fork,created_at,license,homepage,archived}'` |
| [3] | `gh pr view 297 --repo CALLE-AI/awesome-phone-call-agents --json state,createdAt,changedFiles,commits` y `git log --format=%an` en el clone |
| [4] | `gh pr view 297 --json files` (adiciones por archivo) y arbol `git/trees/feat%2Fringback-app?recursive=1` filtrado por `apps/python/ringback/` |
| [5] | `grep -nE 'urllib.request\|http.client' ringback/*.py` y `grep -rn masquer_telephone ringback/*.py \| wc -l` |
| [6] | `grep -c 'def test_'` y `grep -cE 'self\.assert\|assert '` en `tests/test_ringback.py`; lectura de lineas 1190-1300; README seccion Testing |
| [7] | README secciones "Dry-run and preview behaviour" y "Side effects" |
| [8] | README seccion "Campaigns: five situations, three steps" |
| [9] | `curl -A 'Mozilla/5.0' https://devpost.com/software/ringback-sumnr6`, texto filtrado |
| [10] | `curl ... 'https://www.youtube.com/oembed?url=...S909yG8oZkU'` → 200 |
| [11] | regex de `docs/judging.tsv` aplicadas con `python3 -I` a ambos README (Product Experience: 33 vs 1; dinero: 4 vs 0) |
| [12] | `grep -E 'ruff\|flake\|mypy' -r .` en el subdirectorio: sin coincidencias de config |
| [13] | `gh run list --repo Ludo321/...` → `[]`; `gh pr checks 297` → "no checks reported" |
| [14] | `grep -rnEi` de patrones AKIA/sk-/clave literal en `apps/python/ringback/` → 0; secretos: valor no transcripto |
| [15] | README secciones "Credential handling", "Side effects", "If every call comes back 403" |
| [16] | Recuento sobre el repo propio: `grep -rE 'def test_'`, `git log`, `ls docs`, `gh run list --repo gmassello/ringdown` |
