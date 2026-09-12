# Ringdown vs. triage-line (PR #506)

Apareció en la misma categoría el 12 de septiembre. Esto es lo que hay que saber si un jurado lo
menciona.

## Qué es

`apps/typescript/triage-line/` — orquestador de tareas telefónicas sobre el SDK `@call-e/calle`, en
TypeScript. Dos topologías: **fan-out** (llama a varios residentes en paralelo, clasifica por
urgencia y escala a médicos de cabecera) y **chain** (el resultado de cada llamada determina cuál es
la siguiente, armando un grafo dinámico). Trae política de consentimiento, reintento en otro idioma
si detecta barrera idiomática, revisión humana con auditoría, y default sin llamadas reales.

## En qué se parece

- Los dos escalan por teléfono en vez de dar por cerrada una notificación enviada.
- Los dos tienen modo seguro por default: nada disca sin configuración explícita.
- Los dos desconfían del `completionConfidence` del proveedor como única señal.

## En qué no

**La diferencia es el número de canales, y es la única que importa.**

triage-line verifica por el mismo canal que escribió: gatea por `completionConfidence`, chequea que
estén los campos requeridos y confirma que los valores aparezcan en el transcript. Es verificación
en capas, pero todas las capas leen la misma fuente — si el proveedor devuelve mal el estado de una
llamada, las tres capas se equivocan juntas y en la misma dirección.

Ringdown **coloca la llamada por REST y la verifica por MCP**. Son dos transportes distintos: el que
verifica nunca vio la escritura. Y un tercer paso, `verify`, vuelve a derivar el veredicto desde el
ledger sellado, sin red, meses después. Un canal que se autoconfirma no prueba lo mismo que dos que
tienen que coincidir — y cuando no coinciden, Ringdown lo dice: exit 40 es "los canales se
contradicen", distinto de exit 45, "el segundo canal no contestó". Un canal caído nunca se lee como
un canal que disiente.

De ahí salen tres cosas que triage-line no tiene:

- **Ledger encadenado por hash**, con el veredicto re-derivable por la regla de la versión de schema
  que lo escribió.
- **Una llamada por escalón, siempre**: la clave de idempotencia sale del contenido del payload, así
  que un create ambiguo se reintenta con la misma clave en vez de despertar a una segunda persona.
- **Cero dependencias en runtime** — stdlib de Python — contra el SDK oficial. Menos superficie que
  confiar.

## El párrafo, si hay que decirlo en voz alta

> triage-line y Ringdown atacan el mismo problema por lados distintos. Ellos exploran topologías:
> a quién llamar después, en paralelo o en cadena. Nosotros exploramos evidencia: cómo sabés que la
> llamada que dice "atendió y se hizo cargo" realmente pasó. Ellos verifican con tres capas sobre un
> solo canal; nosotros escribimos por REST, verificamos por MCP y volvemos a derivar el veredicto
> desde un ledger sellado sin tocar la red. Un canal que se confirma a sí mismo no es verificación,
> es una segunda lectura del mismo informe.
