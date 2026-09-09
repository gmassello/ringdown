# Regrabar el still del dashboard y re-ensamblar el demo

Plan para ejecutar mañana. Se deja escrito en `plan-still-dashboard.md`, en la raíz del proyecto,
junto a `plan-anti-inyeccion.md`. No se ejecuta nada más hoy.

## Contexto

`video/dashboard.png` es el primer still de cierre del video demo (2:50): muestra el dashboard del
receiver con la llamada real recibida en Argentina. Al rediseñarse `/calls` de tabla a tarjetas, el
still quedó mostrando la interfaz vieja. Está anotado como pendiente en `video/README.md`.

Al abrir el material aparecen dos cosas que cambian el trabajo:

**1. El still no es una imagen suelta: es un OUTRO del ensamblado.** `video/README.md:113-118` deja
el comando completo, con los números ya calculados a partir de `out/timing.txt`:

```
END=142.6  SLIDE=video/slide.png SLIDE_DUR=18.7
OUTRO="video/dashboard.png:4,video/closing.png:4.2"  OUTRO_REPLACE=8.2
```

Cambiar el PNG no toca el `demo.mp4` publicado. Pero **el material caro sigue en disco**:
`out/raw-fitted.mov` (el screencast ya ajustado al audio), `out/narration.wav`, `out/captions.srt`,
`out/timing.txt` y `out/timing-noslide.txt`. Así que re-ensamblar es un solo comando y **no hay que
regrabar ni terminal ni teléfono ni audio**.

**2. `mkstills.sh` no reproduce el PNG commiteado.** Para `dashboard.png` hace
`crop=1200:790:150:20`, `scale=-1:900`, `pad=1920:1080:…:150` y dibuja **una sola** línea a `y=60`,
lo que dejaría el recorte de `y=150` a `y=1050`. El PNG real tiene el texto a ~`y=267`, el dashboard
en una franja de ~420 px y una línea `github.com/gmassello/ringdown` en verde que el script no
dibuja. El artefacto y su generador divergieron, y el README declara al script como la forma de
regenerarlo.

Resultado buscado: el still muestra el dashboard actual con los números enmascarados, `mkstills.sh`
vuelve a producirlo tal cual, y `out/demo.mp4` queda regenerado con él.

## Objetivo

`video/dashboard.png` nuevo (1920x1080, dashboard rediseñado, números enmascarados), `mkstills.sh`
que lo regenere de forma reproducible, y `out/demo.mp4` re-ensamblado con el still nuevo — sin
regrabar ninguna toma.

## Suposiciones

- **Números enmascarados** (`+1********83 → +1********44`), decidido en la conversación. El dashboard
  imprime lo que tiene en la base, así que la llamada de demo se siembra ya enmascarada. El still
  queda distinto del video hoy publicado en ese detalle.
- **Se conserva el reproductor de audio**, en estado vacío como en el still viejo: la llamada
  sembrada lleva `recording_url` de `api.twilio.com` (como `_with_recording` en
  `apps/python/calle-receiver/tests/test_dashboard.py:51`) para que `_audio()` renderice el
  `<audio controls>`.
- Mismo contenido que el still viejo: llamada del 2026-08-16, `completed`, `18s`, y los cuatro
  segmentos (`This is a ring down test call…` / `Okay, is that there?` / `Thank you for your call.` /
  `The bridge.`).
- La composición replica la del still actual, no la del script: línea de contexto arriba
  (`The agent called a US Twilio number. It rang a phone in Argentina.`), dashboard al medio, repo en
  verde abajo.
- **Subir el video nuevo a YouTube es decisión tuya**, no parte de esto. El plan deja `demo.mp4`
  listo.

## Reglas del skill `personal-record-video` que aplican acá

Se usa el skill (`~/Documents/dotfiles/claude-code/skills/personal-record-video/`) para el
ensamblado. De sus reglas, las que tocan este trabajo:

- **`build-audio.sh` borra `video/out/` entero.** No se corre. Sería el error caro del día: se
  llevaría `raw-fitted.mov` y obligaría a rehacer el fit con las marcas de beat. Solo se corre
  `build-video.sh`.
- **`SLIDE_DUR` debe ser exactamente el largo del beat 1** (18.7 s en `out/timing.txt`) y
  `OUTRO_REPLACE` la suma de los outros (8.2). Los números ya están en el README y no cambian, porque
  el still nuevo ocupa el mismo lugar y la misma duración.
- **`dashboard.png` dura 4 s en pantalla.** El skill avisa que bajo ~3.5 s un still no se llega a
  leer, así que 4 s es el piso: el encuadre tiene que priorizar legibilidad sobre mostrarlo todo. La
  tarjeta nueva juega a favor (menos densa que la tabla), pero conviene recortar apretado.
- **libass**: sin él, el filtro de subtítulos falla al final de todo el encode. Verificar
  `ffmpeg -filters | grep " subtitles "` antes de ensamblar; si falta, `brew install ffmpeg@7` (los
  scripts prefieren el keg solos, y `mkstills.sh` ya lo hace).
- **El banner del debugger de Chrome no aplica acá.** Es un problema de las capturas en window mode
  con `Cmd+Shift+5`; el still se saca con la herramienta MCP, que fotografía solo el contenido de la
  página, sin chrome del navegador.
- **Las screenshots vuelven a una escala distinta del viewport**, así que las coordenadas del recorte
  se sacan de `getBoundingClientRect()`, nunca midiendo sobre la imagen.

## Pasos

