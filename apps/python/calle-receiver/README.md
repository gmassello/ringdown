# calle-receiver

Receptor de llamadas Twilio para la demo de Ringdown. CALL-E no soporta Argentina
como región destinataria, así que este servicio recibe la llamada del agente en un
número de EE.UU. y la reenvía a un celular argentino, guardando grabación y
transcripción en SQLite.

> Infraestructura de demo. El producto es [Ringdown](../ringdown/README.md).
> Diseño completo y bitácora en [`docs/plan-twilio-calle.md`](../../../docs/plan-twilio-calle.md).
>
> **En producción:** [`https://calle-receiver.onrender.com/calls`](https://calle-receiver.onrender.com/calls)
> — flujo completo CALL-E → Twilio → celular AR validado end-to-end el 16/08/2026.

## Flujo

```
Agente CALL-E → Número Twilio (+1) → POST /voice → TwiML <Dial> → celular AR (+54)
                                        ├─ <Start><Transcription> → POST /voice/transcription
                                        └─ record dual-channel     → POST /voice/recording
```

## Setup

### 1. Consola de Twilio (una sola vez)

1. Comprar un número de EE.UU. con Voice (`Phone Numbers → Buy a number`).
2. **Habilitar Argentina** en `Voice → Settings → Geographic Permissions`
   (sin esto el `<Dial>` falla con error `21215`).
3. Upgradear la cuenta (~US$20): las cuentas trial anteponen un mensaje
   pregrabado que arruina el video de demo.
4. Copiar `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN` desde `Account Info`.

### 2. Producción (Render)

Deployado en **`https://calle-receiver.onrender.com`** (free tier) vía Blueprint:
`render.yaml` en la raíz del repo + `Dockerfile` en este directorio. Todas las
env vars con valores reales (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
`PUBLIC_BASE_URL`, `TWILIO_NUMBER`, `FORWARD_TO`, `DASHBOARD_PASSWORD`) se
cargan en el dashboard de Render (`sync: false` en el `render.yaml`); el repo no
contiene secretos ni números de teléfono.

- **`calls.db` es efímero**: se limpia en cada deploy/restart (sin disco
  persistente en free tier). Para la demo alcanza.
- **El servicio se duerme a los 15 min de inactividad**: hacer `curl` a la URL
  antes de una demo o la primera llamada da timeout.
- Los webhooks del número se pueden apuntar sin pasar por la consola:

```python
client.incoming_phone_numbers("PNxxxx").update(
    voice_url="https://calle-receiver.onrender.com/voice",
    voice_method="POST",
    status_callback="https://calle-receiver.onrender.com/voice/status",
    status_callback_method="POST",
)
```

### 3. Local (desarrollo)

```bash
cd apps/python/calle-receiver
uv sync
cp .env.example .env   # completar credenciales, número y FORWARD_TO
uv run uvicorn app.main:app --reload --port 8000
cloudflared tunnel --url http://localhost:8000
```

Se usa cloudflared y no ngrok porque ngrok v3 no arranca sin el authtoken de una
cuenta. Copiar la URL `*.trycloudflare.com` a `PUBLIC_BASE_URL` en `.env` **y**
apuntar los webhooks del número ahí (snippet de arriba, o la consola). La URL
cambia en cada reinicio del túnel: actualizar los dos lados y reiniciar uvicorn.

## Pruebas (en orden, sin quemar créditos de CALL-E)

1. `uv run python scripts/test_outbound.py` — llama a tu celular desde el número
   Twilio; valida los geo permissions.
2. Llamar al número Twilio — **no desde el teléfono que es `FORWARD_TO`** (se
   reenviaría a sí mismo y termina en buzón). Hablar en inglés: la transcripción
   está en `en-US`.
3. Recién ahí, la primera llamada de CALL-E.

Los tres pasos están validados (16/08/2026): CALL-E disca a números VoIP de
Twilio sin bloqueo antifraude — llamada `completed` con grabación dual-channel
y transcripción de ambos tracks.

Tests unitarios: `uv run pytest`.

## Endpoints

| Endpoint | Qué hace |
|---|---|
| `POST /voice` | Webhook de llamada entrante: persiste la llamada y devuelve el TwiML de reenvío |
| `POST /voice/status` | Fin del `<Dial>`: guarda estado final y duración |
| `POST /voice/recording` | Guarda la `RecordingUrl` (descargarla con `.mp3` + auth básica SID:TOKEN) |
| `POST /voice/transcription` | Guarda un `TranscriptSegment` por evento `transcription-content` |
| `GET /calls` | Dashboard HTML: llamadas con player de audio y transcripción (auto-refresh 5s) |
| `GET /calls/{sid}/recording.mp3` | Proxy de la grabación (agrega auth de Twilio para el `<audio>`) |

Los webhooks `POST /voice*` validan la firma `X-Twilio-Signature` (desactivable
con `VALIDATE_TWILIO_SIGNATURE=false` para desarrollo local); `/voice/recording`
solo persiste `RecordingUrl` si apunta a `https://api.twilio.com/`. El dashboard
y el proxy de grabaciones piden **Basic Auth**: el password es la env var
`DASHBOARD_PASSWORD` (requerida — la app no arranca sin ella), el usuario es
indistinto.
