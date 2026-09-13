# Ringdown — brechas detectadas y referencias para cerrarlas

Documento de trabajo extraído del punto 4 de `comparativa_calle_actualizada.md`
(escaneo del 2026-09-13 sobre `gmassello/ringdown` + los 15 mejores competidores de la hackathon CALL-E).

---

## Cómo leer las rutas

**Código de Ringdown.** Todas las rutas son relativas a la raíz del repo `gmassello/ringdown`.
El paquete vive en `apps/python/ringdown/`, así que `ringdown/verify.py` es en realidad
`apps/python/ringdown/ringdown/verify.py`. Las rutas de tests y README siguen la misma convención.

**Código de los competidores.** Las referencias apuntan al clon del monorepo comunitario:

```
~/calle-competitor-scan/monorepo/
```

Ese clon es *shallow* de la rama por defecto, o sea que contiene el estado **merged** de cada PR.
Es de solo lectura: no ejecutar nada de ahí, no abrir PRs, no modificarlo.

**Estado de los PRs de Ringdown.** #205 está merged (es el que cumple el requisito de submission);
**#512 está abierto** y es el que sube al monorepo el estado que este documento asume. Si #512 no se
mergea, el evaluador ve el #205: sin PagerDuty/Opsgenie, sin español, sin `sla-breach`, con README de
449 líneas. **Esa es la brecha 0 y no es de código.**

---

## Triage

El cierre es el **14 de septiembre de 2026, 23:45 SGT** — queda aproximadamente un día. Ordenado por
relación impacto/costo real, no por gravedad teórica:

| Prioridad | Brecha | Costo | Por qué ahora |
|---|---|---|---|
| **P0** | 0 — mergear el PR #512 | nulo (es apretar el botón) | Sin esto, la mitad del informe describe código que el jurado no ve |
| **P1** | 4.3 — `report.py` con 1 test | bajo | Es el agujero de cobertura más citable y se tapa con tests, sin tocar diseño |
| **P1** | 4.6 — CI sin lint/type-check | bajo | Dos líneas de workflow; es señal de rigor barata |
| **P2** | 4.7 — squash único + `[Unreleased]` | bajo | Cortar `0.1.0` en el CHANGELOG cuesta minutos |
| **P2** | 4.1 — el extractor se confirma a sí mismo | medio | Es la crítica más fuerte; un mitigante parcial es alcanzable |
| **P3** | 4.2 — ETA/cancelación/run lock | alto | Es trabajo de producto real, no de un día |
| **P3** | 4.4 — sin consola operable | alto | Rehacer el sitio como app en vivo no entra |
| **P3** | 4.5 — `calle-receiver` | medio | Se puede acotar el relato sin refactorizar |
| **P4** | 4.8 — extractor por regex | alto | Ceiling asumido y documentado; no se resuelve con parches |
| **—** | 4.9 — dominio angosto | n/a | No es tarea de código |

---

## 4.1. La verificación cruzada se confirma a sí misma

**Síntoma.** El "segundo canal" se re-parsea con **el mismo extractor** que el primero. Un bug en
`extract.py` produce el mismo error en los dos canales y los 10 checks pasan igual.

**Evidencia.**
- `ringdown/verify.py:61` — `extract(run.turns).disposition == "acknowledged"` dentro de `ack_holds`.
- `ringdown/verify.py:84` — `re_extracted = extract(run.turns)` dentro de `no_ack_checks`.
- Es la misma función que consume el primer canal, importada de `ringdown/extract.py` (351 líneas).
- Ya está admitido: `README.md:1142` (ceiling 23) — *"Hardening the extractor cannot be checked by the
  extractor… The failure is silent by construction."*

**Por qué importa.** El pitch dice "verifica por un segundo canal". Lo que el código sostiene es más
angosto: verifica que el **run** sea el mismo (call id, attempt id, teléfono, status, ventana — esos
6 checks son sólidos y sí cruzan canales), pero los 4 checks del bloque `ack_holds` son una
re-lectura del mismo lector. Si un jurado técnico lee `verify.py` va a ver exactamente esto.

**Referencia — quién lo resuelve mejor.**
`holdfor-board` usa **dos analizadores distintos** sobre el mismo texto, no dos lecturas del mismo:
- `~/calle-competitor-scan/monorepo/apps/python/holdfor-board/holdfor/scan.py:1-9` — scanner
  determinístico, con el comentario *"Nothing here calls a model"*. Es la **autoridad** sobre red
  flags aunque el agente no se haya detenido.
- `.../holdfor/extract.py:37-41` — lo que el agente reportó debe ser substring literal de un turno
  **del paciente**, o el registro se rechaza como `carried_words_not_verbatim`.
