# Revisión de arquitectura — ringdown

**Alcance:** estado actual de `HEAD` (no hay diff de código; los únicos cambios sin commitear son READMEs).
**Referencia de diseño:** `docs/plan.md` y `docs/ringdown-brief.md` (ADRs de facto; no existe `docs/adr/`).
**Suite al momento de la revisión:** 157 tests en verde, 0.49s, sin red ni credenciales.

**Veredicto original: BLOQUEAR** — el camino de verificación (el diferenciador del producto) no puede funcionar contra el proveedor real, y la evidencia de las llamadas colocadas se escribe después de los efectos.

**Estado actual: los 10 hallazgos están resueltos.** Suite en 176 tests (157 + 7 + 5 + 7), demo corriendo los siete escenarios, `verify` del ledger de ejemplo en exit 0. Cada fix tiene su fitness function y todas se verificaron al revés: revirtiendo el fix de a uno, el test correspondiente falla.

Dos decisiones tomadas al implementar, distintas de lo que proponía el reporte:

- El caso "no se pudo verificar" usa un **exit 45 nuevo**, no reusa el 25. El 25 significa "hay una llamada posiblemente viva, reconciliala" y su consejo impreso es el equivocado para un ack sin corroborar.
- El hallazgo 4 se resolvió con campo explícito **más** fallback de compatibilidad, para que ningún ledger ya escrito empiece a reportar adulteración.

---

## Severidad ALTA — resueltos

### 1. El segundo canal es inalcanzable en producción: `McpClient` se deriva de `--base-url` ✅

**Síntoma:** `ringdown/__main__.py:159` construye `McpClient(f"{base_url}/mcp", api_key, allowed_hosts=allowed)`. El default de `--base-url` es `https://api.heycall-e.com` (`__main__.py:45`) y `TRUSTED_HOSTS = frozenset({"api.heycall-e.com"})` (`ringdown/calle.py:11`). Pero el brief documenta el MCP en **otro host**: `https://seleven-mcp-sg.airudder.com/mcp/openagent_oauth` (`docs/ringdown-brief.md:301`). No existe flag `--mcp-url`: el parser de `run` solo acepta `--incident --rotation --ledger --confirm --base-url --allow-host` (`__main__.py:71-76`).

**Causa estructural:** la topología del fake se filtró al diseño del cliente. `FakeCalleServer` sirve REST y MCP sobre un mismo origen (`fake/calle_server.py:332-338`), así que la relación "MCP = base_url + /mcp" quedó codificada como estructura en vez de como configuración. Los 157 tests corren contra esa topología y por construcción no pueden detectar la divergencia.

**Costo:** el `verify` de dos canales — la tesis del proyecto, el exit 40, lo que se muestra en el video — no corre en vivo. Contra el proveedor real cada ack termina en exit 40 (`get_call_run` contra `api.heycall-e.com/mcp` da 404 → `CalleError` → `verify.py:35-36` devuelve el check en `False`), o se apunta `--base-url` al host MCP y se rompe REST. La Etapa 10 del plan ("una llamada real") es donde esto explota.

**Arreglo aplicado:** `calle.py:11` suma `seleven-mcp-sg.airudder.com` a `TRUSTED_HOSTS`. `__main__.py` define `DEFAULT_MCP_URL` y el flag `--mcp-url`, validado por el mismo `assert_trusted_base_url` que ya cubría `--base-url`, y se lo pasa a `McpClient` en lugar de `f"{base_url}/mcp"`. `demo/run_local.py` y el helper `_run` de los tests pasan el flag explícito apuntando al fake.

**Fitness function:** `test_the_second_channel_is_read_from_the_url_it_was_given` — corre con `--mcp-url` apuntando a un path que el fake no sirve y afirma exit 40 con el primer check en `[ ]`. Descartada la versión con dos servidores: compartiendo estado, el server REST también responde `/mcp` y el test pasaría igual con el bug puesto. Este falla.

