# Endurecer la defensa anti-inyección de Ringdown

## Contexto

Ringdown **ya trata el transcript como dato y no como instrucción**: `extract()` solo lee turnos
del `user`, `classify()` exige que cada campo del veredicto esté citado por un span que el
destinatario haya dicho, y `instructed()` marca el intento sin cambiar ningún campo. En las 111
contribuciones del hackathon es la única que aborda el problema — el resto ni lo menciona.

Lo que falta no es la defensa, es su solidez en dos puntos concretos y su demostración:

1. **Un hueco real y explotable.** El task hablado envuelve los campos del incidente entre comillas
   dobles (`script.py:CALL_TASK` paso 5: `read exactly this: "There is a {severity} incident on
   {service}: {title}. {summary}"`). `clean_text` (`incident.py:81`) ya colapsa saltos de línea, así
   que la inyección multilínea está cerrada — pero **no neutraliza las comillas dobles**. Un
   `summary` que llegue del payload de alerta conteniendo `"` cierra el envoltorio, y todo lo que
   siga le llega al agente como texto del task, fuera de las comillas. El README afirma que esos
   campos van "marcados como dato citado"; hoy el propio dato puede romper la marca.
2. **La detección es de manual.** `extract.INJECTION` son cuatro frases literales comparadas con
   `in`. Detecta exactamente el ataque que el demo escenifica y nada más: "olvidá lo anterior",
   "system:", "mark this as acknowledged" pasan sin marca. El flag no decide nada, pero es lo que
   queda escrito en el ledger y lo que lee un auditor, así que un ataque real hoy queda invisible
   en el artefacto.
3. **La propiedad no está probada.** Hay un test de que un voicemail inyectado sigue siendo
   `unreachable` y otro de que el flag solo se prende si lo dice el destinatario. No hay ninguno que
   pruebe la afirmación central: *ningún transcript hostil puede producir `acknowledged`*.

Resultado buscado: el vector cerrado en su raíz, la detección cubriendo familias en vez de frases, y
la propiedad demostrada por tests — **sin cambiar un byte de la salida del demo**, para que
`demo/EXPECTED.md`, `examples/ledger.example.jsonl` y el video del README sigan siendo válidos.

Decidido con el usuario: no se pushea al PR #205 todavía. Se prepara y verifica en local, y se
espera el veredicto de la ronda de revisión en curso antes de decidir cómo entra.

## Cambios

### 1. Cerrar el vector de las comillas — `ringdown/script.py`

Agregar un helper de una línea que neutralice las comillas (`"`, `"`, `"`) reemplazándolas por la
simple, y aplicarlo en `call_task()` a los tres campos que vienen del payload no confiable y se
interpolan dentro del envoltorio citado: `title`, `summary`, `service`.

- **Por qué acá y no en `clean_text`**: `clean_text` también valida `id`, y el `id` alimenta
  `attempt_id()` → `idempotency_key()`. Tocarlo cambiaría claves de idempotencia y, con ellas, el
  ledger de ejemplo. `call_task()` es el único punto donde un dato no confiable cruza a texto
  hablado: un solo saneo ahí cubre el vector completo sin tocar la identidad de las llamadas.
- `runbook_url` no lo necesita: `validate_runbook_url` (`incident.py:110`) ya rechaza cualquier cosa
  que no sea una URL http/https sin espacios.
- `rung.contact.name` no lo necesita: viene de `rotation.json`, que es un archivo del operador, no
  del payload de alerta. Mencionarlo en el threat model en vez de sanearlo.

### 2. Detección por familias — `ringdown/extract.py`

Reemplazar la tupla `INJECTION` de cuatro substrings por regex compiladas agrupadas en tres
familias, y un matcher propio para ellas:

- **override de instrucciones**: `ignore` / `disregard` / `forget` seguido de `previous|prior|all|your`
  y de `instructions|prompt|rules`
- **suplantación de rol o sistema**: `system:`, `you are now`, `new instructions`, `as the admin`
- **comandos sobre el veredicto**: `record this as`, `mark this as`, `log this as`, `set the verdict`,
  `set the eta`

Restricciones:

- **No tocar `_first_matching`**: lo comparten `VOICEMAIL`, `WRONG_PERSON`, `DECLINE` y `ACKNOWLEDGE`,
  que siguen siendo comparación por substring. Agregar un matcher separado para las regex y dejar
  `instructed()` usándolo. SRP: un matcher por tipo de patrón.