- ADR 0005 del proyecto: *"stop conditions are enforced twice"*.

Complemento útil: `redline` marca el ground truth del modo live como **testimonio humano** y lo
etiqueta como tal en la estructura de datos, en vez de mezclarlo con lo que dijo la plataforma —
`.../apps/python/redline/redline/transport/live.py:161-168` (`GroundTruth(..., declared_by="operator")`),
con el razonamiento en el docstring `live.py:22-25`.

**Qué tocar.** Dos caminos, el segundo es el barato:
1. *Caro y correcto:* un segundo lector independiente en un módulo nuevo (p. ej. `ringdown/attest.py`)
   con una estrategia distinta a `extract.py` — no la misma tabla de frases —, y que `ack_holds`
   compare ambos en vez de re-correr uno. Firma sugerida:
   `attest(turns: list[Turn]) -> Attestation`, y en `verify.py` un check nuevo del tipo
   *"los dos lectores coinciden en la disposición"*.
2. *Barato y honesto:* dejar el mecanismo como está pero **separar en el reporte** los checks que
   cruzan canales de los que no. Los 6 de `same_run` son cross-channel; los 4 de `ack_holds` son
   re-lectura. Hoy `verify.py:74` los devuelve como dos bloques ya nombrados
   (`SAME_RUN` / `ACK_HOLDS`) — falta que el README y el pitch usen esa misma distinción en vez de
   decir "10 checks" en bloque.

**Hecho cuando.** `pytest` sigue verde y existe un test que falla si un bug inyectado en `extract.py`
pasa inadvertido por los dos canales. Si se va por el camino 2: el README describe los dos bloques por
separado y el ceiling 23 deja de ser la única mención del problema.

---

## 4.2. Funcionalidad faltante para el dominio que dice atacar

**Síntoma.** Tres huecos funcionales en un producto de on-call, los tres ya documentados como ceilings.

**Evidencia.**
- `README.md:893` (ceiling 7) — *"Re-escalation when an ETA expires is still not implemented, and a
  callback is not it."* Un callback vive **dentro de un proceso y una escalera**; nada sobrevive al run.
- `README.md:881` (ceiling 4) — *"No cancellation of a call in flight."*
- `README.md:882` (ceiling 5) — el lock se toma por append sobre el ledger; **no es un run lock ni es
  distribuido**. Lo que impide discar dos veces es la idempotency key *si el proveedor la honra*.

**Por qué importa.** "El on-call dijo que llega en 15 minutos" y nadie re-escala cuando pasan 30 es
precisamente el fallo que el producto dice atacar. Es el hueco más difícil de defender ante alguien
del dominio.

**Referencia.**
- Cancelación documentada como sección propia: `zapier-calle` — README "Side effects and cancellation",
  `~/calle-competitor-scan/monorepo/plugins/zapier-calle/README.md:738`.
- Un intento por caso con **reserva atómica antes de discar**, para que un reintento no haga sonar el
  teléfono dos veces: `~/calle-competitor-scan/monorepo/apps/python/ringfence/ringfence/webhook.py:142-160`.
- Tests que custodian la invariante "una sola llamada":
  `~/calle-competitor-scan/monorepo/apps/python/holdfor-board/tests/test_one_call_at_a_time.py` y
  `.../tests/test_idempotency.py`.
- Ambigüedad de creación que **no se reintenta** y deja la llamada abierta para reconciliar bajo la
  misma key: `~/calle-competitor-scan/monorepo/apps/typescript/multi-party-scheduler/src/calle.ts:86-88`
  (null/408/409/429/5xx ⇒ ambiguo).

**Qué tocar.** El ETA es el único de los tres que vale la pena intentar en el tiempo que queda, y aun
así es trabajo real: haría falta persistir el compromiso con su deadline en el ledger (ya se escribe
el `verdict` con el ETA, `ringdown/audit.py:89`) y un comando nuevo tipo `ringdown sweep` que relea el
ledger, encuentre ETAs vencidos sin cierre y re-escale. Eso reabre la decisión de si Ringdown es un
proceso de una corrida o un daemon — es cambio de arquitectura, no un parche.

**Hecho cuando.** No intentarlo es una respuesta válida. Si se deja como está, la acción correcta es
que el ceiling 7 sea **más visible** (hoy está en la posición 7 de 23): subirlo o mencionarlo en la
sección donde se explica el callback, para que nadie lo lea como implementado.

---

## 4.3. `report.py`: 216 líneas, 1 test