**Riesgo abierto:** el endpoint del brief es OAuth y el cliente manda `Authorization: Bearer $CALLE_API_KEY`. Sin credenciales no se puede verificar si lo acepta. Si falla, falla por auth y no por topología, y se corrige con `--mcp-url`.

---

### 2. "Canal caído" y "canal contradice" son el mismo resultado ✅

**Síntoma:** `ringdown/verify.py:34-36` y `verify.py:78-79`: ante cualquier `CalleError` (timeout, DNS, 503, transporte) devuelven `[(False, ...)]`, idéntico a un check que reprobó por contradicción. Eso baja a `all_ok(checks) is False` (`__main__.py:162`) → exit 40 → se imprime `MISMATCH_ADVICE`: *"Treat this incident as unowned."* (`report.py:21-24`). `McpClient.get_call_run` no tiene reintento: un solo request, timeout 15s (`calle.py:229-244`).

**Causa estructural:** `Check = tuple[bool, str]` es de dos valores. El resto del sistema es de tres o cuatro (`Verdict` incluye `unknown`, `CalleError.ambiguous` existe justamente para eso), pero la capa de verificación colapsa "no sé" en "no". El espacio de exit codes tampoco tiene estado para "no se pudo verificar".

**Costo:** un blip de red de 15 segundos en el canal MCP convierte un ack real y comprometido en "este incidente no tiene dueño", y el operador despierta a la siguiente persona. Es exactamente lo que el proyecto existe para evitar, y lo que le critica a la receta Zapier en `docs/plan.md:91-95`.

**Arreglo aplicado:** el corte lo da `CalleError.ambiguous`, que ya existía y distingue exactamente lo que hacía falta. Transporte, timeout, 408/409/425/429 y 5xx rinden `None`; 404 `no_call_run`, 401 y 400 siguen rindiendo `False` — el proveedor respondió y contradice, que es el caso de `unseen_on_second_channel`.

- `verify.py` — `Check = tuple[bool | None, str]`, `passed()` cuenta `ok is True` (el `sum(ok for ok, _ in checks)` viejo reventaba con `None`), `unresolved()` y `contradicted()` nuevos, `MARKS` rinde `[?]`, `tally()` reporta los indeterminados.
- `calle.py` — `get_call_run` reintenta **una vez** ante `error.retriable` con `MCP_RETRY_DELAY` de módulo. El reintento vive solo ahí, nunca en `_send`: `create_call` coloca llamadas y no se reintenta a ciegas.
- `__main__.py` — `EXIT_UNRESOLVED = 45`. Con algún `False` gana el 40; sin contradicciones y con algún `None`, 45.
- `report.py` — `UNRESOLVED_ADVICE` propio. **No** se reusa `MISMATCH_ADVICE` ("treat this incident as unowned"), que es justo el consejo equivocado cuando nada contradijo el ack.
- `audit.py` — `verification_record` cuenta igual y registra `unresolved`.

**Fitness function:** `test_a_second_channel_that_cannot_be_reached_is_unresolved_not_a_mismatch` — escenario `unreachable_second_channel` (dos faults MCP, porque ahora hay un reintento), afirma exit 45, `[?]` en el render, `1 unresolved` en el tally, ausencia de `MISMATCH_ADVICE` y `unresolved == 1` en el ledger.

---

### 3. El ledger se escribe después de los efectos, en batch al final de la escalera ✅

**Síntoma:** `__main__.py:149` llama a `_record_ladder` **después** de que `run_ladder` retornó, y `_record_ladder` (`__main__.py:104-107`) recién ahí itera todos los attempts. `run_ladder` puede tardar `per_call_timeout_seconds × rungs` (180s × 3 = 9 minutos con la policy default, `incident.py:51`). Durante esos 9 minutos suenan teléfonos y no se escribe nada. El README lo roza sin decirlo: *"Ctrl-C stops the local waiter and nothing else"*.