1. **Capturar el dashboard nuevo.** Método que ya documenta `video/README.md:91-94` y que se usó al
   implementar el rediseño: receiver local contra una `calls.db` propia en el scratchpad, sembrar por
   `POST /voice` + cuatro `POST /voice/transcription` + `POST /voice/status`, marcar el
   `recording_url`, bajar la página con `curl -u`, servir esa copia estática y fotografiarla con
   Chrome. La copia estática existe porque el Basic Auth abre un diálogo nativo que bloquea la
   automatización. Ventana a 1280×800 con `resize_window`, como pide el skill.
2. **Derivar el recorte midiendo.** Con `javascript_tool` sobre la copia servida, leer el
   `getBoundingClientRect()` de `.call` y del encabezado y calcular de ahí el `crop=w:h:x:y`. El
   recorte viejo (`1200:790:150:20`, afinado a una ventana de 1505x812) no sirve: el layout pasó de
   tabla ancha a tarjeta más angosta y alta.
3. **`video/mkstills.sh` — arreglar el bloque de `dashboard.png`.** Nuevo `crop`, y las tres capas
   que el still realmente tiene: línea de contexto arriba, recorte escalado y centrado vía `pad`, y
   `github.com/gmassello/ringdown` en `$GO` abajo. Se reusan los helpers `line()` y `card()` y las
   variables de color que ya están en el script. No se toca la generación de `slide.png` ni de
   `closing.png`.
4. **Regenerar `video/dashboard.png`**: `bash video/mkstills.sh <captura>`.
5. **Re-ensamblar el mp4** con el comando del README, sin cambiar un número:
   ```bash
   VIDEO_DIR=$PWD/video END=142.6 \
     SLIDE=video/slide.png SLIDE_DUR=18.7 \
     OUTRO="video/dashboard.png:4,video/closing.png:4.2" OUTRO_REPLACE=8.2 \
     bash ~/Documents/dotfiles/claude-code/skills/personal-record-video/scripts/build-video.sh \
       video/out/raw-fitted.mov
   ```
   No se corre `fit-to-audio.py`: `raw-fitted.mov` ya está hecho y las marcas de beat no cambian.
6. **`video/README.md`** — quitar la anotación `**Shot before the dashboard was restyled** —
   re-shoot it before the next take` de la fila de `dashboard.png`. La sección *The dashboard still*
   describe bien el método y queda como está.

## Documentación

`video/README.md`, en el paso 6. Nada más: ningún otro doc describe el still. No cambia código Python
ni el sitio.

## Verificación

- **`slide.png` y `closing.png` no deben cambiar**: `mkstills.sh` los regenera siempre, así que
  `git status video/` tiene que listar `dashboard.png` como único PNG modificado.
- `dashboard.png` mide 1920x1080; abrirlo con la herramienta de imágenes y mirarlo: tarjeta entera,
  los cuatro segmentos legibles, nada cortado.
- **Números enmascarados**: revisión visual, y `grep` sobre el HTML capturado confirmando que no
  quedó ningún `+1832590` ni `+1364365`.
- Correr `mkstills.sh` dos veces con la misma captura y comparar `shasum` — prueba de que el script
  quedó reproduciendo el artefacto.
- `out/demo.mp4` regenerado: duración ~2:49.5 (`out/timing.txt`), y mirar los últimos 10 s para ver
  el still nuevo entrando donde iba el viejo. `ffprobe` para la duración, y extraer un frame del
  tramo del outro para confirmarlo a ojo.
- Legibilidad a 4 s: mirar el frame extraído al tamaño de un teléfono; si el texto de los segmentos
  no se lee, apretar más el recorte.
- Las dos suites siguen verdes (297 + 19), aunque no se toca Python.
- Apagar el receiver y el servidor estático que quedan levantados durante la captura.

## Fuera de alcance

- **Regrabar tomas**: terminal, teléfono y audio se reusan tal cual. No se corre `build-audio.sh`
  (borraría `out/`) ni `fit-to-audio.py`.
- **Subir el video a YouTube.** El plan deja `out/demo.mp4` y `out/demo.en.srt` listos.
- `slide.png`, `closing.png` y `thumbnail.png`: su contenido sigue vigente.
- `narration.tsv` y los tiempos: el still ocupa el mismo lugar y la misma duración.
- El dashboard vivo, el sitio y los dos paquetes Python.

## Explicación funcional para dummies

El video de demostración termina mostrando una foto de la pantalla donde se ven las llamadas
recibidas. Esa foto quedó vieja: muestra la pantalla como era antes, una planilla con filas y
columnas, y ahora esa pantalla tiene una ficha por llamada.

Se saca la foto de nuevo: se levanta el programa en la computadora, se le carga la misma llamada que
aparecía antes —misma fecha, mismos 18 segundos, las mismas cuatro frases— y se fotografía la
pantalla nueva. Los números de teléfono esta vez van tapados, como ya se hizo en la página web.

Lo bueno es que **no hay que volver a grabar nada**: ni la voz, ni la pantalla, ni el teléfono. Todo
ese material quedó guardado, así que se cambia la foto y se vuelve a armar el video con un solo
comando. Queda un archivo nuevo listo para subir; subirlo o no lo decidís vos.

De paso se arregla algo roto que no se notaba: hay un archivo que se supone que rehace esas fotos
automáticamente, y hoy no produce la que realmente se usa (le falta el renglón de abajo con la
dirección del repositorio, y encuadra distinto). Corregido, pedirle que rehaga la foto devuelve
exactamente la que va en el video.

El riesgo del día está anotado y es uno solo: hay un comando parecido (`build-audio.sh`) que borra
toda la carpeta de material generado. Si se corre por error, hay que rehacer el trabajo pesado de
sincronizar el video con la voz. No se corre.
