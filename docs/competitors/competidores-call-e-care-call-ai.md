# Competidores — CALL-E (Honorable Mention: care-call-ai)

| | |
|---|---|
| Fecha | 2026-10-19 |
| Modo | hackathon |
| Evaluados | 1 (+ proyecto propio) · clonados 1 (borrado) · **nada se ejecuto** |
| Ventana | submissions 2026-07-23 → 2026-09-14 (`/details/dates`) |

## En criollo

- **Que se miro:** `NeoSPU/care-call-ai`, ganador de Honorable Mention, leido solo por codigo, sin correr nada.
- **Quien es la amenaza:** media-alta. Hace lo que a Ringdown le falta (pantalla para que un humano apruebe antes de llamar) y lo hace con reglas reales en el codigo, no solo descritas.
- **Como estamos:** Ringdown le gana en pruebas automaticas, historial de trabajo y verificacion de lo que se dijo en la llamada; pierde en producto visible (no hay panel ni pantalla de aprobacion).
- **Que conviene hacer:** copiar la idea de la aprobacion del lote y de a quien no se llama (S-01, S-02), sin sumar dependencias.

**Pesos del jurado** (`docs/judging.tsv`: los cuatro criterios de CALL-E, "equally weighted"):

| Criterio | Peso | Secciones que lo responden |
|---|---:|---|
| Real World Impact | 25 | 1, 6 |
| Quality of the Idea | 25 | 7, 4 |
| Technical Implementation | 25 | 4, 5, 6, 10 |
| Product Experience & Demo | 25 | 1, 8 |

**Lo que no se pudo ver** — el margen de error de todo lo que sigue:

- El dashboard en vivo pide usuario y contrasena (`/dashboard` redirige a `/login`) [4]: no se vio ninguna pantalla real; la superficie de producto se juzga por codigo.
- El video de YouTube y las 14 capturas de Devpost no se miraron; solo se confirmo que el embed existe [11].
- Los tests no se corrieron: se contaron, y que pasen solo lo dice el CI (verde) [8].
- El repo publico es una copia "sanitizada" del privado (README): el historial real de trabajo no es visible [3].

---

## Tabla comparativa

Escala: `fuerte` · `cumple` · `flojo` · `ausente` (se miro y no esta) · `sin evidencia` (no se pudo ver).

| Proyecto | Nicho | Real World Impact | Quality of the Idea | Technical Implementation | Product Experience & Demo | Nota | Amenaza |
|---|---|---|---|---|---|---:|---|
| `NeoSPU/care-call-ai` | Llamadas de organizaciones de caridad a personas con enfermedad o discapacidad | fuerte | cumple | fuerte | fuerte | 8/10 | media-alta |
| `gmassello/ringdown` (propio) | Escalada telefonica de incidentes con verificacion de lo dicho | cumple | fuerte | fuerte | flojo | 8/10 | — |

**Amenaza** es contra *tu* entrada: care-call-ai compite en el mismo evento pero en otro nicho; lo que amenaza es la superficie de producto y la aprobacion humana, que el jurado ve y Ringdown no muestra.

---

## `NeoSPU/care-call-ai` — Care Call AI

<!-- ficha -->

**Que hace:** una organizacion de caridad prepara una ronda de llamadas a beneficiarios, un coordinador la aprueba, se llama con CALL-E y las respuestas se vuelven pedidos imprimibles.

| | |
|---|---|
| Repo | https://github.com/NeoSPU/care-call-ai · creado 2026-08-13 · Python (+ Next.js/TypeScript) · licencia sin reconocer (`NOASSERTION`) [1] |
| Demo | https://care.alexraixon.com · `curl` 200 en 1.8s la portada; `/dashboard` 307 a login [4] |
| Devpost | `care-call-ai` · video si (YouTube) · Honorable Mention [11] |
| Equipo | 1 contribuyente · 39/39 commits de una sola cuenta [3] |
| Historial | primer commit 2026-08-11 · 39 commits · previos al evento: no (0 commits antes del 2026-07-23) [2] |

| Criterio | Veredicto | Evidencia |
|---|---|---|
| Real World Impact 25% | fuerte | Nicho concreto (caridades, beneficiarios, coordinador), 19 menciones de approval/preflight/dashboard/operator en el README [9] |
| Quality of the Idea 25% | cumple | El humano conserva la decision: aprobacion obligatoria antes de marcar. La idea es una app de flujo, no una pieza reutilizable; sin licencia reconocida [1] |
| Technical Implementation 25% | fuerte | Backend con `dependencies = []` (solo biblioteca estandar) [7]; 166 `def test_` y 683 asserts en Python + 126 `it(`/`test(` en TypeScript [7]; CI verde en 10 de 10 corridas [8] |
| Product Experience & Demo 25% | fuerte | Dashboard, panel de operador, tarjeta de destinatario, orden imprimible y pantalla de aprobacion: 2601 lineas en 4 componentes, y el front llama al backend por `carecall-api.ts` [12] |
| Calidad de codigo | cumple | 30013 lineas sin lockfile ni imagenes; el primer commit trae 120 archivos y 20757 lineas, o sea un import [3] |
| Seguridad | cumple | `make secrets-check` propio; sin `.env` en el historial; `.env.example` con datos de demo documentados en README:175-179 [13] |