**Causa estructural:** el registro de auditoría es un *reporte del resultado*, no un *write-ahead log del efecto*. El seam correcto ya existe y está sin usar: `watch(position, rung, placed)` se invoca por attempt con el `Attempt` ya resuelto (`escalate.py:124`), y `place_and_settle` ya imprime la idempotency key antes del POST (`escalate.py:56`) pero no la persiste.

**Costo:** Ctrl-C, SIGTERM, OOM o un crash a mitad de la escalera dejan cero registros de llamadas que **ya sonaron**. Para un producto cuya tesis es "probar el acuse de recibo", el agujero de evidencia tiene el tamaño exacto de la corrida. Peor caso: el POST se envía, el proceso muere antes de la respuesta, y no queda ni la idempotency key — nadie sabe que hay una llamada viva ni con qué key reconciliarla.

**Arreglo aplicado:** `place_and_settle` recibe un callback `announce(attempt_id, key, rung)` y lo invoca apenas calcula la identidad, **antes** de `rest.create_call`; `run_ladder` lo propaga. En `run()`, `announce` escribe el `intent_record` y el `attempt_record` se mudó al callback `watch`, que ya se invocaba por attempt resuelto. `_record_ladder` desapareció: el `verdict_record` se escribe directo al final. `chain_checks` ignora `type == "intent"` al re-derivar, y los checks de link y hash sí lo cubren.

El ledger gana una línea por attempt. Los ledgers viejos siguen verificando — link y hash son agnósticos al tipo.

**Fitness function:** `test_a_crash_mid_ladder_leaves_the_placed_attempt_and_the_pending_key_on_the_ledger` — monkeypatchea `RestClient.create_call` para lanzar `KeyboardInterrupt` en el segundo rung y afirma que el ledger quedó en `["intent", "attempt", "intent"]`, con la key del segundo intent y el `call_id` del primer attempt en su lugar.

---

### 4. `chain_checks` re-deriva el verdict por posición en el archivo ✅

**Síntoma:** `ringdown/audit.py:110-124` acumula `verdicts` de todo registro `type == "attempt"` que aparezca antes de un `type == "verdict"`, sin mirar a qué incidente pertenece. Los registros `attempt` ni siquiera llevan campo de incidente (`audit.py:36-48`); el id vive embebido dentro de `attempt_id`. Mientras tanto, `append_record` (`audit.py:75-81`) soporta escritores concurrentes correctamente vía `flock`, y el README declara que dos runners no están impedidos (ceiling 5).

**Causa estructural:** el formato del ledger asume corridas serializadas y de un solo incidente, pero la capa de escritura habilita explícitamente lo contrario. La correlación se toma de la adyacencia posicional en vez del identificador que ya está en los datos.

**Costo:** el uso operacional obvio — un ledger por equipo, o dos incidentes simultáneos — hace que `verify --ledger` reporte adulteración que no ocurrió. Una herramienta de auditoría con falsos positivos se deja de mirar en dos semanas, y ahí se pierde también la detección verdadera.

**Arreglo aplicado:** `attempt_record(attempt, incident_id)` agrega `"incident"`, y `chain_checks` acumula los verdicts en un `dict` por incidente, haciendo `pop` al llegar al `verdict_record` de ese incidente. Los checks de relink y de hash siguen siendo posicionales, que es lo correcto.

Compatibilidad hacia atrás: `incident_of` cae en `attempt_id.rsplit("/", 2)[0]` cuando el registro no trae el campo — el formato es `{incident.id}/{scope}/{n}` y el incident id es texto libre que puede contener `/`, por eso `rsplit` con límite. Sin eso, todo ledger ya escrito habría empezado a reportar adulteración.

**Fitness functions:** `test_two_incidents_interleaved_in_one_ledger_each_derive_their_own_verdict` — attempts de dos incidentes intercalados donde la lógica posicional vieja derivaba `declined` para el incidente equivocado. Y `test_an_attempt_written_before_the_incident_field_existed_still_verifies`, que borra el campo del registro y comprueba el fallback.

---

