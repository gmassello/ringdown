# calle-receiver

Receptor de llamadas Twilio para la demo de Ringdown. CALL-E no soporta Argentina
como región destinataria, así que este servicio recibe la llamada del agente en un
número de EE.UU. y la reenvía a un celular argentino, guardando grabación y
transcripción en SQLite.

> Infraestructura de demo. El producto es [Ringdown](../ringdown/README.md).
> Diseño completo en [`docs/plan-twilio-calle.md`](../../../docs/plan-twilio-calle.md).

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

### 2. Local

```bash
cd apps/python/calle-receiver
uv sync
cp .env.example .env   # completar credenciales, número y FORWARD_TO
uv run uvicorn app.main:app --reload --port 8000
ngrok http 8000
```

Copiar la URL de ngrok a `PUBLIC_BASE_URL` en `.env` **y** configurar el número en
`Phone Numbers → tu número → Voice Configuration`:

- **A call comes in:** Webhook → `https://TU_URL/voice` → HTTP POST
- **Call status changes:** `https://TU_URL/voice/status` → HTTP POST

La URL de ngrok cambia en cada reinicio: reconfigurar ambos lados.

## Pruebas (en orden, sin quemar créditos de CALL-E)

1. `uv run python scripts/test_outbound.py` — llama a tu celular desde el número
   Twilio; valida los geo permissions.
2. Llamar al número Twilio desde tu celular: debe reenviar, grabar y transcribir.
3. Recién ahí, la primera llamada de CALL-E (confirma que disca a VoIP).

Tests unitarios: `uv run pytest`.

## Endpoints

| Endpoint | Qué hace |
|---|---|
| `POST /voice` | Webhook de llamada entrante: persiste la llamada y devuelve el TwiML de reenvío |
| `POST /voice/status` | Fin del `<Dial>`: guarda estado final y duración |
| `POST /voice/recording` | Guarda la `RecordingUrl` (descargarla con `.mp3` + auth básica SID:TOKEN) |
| `POST /voice/transcription` | Guarda un `TranscriptSegment` por evento `transcription-content` |

Todos validan la firma `X-Twilio-Signature` (desactivable con
`VALIDATE_TWILIO_SIGNATURE=false` para desarrollo local).