**Lo mas fuerte:** la aprobacion esta forzada en el codigo, no solo descrita (ver abajo), mas 166 + 126 pruebas.
**Donde se cae:** un solo autor, un solo commit de import (20757 lineas), licencia sin reconocer, y "Kubernetes" figura en Devpost pero hay 0 archivos de Kubernetes en el repo [10].
**Sin evidencia:** pantallas reales, video, y si el sistema llamo alguna vez a una persona de verdad (el repo publico tiene solo registros ficticios, `seed_recipients.json`).

### Lo que pediste mirar

| Pieza | Que hay realmente | Evidencia |
|---|---|---|
| Aprobacion del lote (Approval Gate) | **Enforced en el servidor.** Se genera un plan con las claves exactas de los destinatarios listos; la aprobacion debe coincidir con ese conjunto exacto, no estar vencida, llevar nombre del aprobador, 4 confirmaciones (`active_consent`, `care_route_match`, `exact_keyset`, `real_side_effects`) y la frase `EXECUTE LIVE CALLS`. La ejecucion en vivo la vuelve a chequear y exige `CARECALL_LIVE_CALLS_ENABLED=true`, lote maximo de 1 por defecto y readiness de CALL-E [5] | `approval.py`, `approval_policy.py`, `server.py:391-420` |
| "No-call preflight" | Es un plan en seco: arma el prompt y la clave de idempotencia (hash sha256 de fecha, destinatario, ruta, telefono, proposito) sin marcar nada. Hay endpoint de dry-run que aplica los mismos bloqueos [5] | `call_planning.py`, `server.py:362-380` |
| A quien NO se llama | **Enforced**: `do_not_call`, consentimiento faltante o revocado, telefono invalido, ruta cuidador/staff sin telefono bloquean la fila [6]. Critico o ruta "staff" (solo-operador) se desvia a revision manual y queda fuera de la ronda automatica [6]. Repeticion el mismo dia: tope por destinatario (2 por defecto) y confirmacion extra [5] | `validation.py`, `server.py:890-905`, `daily_limits.py` |
| "Llamado hace muy poco" | **Solo mismo dia** (`same_day_call_count`); no hay ventana de enfriamiento de varios dias en el codigo leido [6] | `repository.py:860-880` |
| Debilidad del gate | `approved_at` se guarda como el texto fijo `"api-request"`, no una fecha; el aprobador sale del campo `operator` del pedido [5] | `server.py:~340` |
| Superficie de producto | Real en codigo: rutas `dashboard`, `operator`, `preflight`, `recipients/[id]`, `orders/print`, `urgent-callback`, con tests de componente (vitest) [12]. Que se vea bien en vivo: sin evidencia (login) [4] | arbol del repo |
| Tests | 166 `def test_` y 683 asserts con `unittest` (stdlib) + 126 `it(`/`test(` de vitest [7]. Ringdown: 606 tests (dato tuyo) contra 376 `def test_` en `apps/python/ringdown/tests` [14] | ver apendice |

---

## Donde queda tu proyecto

| Criterio | `gmassello/ringdown` | `NeoSPU/care-call-ai` |
|---|---|---|
| Aprobacion humana antes de llamar | **ausente** (no hay gate; el comando de escalada llama solo) [14] | fuerte: gate exacto, 4 confirmaciones, frase, tope de lote [5] |
| Reglas de a quien no llamar | flojo: ladder por incidente, sin lista de bloqueados/consentimiento [14] | cumple: consentimiento, do_not_call, critico, staff, tope diario [6] |
| Verificacion de lo dicho | fuerte: verificacion por MCP, citas, ledger con hash en cadena [14] | flojo: sin segundo canal; hashea claves, no verifica resultados [7] |
| Tests / asserts | 606 tests (dato tuyo), cero dependencias de runtime [14] | 166 + 126 tests, backend sin dependencias [7] |
| Commits | 102 [14] | 39, de una sola cuenta, con import inicial [3] |
| Interfaz | flojo: terminal, GIF y sitio estatico, sin panel [14] | fuerte en codigo, sin evidencia en vivo [12] |
| Endpoint desplegado | recibidor en Render (notes/plan-twilio-calle.md) [14] | portada 200 en 1.8s, panel tras login [4] |

### Sugerencias