### 5. En exit 25 se reporta el call id equivocado ✅

**Síntoma:** `ringdown/escalate.py:42-43`:

```python
def live_call_id(self) -> str | None:
    return next((a.call_id for a in self.attempts if a.call_id), None)
```

Devuelve el **primer** attempt con call id. Como `run_ladder` corta ante cualquier verdict distinto de `not_acknowledged` (`escalate.py:126-127`), el attempt `unknown` es siempre el **último**. Con rung 1 `not_acknowledged` (llamada completada, call `c1`) y rung 2 `unknown`, `report.unknown_lines` (`report.py:170-172`) imprime *"call c1 may still be live"*. Si el `unknown` vino de ambigüedad en el create, ese attempt no tiene call id y `c1` es pura desinformación.

**Causa estructural:** una property de `LadderResult` adivina cuál es el attempt relevante por escaneo, en vez de que el attempt que decidió el verdict lo cargue. `LadderResult.deciding` ya existe (`escalate.py:33-35`) y es el correcto.

**Costo:** el exit 25 es la hoja de instrucciones del operador a las 3am, y el README la eleva a contrato: *"prints the call id, and tells you to reconcile it rather than run again"*. El operador reconcilia una llamada terminada, concluye que no hay nada vivo, y la llamada fantasma queda sin reconciliar.

**Arreglo aplicado:** `return self.deciding.call_id if self.deciding else None`. Una línea.

**Fitness function:** `test_the_call_that_may_be_live_is_the_one_that_decided_not_the_first_placed` — escalera mixta (rung 1 `no_answer` con llamada creada, rung 2 `queued_forever` → `unknown`) que afirma que `live_call_id` es el del segundo y que `unknown_lines` no menciona el call id del primero. Se sumó `test_the_idempotency_key_is_announced_before_the_request_is_sent`, que fija el orden del `announce` del hallazgo 3.

---

## Severidad MEDIA — resueltos

### 6. El ledger no tiene versión de esquema y su validación depende del módulo de escalación ✅

**Síntoma:** `audit.py:9-11` importa `ladder_verdict` desde `escalate`; `chain_checks` (`audit.py:117`) valida ledgers históricos con la regla de escalación **de hoy**. Ningún registro lleva campo de versión (`audit.py:36-48`, `51-60`, `63-72`), y el ledger de ejemplo confirma el esquema plano (`examples/ledger.example.jsonl:1`).

**Causa estructural:** una regla de negocio pura (`ladder_verdict`, 2 líneas) vive en el módulo orquestador, y el módulo de integridad la importa desde ahí. La cadena de confianza queda acoplada a una política mutable sin marcador de qué versión la produjo.

**Costo:** cuando `ladder_verdict` cambie — el ceiling 6 del README ya contempla agregar re-llamados — todo ledger anterior empieza a reportar adulteración. Efecto colateral menor: `verify --ledger` carga `escalate` → `calle` → `urllib` para leer un archivo.

**Arreglo aplicado:** `SCHEMA = 1` y `VERDICT_RULES = {1: ladder_verdict}` en `audit.py`. El estampado va en `append_record`, no en cada builder, así ningún tipo de registro nuevo puede olvidarse del campo. `chain_checks` re-deriva con la regla del `schema` del propio registro `verdict` (ausente cuenta como 1); un `schema` que este build no conoce rinde `None` —indeterminado, `[?]`— y no `False`, que es la misma distinción que el exit 45 introdujo en `verify.py`. Un ledger escrito por una versión futura no es adulteración.

**No** se movió `ladder_verdict` fuera de `escalate`: `audit.py` también importa `Attempt` y `LadderResult` de ahí, así que mover dos líneas no corta la dependencia a `urllib`. Eso es el hallazgo 10.