**Síntoma.** Toda la capa de render de terminal está prácticamente sin cobertura, y dos suites se
auto-skipean si falta el entorno.

**Evidencia.**
- `ringdown/report.py` — 216 líneas.
- `tests/test_report.py` — 16 líneas, **1 test** (`test_the_ladder_shows_each_person_their_own_clock`),
  que solo ejercita `ladder_lines`.
- `tests/test_site_port.py` — skipea sin `node`; es la paridad Python↔JS del verificador de ledger
  (`docs/ledger.js`). Si el CI no tiene node, esa paridad **no corre nunca**.
- `tests/test_site_audio.py` — skipea sin `docs/`.

**Por qué importa.** 364 tests es un número fuerte, pero está mal repartido y se nota al mirar el
desglose. Es la crítica más fácil de hacer y la más barata de tapar.

**Referencia.** Ningún competidor tiene un agujero así en una capa de 200+ líneas. La disciplina de
reparto más clara del lote está en
`~/calle-competitor-scan/monorepo/apps/python/redline/tests/` (23 archivos, 653 casos, con archivos
dedicados a custodiar que no se toque la red: `test_no_network.py`, `test_no_real_calls.py`).

**Qué tocar.**
- Tests para las funciones de `ringdown/report.py` que hoy no se tocan. No hace falta cobertura total:
  alcanza con que cada función pública tenga al menos un caso.
- En el CI, instalar `node` en el job para que `test_site_port.py` **corra** en vez de skipearse
  (`.github/workflows/ci.yml`), o convertir el skip en fallo cuando corre en CI.

**Hecho cuando.** `tests/test_report.py` cubre cada función pública de `report.py`, y el log de CI
muestra `test_site_port.py` ejecutado, no skipeado.

---

## 4.4. No hay interfaz de producto, solo un sitio de replay

**Síntoma.** El sitio de `docs/` es técnicamente sólido pero **no llama a ninguna API viva**: es un
replay de datos versionados.

**Evidencia.**
- `docs/app.js:156` — `fetch` a `./audio/manifest.json`.
- `docs/ledger.js:2` y `docs/app.js:468` — `fetch` a `./ledger.example.jsonl`.
- No hay ningún otro `fetch` en el sitio. `docs/index.html` son 752 líneas con 4 vistas
  (Overview / The run / The ledger / Receiver).

**Por qué importa.** Seis de los quince competidores tienen un producto que un jurado puede operar:
veyra, sundials, arc-platform, fieldclose, asheard y muster-phone-to-report.

**Referencia — el mejor patrón para copiar barato.**
`asheard` tiene **tres páginas que funcionan sin credenciales**, contra fixtures del propio paquete:
`~/calle-competitor-scan/monorepo/apps/web/asheard/src/app/read/page.tsx:7` y
`.../src/app/briefing/page.tsx:19`. Es exactamente la mitad del camino: no es una consola en vivo,
pero es tocable sin setup.

Comparables en austeridad, por si sirve el enfoque sin frameworks:
- `~/calle-competitor-scan/monorepo/apps/python/muster/muster/api.py:1-16` — frontend servido con
  `http.server` de stdlib, 6 vistas, y el API **nunca** coloca una llamada real (`api.py:4-6`).
- `~/calle-competitor-scan/monorepo/apps/python/ringfence/ringfence/demo_server.py:388` — HTML de dos
  lados servido con stdlib.

**Qué tocar.** Lo alcanzable no es una consola en vivo: es que el sitio actual deje **cargar un
incidente propio** y corra la escalera contra el servidor falso que ya existe
(`fake/calle_server.py`, 397 líneas) para ver el ledger generarse. Eso reusa todo lo que ya está y no
toca el producto.

**Hecho cuando.** Alguien sin cuenta de CALL-E puede, desde el sitio, disparar un run contra el fake y
ver la cadena verificarse en el browser.

---

## 4.5. `calle-receiver` rompe el relato y está online

**Síntoma.** El repo dice "cero dependencias externas"; el repo tiene 7. Y el componente que las trae
es el único expuesto a internet, con el menor rigor.

**Evidencia.**
- `apps/python/calle-receiver/pyproject.toml:6-14` — 7 dependencias de runtime: `fastapi`,
  `uvicorn[standard]`, `twilio`, `pydantic-settings`, `sqlmodel`, `python-multipart`, `requests`.
- 539 líneas de fuente, 28 tests (contra 3.840 / 364 del paquete `ringdown`).
- `render.yaml:11` — `DASHBOARD_PASSWORD` como único control.
- `docs/index.html:737` — expone `/demo` públicamente en `calle-receiver.onrender.com`.
- `.github/workflows/ci.yml` — corre en la misma matriz que `ringdown`.

