# calle-receiver

Twilio call receiver for the Ringdown demo. CALL-E does not support Argentina
as a destination region, so this service receives the agent's call on a US
number and forwards it to an Argentine cell phone, storing the recording and
transcription in SQLite.

> Demo infrastructure. The product is [Ringdown](../ringdown/README.md).
>
> **In production:** [`https://calle-receiver.onrender.com/calls`](https://calle-receiver.onrender.com/calls)
> — full CALL-E → Twilio → AR cell phone flow validated end-to-end on 2026-08-16.

## Flow

```
CALL-E agent → Twilio number (+1) → POST /voice → TwiML <Dial> → AR cell phone (+54)
                                        ├─ <Start><Transcription> → POST /voice/transcription
                                        └─ record dual-channel     → POST /voice/recording
```

## Setup

### 1. Twilio console (one time)

1. Buy a US number with Voice (`Phone Numbers → Buy a number`).
2. **Enable Argentina** in `Voice → Settings → Geographic Permissions`
   (without this the `<Dial>` fails with error `21215`).
3. Upgrade the account (~US$20): trial accounts prepend a pre-recorded
   message that ruins the demo video.
4. Copy `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` from `Account Info`.

### 2. Production (Render)

Deployed at **`https://calle-receiver.onrender.com`** (free tier) via Blueprint:
`render.yaml` at the repo root + `Dockerfile` in this directory. All env vars
with real values (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
`PUBLIC_BASE_URL`, `TWILIO_NUMBER`, `FORWARD_TO`, `DASHBOARD_PASSWORD`) are
set in the Render dashboard (`sync: false` in `render.yaml`); the repo
contains no secrets and no phone numbers.

- **`calls.db` is ephemeral**: it is wiped on every deploy/restart (no
  persistent disk on the free tier). Good enough for the demo.
- **No schema migrations**: `DATABASE_URL` accepts Postgres and the engine
  starts, but the schema is created with `create_all`, which only adds
  missing tables — it never alters existing columns. Deliberate decision for
  the demo; if the schema changes with data in production, bring in Alembic.
- **The service sleeps after 15 min of inactivity**: `curl` the URL before a
  demo, or the first call times out.
- The number's webhooks can be pointed without going through the console:

```python
client.incoming_phone_numbers("PNxxxx").update(
    voice_url="https://calle-receiver.onrender.com/voice",
    voice_method="POST",
    status_callback="https://calle-receiver.onrender.com/voice/status",
    status_callback_method="POST",
)
```

### 3. Local (development)

```bash
cd apps/python/calle-receiver
uv sync
cp .env.example .env   # fill in credentials, number and FORWARD_TO
uv run uvicorn app.main:app --reload --port 8000
cloudflared tunnel --url http://localhost:8000
```

cloudflared is used instead of ngrok because ngrok v3 does not start without
an account's authtoken. Copy the `*.trycloudflare.com` URL to
`PUBLIC_BASE_URL` in `.env` **and** point the number's webhooks there (snippet
above, or the console). The URL changes on every tunnel restart: update both
sides and restart uvicorn.

## Testing (in order, without burning CALL-E credits)

1. `uv run python scripts/test_outbound.py` — calls your cell phone from the
   Twilio number; validates the geo permissions.
2. Call the Twilio number — **not from the phone that is `FORWARD_TO`** (it
   would forward to itself and end up in voicemail). Speak in English: the
   transcription is in `en-US`.
3. Only then, the first CALL-E call.

All three steps are validated (2026-08-16): CALL-E dials Twilio VoIP numbers
without anti-fraud blocking — `completed` call with dual-channel recording
and transcription of both tracks.

Unit tests: `uv run pytest`.

## Endpoints

| Endpoint | What it does |
|---|---|
| `POST /voice` | Incoming call webhook: persists the call and returns the forwarding TwiML |
| `POST /voice/status` | End of the `<Dial>`: stores final status and duration |
| `POST /voice/recording` | Stores the `RecordingUrl` (download it with `.mp3` + basic auth SID:TOKEN) |
| `POST /voice/transcription` | Stores one `TranscriptSegment` per `transcription-content` event |
| `GET /calls` | HTML dashboard: calls with audio player and transcript (5s auto-refresh) |
| `GET /calls/{sid}/recording.mp3` | Recording proxy (adds Twilio auth for the `<audio>` element) |

The `POST /voice*` webhooks validate the `X-Twilio-Signature` header (can be
disabled with `VALIDATE_TWILIO_SIGNATURE=false` for local development);
`/voice/recording` only persists a `RecordingUrl` that points to
`https://api.twilio.com/`. The dashboard and the recording proxy require
**Basic Auth**: the password is the `DASHBOARD_PASSWORD` env var (required —
the app does not start without it), the username does not matter.