**Corrección posterior — la primera versión de este fix no cumplía lo que decía.** `VERDICT_RULES = {1: ladder_verdict}` versionaba la *llamada*, no la *regla*: la clave `1` apuntaba al objeto función vivo, así que editar `ladder_verdict` en `escalate.py` re-derivaba todo ledger histórico con la regla nueva. Demostrado, no deducido: mutando la regla, los dos goldens seguían verificando. La afirmación de que "quien cambie `ladder_verdict` ve fallar el golden" era falsa — los goldens tienen un solo attempt `acknowledged`, que sobrevive a cualquier cambio plausible de la regla.

La regla 1 ahora está congelada **por valor**: `verdict_v1` vive en `audit.py`, es histórica y no se edita; `escalate.ladder_verdict` sigue siendo la regla viva. `SCHEMA = max(VERDICT_RULES)`, así que el número de versión se escribe una sola vez.

**Fitness functions:** una tabla de nueve vectores que fija el comportamiento de `verdict_v1`; `test_the_rule_the_ladder_runs_today_still_agrees_with_the_frozen_one`, que falla en el momento en que alguien cambia la regla viva sin bumpear la versión; y `test_every_schema_this_build_ever_wrote_can_still_be_re_derived`, que exige que `VERDICT_RULES` cubra `1..SCHEMA`. Los goldens `ledger-v0.jsonl` y `ledger-v1.jsonl` siguen, pero fijan la **forma** del record en disco, no la regla — eso quedó claro recién cuando la revisión los mutó. `.gitignore` necesitó `!**/tests/golden/*.jsonl`. Verificado al revés: editando la regla en `escalate`, falla el test de acuerdo; volviendo a versionar por referencia, falla el layering.

---

### 7. La cadena es sin clave y sin anclaje: el truncado del final es indetectable ✅

**Síntoma:** `canonical.py:12-13` usa SHA-256 desnudo; `GENESIS` es una constante pública (`audit.py:15`); `append_record` no hace `fsync` (`audit.py:75-81`). El `tamper()` del demo (`demo/run_local.py:56-67`) solo reescribe el registro `verdict` y relinkea — justamente el caso que el tercer check atrapa.

**Causa estructural:** hash-chain sin clave ni ancla externa prueba consistencia interna, no autenticidad ni completitud. Nada ata el head del archivo a algo fuera del archivo.

**Costo:** cortar las últimas N líneas deja una cadena perfectamente válida — se borra un intento y su verdict sin dejar rastro. Reescribir attempts **y** verdict de forma coherente pasa los tres checks. El README dice *"A flat append-only log has nothing left to complain about at that point"* (`apps/python/ringdown/README.md:180-182`), que promete más de lo que la construcción entrega.

**Arreglo aplicado:** `append_record` estampa `"seq"` monotónico junto al `schema` y el `prev`; `len(lines)` ya estaba calculado bajo el lock, así que no cuesta I/O. `chain_checks` suma un check de contigüidad —el registro N tiene que traer `seq == N`— que se saltea cuando el campo no está, para que los ledgers viejos sigan verificando.

Lo que esto compra, sin sobrevenderlo: el borrado de un registro **del medio** con relink y resellado, que antes pasaba los tres checks, ahora se cae por el hueco en la numeración.

**Corrección posterior:** eso vale contra un borrado accidental, **no contra un adversario**. La revisión lo demostró borrando el record `intent`, sacando `seq` de los demás, relinkeando y resellando: los cuatro checks en verde. Quien puede resellar la cadena puede además borrar el campo, y un record sin `seq` se saltea a propósito para que los ledgers viejos sigan verificando. El README decía *"a deleted record that was relinked and resealed still fails the third"* — la misma sobre-promesa que este hallazgo le criticaba al texto anterior, con otra frase. Corregido en el ceiling 11.

**Lo que sí sería el mecanismo, y queda propuesto y no implementado:** el ancla ya existe pero se imprime y nadie la vuelve a ingresar. `verify --ledger --expect-head <sha> --expect-count <n>` son dos `add_argument` y un check, y cubren truncado de cola, renumerado completo y borrado del medio — la lista entera del ceiling 11. Es agregar superficie de CLI, así que va como propuesta y no colado en una pasada de limpieza.