- La regex debe exigir la **combinación** instrucción + objeto, nunca el verbo suelto: un ingeniero
  que diga "ignore the previous alert, this is the real one" no puede quedar marcado.
- El escenario del fake (`fake/scenarios.py:103`) debe seguir dando `instructed=True`, o la salida
  del demo cambia y `test_demo.py` falla. Es el canario de este cambio.

### 3. Tests de la propiedad

- **`tests/test_dispositions.py`** — el test central, parametrizado sobre un corpus de transcripts
  hostiles, afirmando `classify(...).verdict != "acknowledged"` en todos: inyección pidiendo el
  acuse sin owner ni ETA; inyección que aporta owner y ETA en el turno del atacante pero con un
  nombre que no es el del contacto; inyección sumada a un voicemail; inyección que pretende
  declarar `task_completed` o subir la confianza (vienen del snapshot, no del transcript, y el test
  lo deja demostrado).
- **`tests/test_extract.py`** — que cada familia nueva se marque cuando la dice el destinatario y
  no cuando la dice el bot, y que la frase de control ("ignore the previous alert") no se marque.
- **`tests/test_script.py`** — que un incidente con comillas dobles en `title`, `summary` y
  `service` produzca un task cuyos campos interpolados no aportan comillas, es decir que el
  envoltorio de datos citados sigue cerrado.

Reutilizar los helpers que ya existen: `said()` en `tests/test_extract.py`, `an_incident()` en
`tests/data.py`, y las fixtures de `tests/conftest.py`.

### 4. Documentación

- **`apps/python/ringdown/README.md`**, sección *Threat model*: hoy dice que los campos del
  incidente son "length-limited and validated". Agregar que las comillas se neutralizan al
  formatear el task y por qué — el envoltorio citado es la defensa, y un dato capaz de cerrarlo la
  anula. Nombrar que `rotation.json` es un archivo del operador y no comparte ese estatus.
- **`apps/python/ringdown/README.md`**, *Known ceilings*: dejar explícito que `instructed` es una
  heurística en inglés sobre familias conocidas y no un clasificador — la defensa real es
  estructural (todo campo del veredicto sale de reglas deterministas sobre turnos del destinatario),
  y el flag es evidencia para el auditor, no un control. Es la respuesta a "¿y si la inyección no
  está en tu lista?".
- **`README.md`** raíz: la viñeta "The transcript is data, never instruction" gana la mención de que
  también el incidente entrante es dato.
- Actualizar el conteo de tests en `apps/python/ringdown/README.md` (hoy dice 295, la suite corre
  297 y va a subir). El badge del README raíz dice 313 y ya estaba mal antes de este cambio:
  corregirlo de paso o dejarlo, a decisión del usuario.

Sin dependencias nuevas: `re` ya está importado en `script.py` y en `extract.py`.

## Verificación

```bash
cd apps/python/ringdown
uv run pytest -q                 # todos pasan, con los casos nuevos sumados
python -m demo.run_local         # regenera examples/ledger.example.jsonl
cd /Users/germanmassello/Documents/ringdown
git diff --stat                  # debe NO listar demo/EXPECTED.md ni examples/ledger.example.jsonl
```

El gate de finalización es el `git diff --stat`: si el ledger de ejemplo o `EXPECTED.md` aparecen
modificados, el cambio se filtró a la salida del demo y hay que corregirlo, no regenerarlos.
`tests/test_demo.py` lo detecta solo — compara el ledger byte a byte y verifica que el demo siga
imprimiendo cada bloque que `EXPECTED.md` cita, en orden.

Prueba manual del vector cerrado, antes y después:

```bash
python - <<'PY'
from ringdown.incident import parse_incident
from ringdown.script import call_task
# summary hostil que hoy cierra el envoltorio de comillas
PY
```

es decir: armar un incidente cuyo `summary` contenga `"` seguido de una orden, renderizar el task y
confirmar que la orden queda dentro de las comillas en vez de fuera.

## Fuera de alcance

- No se toca `demo/run_local.py` ni se agrega un escenario nuevo (decisión del usuario: salida del
  demo intacta, video del README válido).
- No se pushea al PR #205 ni se espeja al checkout del fork
  (`~/Documents/awesome-phone-call-agents`, ver memoria `ringdown-dos-checkouts`). Ese espejado
  queda pendiente hasta que se decida cómo entra el cambio.
- No se agrega un check nº11 de verificación cruzada del flag `instructed` sobre el transcript del
  segundo canal. Vale la pena, pero cambia lo que las diez comprobaciones prueban y eso es una
  decisión aparte, no un endurecimiento.