| # | Sugerencia | Por que importa | Criterio (peso) | Origen | Evidencia | Esfuerzo | Mueve nota |
|---|---|---|---|---|---|---|---|
| S-01 | Agregar un paso de aprobacion explicito del lote en Ringdown: plan en seco con claves exactas, nombre del aprobador, fecha real y registro en el ledger | El jurado ve que un humano decide antes de que suene un telefono; hoy Ringdown no lo muestra | Product Experience & Demo (25%) | brecha | care-call-ai fuerza el gate en servidor [5]; Ringdown no tiene [14] | medio | si |
| S-02 | Lista de "no llamar" con consentimiento, bloqueados y tope diario, bloqueando antes del primer intento | Es la regla de seguridad que mas se cita en el nicho y hoy solo se explica en prosa | Technical Implementation (25%) | brecha | `validation.py` y `daily_limits.py` bloquean en codigo [6] | medio | si |
| S-03 | Una pagina estatica con la salida de la demo (ya hay sitio) que muestre el paso de aprobacion y los diez escenarios como pantalla | Cubre la superficie visible sin sumar una dependencia de runtime | Product Experience & Demo (25%) | brecha | 4 componentes de UI con 2601 lineas en care-call-ai [12] | medio | si |
| S-04 | Declarar en el README la licencia y el origen del trabajo (repo, fechas) en el pitch | care-call-ai figura sin licencia reconocida y como copia de un repo privado; la transparencia suma | Quality of the Idea (25%) | brecha | `NOASSERTION` [1], copia sanitizada [3] | bajo | si |
| S-05 | Nombrar en el pitch la ventaja de verificar por un segundo canal, comparada con un panel que confia en el resultado de CALL-E | Es lo que ningun rival del set mide | Quality of the Idea (25%) | hueco | care-call-ai no re-verifica la llamada [7] | bajo | si |
| S-06 | Estrellas, topics y el tamano del README | Ningun criterio del jurado los pondera | — | — | 0 estrellas en el rival, ganador igual [1] | bajo | **cosmetico** |

> Control de sesgo: Ringdown salio con `flojo` en Producto, `ausente` en aprobacion y `flojo` en reglas de bloqueo; las tres celdas mas comodas (tests, verificacion, historial) se releyeron contra los numeros de arriba. Las celdas de Ringdown salen de `CLAUDE.md`, `ls` y los conteos del apendice, no de una corrida nueva de sus tests. Solo se evaluo un rival: la columna `hueco` (S-05) vale solo contra este.

---

## Apendice — como se midio

<!-- ficha -->

| Ref | Comando |
|---|---|
| [1] | `jq '{fork,stars:.stargazers_count,created:.created_at,pushed:.pushed_at,lang:.language,license:.license.spdx_id,homepage,archived}' care-call-ai.json` |
| [2] | `gh api "repos/NeoSPU/care-call-ai/commits?until=2026-07-23T00:00:00Z&per_page=1" --jq 'length'` (devuelve 0) |
| [3] | `git clone --depth 50 --no-tags` + `git log --reverse --format='%ad %s' --date=short \| head -3`, `git rev-list --count HEAD` (39), `git shortlog -sn HEAD` (39 Alex R), `git show --stat <primero> \| tail -2` (120 archivos, 20757 +) |
| [4] | `curl -s -o /dev/null -w '%{http_code} %{time_total}s' https://care.alexraixon.com` (200 1.8s) y `/dashboard` (307, destino `/login?next=%2Fdashboard`) |
| [5] | Lectura de `backend/app/approval.py`, `approval_policy.py`, `server.py` (approve/dry-run/execute_live) y `daily_limits.py` |
| [6] | Lectura de `backend/app/validation.py`, `repository.py` (`_default_safety_category`, `call_plan_previews_with_same_day_history`) y `server.py` (categorizacion de previews) |
| [7] | `grep -rcE "^\s*def test_" backend/tests` (166); `grep -rhcE assert backend/tests` (683); `grep -rhoE "^\s*(it\|test)\(" frontend/src \| wc -l` (126); `grep -A3 dependencies backend/pyproject.toml` (`dependencies = []`) |
| [8] | `jq -r '.[] \| "\(.conclusion // .status)\t\(.name)\t\(.createdAt)"' care-call-ai.runs` (10 success, 2026-09-13 a 2026-09-14) |
| [9] | `grep -ciE "approval\|preflight\|dashboard\|operator" care-call-ai.readme` (19); `head -40` del README |
| [10] | `git ls-files \| grep -ciE "k8s\|kube\|helm"` (0) contra el tag "kubernetes" en la ficha de Devpost |
| [11] | `curl -s -A "Mozilla/5.0" https://devpost.com/software/care-call-ai` (200; embed `youtube.com/embed/Hc2bWjTnKFQ`; "Honorable Mention") |
| [12] | `wc -l` de `PreflightApprovalGate.tsx`, `PrintableOrderSheet.tsx`, `OperatorPanelClient.tsx`, `RecipientDetailClient.tsx` (2601); `grep -rlE "fetch\(" frontend/src` (incluye `lib/carecall-api.ts`) |
| [13] | `git log --all --diff-filter=A --name-only --format= \| grep -iE '\.env$\|\.pem$'` (vacio); `make secrets-check` existe pero no se corrio |
| [14] | Proyecto propio: `CLAUDE.md`, `ls`, `grep -rcE "^\s*def test_" apps/python/ringdown/tests` (376 definiciones; los 606 son tu dato), `git rev-list --count HEAD` (102) |