**Fitness functions:** `test_a_deleted_record_is_caught_even_when_the_chain_is_relinked_and_resealed` (link y hash en verde, contigüidad en rojo) y `test_a_truncated_tail_leaves_a_chain_that_still_verifies`, que fija por escrito el techo en vez de dejarlo para que alguien lo descubra. Verificado al revés: sacando el estampado de `seq`, el primero falla.

**README:** ceiling 11 nuevo, y se bajó la promesa de la sección del ledger — *"A flat append-only log has nothing left to complain about at that point"* pasó a decir qué prueban los cuatro checks y qué no.

---

## Severidad BAJA — resueltos

### 8. `report.py` re-deriva la política de confianza para decidir qué imprime ✅

**Síntoma:** `ringdown/report.py:5` importa `confident` desde `dispositions`, y `report.py:127` re-evalúa `not confident(snapshot, policy)` para ocultar spans — decisión que `classify` ya tomó y dejó registrada en `attempt.reason == "low_confidence"` (`dispositions.py:68-69`).

**Causa estructural:** la capa de presentación re-ejecuta una regla de dominio en vez de leer el resultado que el dominio ya produjo.

**Costo:** hoy solo cosmético. Si la regla de confianza cambia en `classify` y no en `report`, se imprimen spans como evidencia de un veredicto que rechazó esa misma evidencia.

**Arreglo aplicado:** `not confident(snapshot, policy)` → `attempt.reason == "low_confidence"`, e import borrado. La otra mitad de la condición (`snapshot.status != "completed"`) se queda: no es una regla de dominio re-derivada, es leer el estado del snapshot, y el `reason` de una llamada fallida es el failure code, que no se puede enumerar. `policy` quedó sin uso en `_span_lines` y salió de su firma.

**Fitness function:** `tests/test_layering.py` — un helper de 8 líneas con `ast` en vez de import-linter, porque `dependencies = []` es restricción dura del proyecto y el reporte acepta "un grep en CI". Verificado al revés: reponiendo el import, el caso `[report-ringdown.dispositions]` falla.

---

### 9. `place_and_settle(attempt=...)` es la perilla que el diseño prohíbe ✅

**Síntoma:** `escalate.py:46-52` acepta `attempt: int = 1` y lo propaga a `attempt_id` e `idempotency_key` (`escalate.py:53-55`). `run_ladder` nunca pasa otra cosa que el default (`escalate.py:123`); nadie más lo llama.

**Causa estructural:** parámetro especulativo para una capacidad que el diseño declara prohibida. `docs/plan.md:298` y el ceiling 6 del README dicen que re-llamar exige "otra idempotency key y otro registro, nunca un retry silencioso" — y este parámetro entrega exactamente la nueva key sin el nuevo registro.

**Costo:** bajo hoy. La invariante "no re-llamamos" pasa de ser estructural a depender de que nadie use un parámetro público que ya está ahí y hace justo lo prohibido.

**Arreglo aplicado:** parámetro borrado; adentro se usa la constante de módulo `ONLY_ATTEMPT = 1`, que nombra la invariante en vez de dejar un literal suelto. `run_ladder` ya llamaba sin él y los dos tests que usan `place_and_settle` pasan todo por keyword, así que cero call sites tocados. `script.attempt_id` y `script.call_payload` mantienen su tercer argumento: son funciones puras que `preview` también usa. Lo que se cierra es la perilla en la capa que corre la escalera, que es donde vive la invariante.

---

### 10. `calle.py` mezcla transporte y objetos de valor; `Check` está declarado dos veces ✅

**Síntoma:** `calle.py` contiene `Turn`/`CallSnapshot`/`CallRun` (líneas 49-81) junto con `RestClient`/`McpClient`/urllib. Por eso `extract.py:7` y `dispositions.py:6` —lógica de texto pura, sin red— dependen del módulo de transporte. Y `Check = tuple[bool, str]` está definido en `verify.py:12` **y** en `audit.py:13`, con `render_blocks`/`all_ok` viviendo en `verify.py` (verificación de canal) pero sirviendo también a la verificación de cadena (`__main__.py:174`).