**Por qué importa.** "Cero dependencias" es una de las afirmaciones más citadas del pitch. Es cierta
para el paquete y falsa para el repo; que lo note un tercero es peor que declararlo.

**Referencia.** `fieldclose` maneja bien la separación entre lo que es demo y lo que es producto: el
demo público es **fake-only por default** y hay un script que lo custodia como gate del build —
`~/calle-competitor-scan/monorepo/apps/web/fieldclose/scripts/verify-public-demo-environment.mjs`,
cableado en `package.json:16`. Y el kill switch vive en la base y **falla cerrado**:
`.../src/application/live-call-gate.ts:87` (`globalKillSwitchPaused: killSwitch?.paused ?? true`).

**Qué tocar.** No hace falta refactorizar: alcanza con **acotar el relato**. En el README, decir
explícitamente que las cero dependencias son del paquete `ringdown` y que `calle-receiver` es infra de
demo con su propio perfil. Si sobra tiempo, poner auth en `/demo`.

**Hecho cuando.** El README no permite leer "cero dependencias" como una propiedad del repo entero.

---

## 4.6. CI mínimo

**Síntoma.** El CI corre tests y nada más.

**Evidencia.** `.github/workflows/ci.yml` completo: matriz de dos paquetes, una guarda que verifica
que no aparezcan paquetes nuevos sin declarar, `uv sync` y `uv run pytest`. **Sin lint, sin
type-check, sin escaneo de dependencias.**

**Por qué importa.** Es la señal de rigor más barata que existe y la única que un evaluador puede
comprobar sin leer código.

**Referencia.**
- `~/calle-competitor-scan/monorepo/apps/web/fieldclose/package.json:16` — `pnpm validate` encadena
  typecheck + lint + test + db:check + integration + build + e2e.
- `~/calle-competitor-scan/monorepo/apps/typescript/muster-phone-to-report` — `pnpm verify:foundation`
  encadena 12 gates; además el workspace endurece la instalación con `minimumReleaseAge: 1440`,
  `trustPolicy: no-downgrade` y `blockExoticSubdeps: true` en `pnpm-workspace.yaml`.
- `~/calle-competitor-scan/monorepo/apps/typescript/sundials/package.json:12-13` — `npm test` incluye
  el build, o sea el type-check entra como gate.
- `~/calle-competitor-scan/monorepo/apps/python/redline/pyproject.toml:73-76` — marker `network`
  deseleccionado por defecto, para que los tests no puedan tocar la red por accidente.

**Qué tocar.** Agregar a `.github/workflows/ci.yml`, como pasos del job existente:
`uv run ruff check`, `uv run mypy` (o `ty`), y `uv run pip-audit` — este último casi decorativo con
cero dependencias, pero cubre a `calle-receiver`, que sí las tiene. Instalar `node` en el job para que
`test_site_port.py` deje de skipearse (ver 4.3).

**Hecho cuando.** El workflow corre lint, type-check y tests, y falla si alguno falla.

---

## 4.7. Un solo commit y todo bajo `[Unreleased]`

**Síntoma.** No hay historial que evaluar, y el CHANGELOG — que es bueno — no marca ninguna versión.

**Evidencia.**
- Historial git: **1 commit** (`ea795ad`, 2026-09-13, squash).
- `CHANGELOG.md` — 200 líneas, formato Keep a Changelog + SemVer, con entradas escritas contra
  evidencia de llamadas reales fechadas (`CHANGELOG.md:12-22`: una llamada del 2026-09-13 respondida
  *"Hi. Yes. I am."* que terminó en `owner_not_confirmed`; `:24-33`: cuatro de seis llamadas del
  2026-08-20 que el proveedor cerró en el mismo segundo). **Todo bajo `[Unreleased]`.**
- `apps/python/ringdown/pyproject.toml:3` — `version = "0.1.0"`.

**Por qué importa.** El contenido del CHANGELOG es de lo mejor del repo — son hallazgos de llamadas
reales, no changelog de relleno — y queda deslucido por no estar versionado.

**Qué tocar.** Cortar `[0.1.0]` con la fecha de hoy en `CHANGELOG.md` y dejar `[Unreleased]` vacío
arriba. Opcional: un tag `v0.1.0`. El historial squasheado ya no tiene arreglo y no vale la pena
reescribirlo.

**Hecho cuando.** `CHANGELOG.md` tiene al menos una versión fechada y `[Unreleased]` queda vacío.

---

## 4.8. El extractor es regex sobre listas literales de frases

**Síntoma.** La decisión depende de tablas de frases en dos idiomas.