**Causa estructural:** el concepto "checklist" no tiene módulo propio, así que quedó en el primero que lo necesitó; y los DTOs del proveedor tampoco, así que quedaron con su cliente.

**Costo:** bajo y acotado: `verify --ledger` carga urllib para leer un archivo, y la lógica de extracción no se puede testear ni reusar sin arrastrar el cliente HTTP.

**Arreglo aplicado:** dos módulos nuevos, cero lógica nueva.

- `calls.py` — lo que dijo el proveedor, sin red: `Turn`, `CallSnapshot`, `CallRun`, `STATUS_MAP`, `TERMINAL_STATUSES` y los parsers puros `parse_turns`, `snapshot_from`, `run_from`.
- `checks.py` — el checklist, que no tenía módulo propio: `Check`, `Block`, `MARKS`, `all_checks`, `passed`, `unresolved`, `contradicted`, `all_ok`, `tally`, `render_blocks`.

`calle.py` queda solo con transporte y el trust boundary. `audit.py` borró su `Check` duplicado. `extract` y `dispositions` dejaron de tocar el cliente HTTP. Seis importadores actualizados, sin shims ni re-exports.

**Mover solo `Check` no alcanzaba:** la fitness function que este mismo hallazgo declara —*"`extract` y `dispositions` no importan `calle`"*— exige mover también los DTOs. Por eso se hicieron las dos mitades y no la que el reporte proponía sola.

**Fitness function:** `tests/test_layering.py`, seis reglas parametrizadas más una que afirma que ninguna capa de texto alcanza `urllib`. Verificado al revés: reponiendo `from ringdown.calle import Turn` en `extract.py`, la suite ni siquiera colecta.

**Nota de método:** durante la verificación al revés apareció un falso negativo que no era del código — restaurar un archivo con `cp` deja el mismo tamaño y el mismo segundo de mtime, así que Python revalidó un `.pyc` viejo. Los chequeos al revés de este hallazgo se corrieron limpiando `__pycache__` entre pasos.

---

## Sin hallazgos (revisado y correcto)