**Evidencia.** `ringdown/extract.py` (351 líneas), con listas literales:
`VOICEMAIL` (`:12`), `WRONG_PERSON` (`:26`), `DECLINE` (`:37`), `ACKNOWLEDGE` (`:54`), `HEDGES` (`:75`).
Declarado en `README.md:864` (ceiling 1, *"Grounding compares text, not meaning"*) y `README.md:904`
(ceiling 10, *"The extractor reads English and Spanish, and nothing else"*).

**Por qué importa.** Es la misma clase de fragilidad que se les marcó a los competidores, así que no
es una desventaja *relativa* — pero sí un límite real.

**Referencia — la misma debilidad en el lote, para calibrar.**
- `~/calle-competitor-scan/monorepo/apps/typescript/multi-party-scheduler/src/read.ts:25-104` — regex
  de inglés hardcodeado, y `DECLINE_PATTERNS` incluye `/\bno\b/i` (`read.ts:68`), que gana en cualquier
  posición: un *"no, ningún problema"* se lee como rechazo.
- `~/calle-competitor-scan/monorepo/apps/python/ringfence/ringfence/resolve.py:39-63` — clasifica por
  substrings de mensajes de error del proveedor.
- `~/calle-competitor-scan/monorepo/apps/python/reality-resolver/evidence/rules.py:8-15` — declara
  *"Nada de esto es comprensión de lenguaje natural real"* y **acepta el riesgo residual por escrito**
  (`rules.py:54-58`) en vez de intentar resolverlo. Es el modelo de honestidad a copiar.

**Ventaja propia a no perder de vista.** El soporte de español no lo tiene **ningún** competidor del
lote. Es un diferencial real aunque el mecanismo sea el mismo.

**Qué tocar.** Nada, salvo que sobre tiempo. Es un ceiling asumido y correctamente documentado.

**Hecho cuando.** No aplica — se deja como está deliberadamente.

---

## 4.9. Dominio angosto para un jurado

**No es una tarea de código.** on-call / SRE es un nicho que un jurado no técnico no vive.

**Para calibrar el pitch, cómo lo resuelven los que tienen mejor gancho:**
- `~/calle-competitor-scan/monorepo/apps/python/muster/README.md:16-33` — abre con dos casos reales
  citados: *US v. Suchowolski*, 838 F.3d 530 (5th Cir. 2016), y el caso Sogen Kato (Adachi, Tokio).
- `~/calle-competitor-scan/monorepo/apps/python/reality-resolver/README.md:547-593` — 8 zonas grises
  legales nombradas con jurisprudencia.
- `~/calle-competitor-scan/monorepo/apps/typescript/arc-platform/README.md:214` — la limitación
  contada como historia, con el número medido (la cola de CALL-E en 11m48s).

**Activo propio que ya existe y se puede usar más.** El segundo escenario de dominio
(`examples/sla-breach.example.json` + `sla-breach.script.txt`) demuestra que la máquina no es solo
on-call. Hoy es un ejemplo; podría ser el gancho del pitch.

---

## Resumen de archivos a tocar

| Brecha | Archivos |
|---|---|
| 0 | ninguno — mergear PR #512 |
| 4.1 | `ringdown/verify.py`, `apps/python/ringdown/README.md` (y `ringdown/attest.py` si se va por el camino caro) |
| 4.2 | `ringdown/audit.py`, `ringdown/__main__.py` — solo si se decide encararlo |
| 4.3 | `tests/test_report.py`, `.github/workflows/ci.yml` |
| 4.4 | `docs/app.js`, `docs/index.html`, `fake/calle_server.py` |
| 4.5 | `apps/python/ringdown/README.md`, `render.yaml` |
| 4.6 | `.github/workflows/ci.yml` |
| 4.7 | `CHANGELOG.md`, `apps/python/ringdown/pyproject.toml` |
| 4.8 | ninguno (ceiling asumido) |
| 4.9 | ninguno (pitch, no código) |

---

## Origen de los datos

- Informe completo: `comparativa_calle_actualizada.md` (mismo directorio).
- Hallazgos crudos de Ringdown: `~/calle-competitor-scan/findings-ringdown.md` (465 líneas).
- Hallazgos de los competidores: `~/calle-competitor-scan/findings-g1.md` … `findings-g4.md`.
- Métricas de las 198 carpetas escaneadas: `~/calle-competitor-scan/scan.json`.
- Clon de solo lectura del monorepo comunitario: `~/calle-competitor-scan/monorepo/`.

Todo el escaneo fue estático: no se ejecutó código de terceros ni se hicieron requests a APIs en vivo.