- **Dirección de dependencias:** grafo DAG limpio, verificado módulo por módulo. `canonical`, `incident` y `adapter` son puros. `dependencies = []` en `pyproject.toml`, stdlib estricta, sin SDK — coherente con `docs/plan.md:68-79`. Ninguna capa interna importa un framework.
- **Ciclos:** ninguno. `audit → escalate` y `verify → escalate` son unidireccionales.
- **Contrato del incident file y del rotation file:** validación completa y fail-closed en `incident.py`. E.164 sin reformateo (`incident.py:90-96`), timezones IANA validadas contra `zoneinfo` (`incident.py:109-116`), timestamps sin offset rechazados (`incident.py:140-143`), campos desconocidos de policy rechazados (`incident.py:152-154`), escalera con scopes duplicados rechazada (`incident.py:179-180`). Es la parte mejor construida del repo.
- **Contrato del adapter:** `adapter.py:10-30` tokeniza a mano, sin `eval`, sin regex de vendor; un path que no resuelve omite la clave y la omisión sale como error del loader, no como llamada.
- **Degradación ante drift del proveedor:** `snapshot_from` (`calle.py:121-139`) colapsa campos ausentes a defaults que caen del lado seguro — `status=""` no es terminal, `task_completed=None` no es `True`. Un renombre del proveedor produce exit 25 o 20, nunca un ack falso.
- **Modos de falla de red:** toda llamada tiene timeout. `wait_for_result` (`calle.py:212-225`) acota el poll contra un deadline monotónico y clampea el timeout por request al remanente. `CalleError.ambiguous`/`retriable` (`calle.py:36-42`) separan rechazo de incertidumbre, y el replay es **uno solo** con la misma key. La ausencia de reintento en el canal MCP era la única falta y quedó cubierta por el hallazgo 2.
- **Idempotencia de la key:** derivada del contenido del payload (`script.py:66-69`), sin nada per-run, estable entre procesos, impresa antes del POST. Es la propiedad que salva al hallazgo 3 de ser catastrófico.
- **Trust boundary del host:** `assert_trusted_base_url` (`calle.py:84-100`) valida **antes** de construir el cliente, rechaza credenciales en userinfo, query y fragment, y prohíbe http fuera de loopback. La key nunca viaja a un host no nombrado.
- **Estado global y acoplamiento temporal:** sin singletons, sin estado de módulo mutable, sin orden de inicialización significativo. Todos los dataclasses de dominio son `frozen=True`. `demo/run_local.py:124` escribe `os.environ` pero es entrypoint de demo, no biblioteca.
- **Esquema y migraciones:** no aplica, no hay base de datos. El único formato persistido es el ledger JSONL, cubierto arriba.
- **Estructura del monorepo:** `apps/python/ringdown/` **está justificada**, no es over-engineering. Espeja la estructura exigida por el repo destino (`docs/ringdown-brief.md:88-93`) y la decisión está registrada (`docs/plan.md:69`). No hay workspace config, ni CI, ni tooling de raíz — y eso es correcto: es un espejo de directorios, no un monorepo con pretensiones. Única observación: **no hay CI en ningún nivel**, así que todas las fitness functions de arriba dependen de que alguien corra pytest a mano.
- **Modelo de estados de `Attempt`:** `verify.py:51` desreferencia `attempt.snapshot.status` sin guarda mientras el tipo es `CallSnapshot | None`; trazados todos los caminos, no es alcanzable (solo `place_and_settle:96-106` produce `verdict == "acknowledged"`, y ahí el snapshot siempre está). La invariante se sostiene por construcción. Se menciona porque `report.py:117` y `audit.py:26` sí ponen la guarda y `verify.py` no: la inconsistencia sugiere que la invariante no está entendida igual en los tres lugares, pero sin costo actual no es hallazgo.

---

## Fuera de alcance

Los cuatro estados que hoy conviven en un solo `Attempt` (rechazado sin colocar / colocado sin resolver / resuelto / desconocido) pedirían un union type; eso es un rediseño, no un arreglo, y el sistema funciona sin él.

---

## Qué queda abierto

Los cinco ALTA están cerrados. Sigue pendiente, en orden de impacto:

1. **[MEDIA]** El ledger no tiene versión de esquema y `chain_checks` valida ledgers históricos con la `ladder_verdict` de hoy (hallazgo 6). El ceiling 6 del README ya contempla agregar re-llamados; ese día todo ledger anterior empieza a reportar adulteración. Falta también un golden commiteado y no regenerado — `examples/ledger.example.jsonl` lo regenera el demo antes de verificarlo, así que valida el código contra sí mismo.
2. **[MEDIA]** La cadena es sin clave y sin anclaje: truncar las últimas N líneas deja una cadena válida (hallazgo 7). El mínimo honesto es un `seq` monotónico y admitir el techo en el README.
3. **[BAJA]** `report.py` re-deriva `confident()` en vez de leer `attempt.reason` (hallazgo 8); `place_and_settle(attempt=...)` sigue siendo la perilla que el diseño prohíbe (hallazgo 9); `calle.py` mezcla transporte y objetos de valor, y `Check` se declara dos veces (hallazgo 10) — esta última empeoró levemente, porque el tipo de `Check` cambió en los dos lugares a la vez y nada garantiza que sigan sincronizados.

Sigue sin haber CI en ningún nivel: los 164 tests del repo dependen de que alguien corra `pytest` a mano.

**Nota sobre los números de línea:** las referencias `archivo:línea` de este reporte corresponden al estado previo a los arreglos. Los nombres de función y las descripciones siguen siendo válidos; los offsets se corrieron.
