---
name: twilio
description: Verified Twilio operational knowledge for this project (calle-receiver inbound relay). Use when configuring or debugging voice webhooks, geo permissions, the public tunnel, recordings, live transcription, navigating the new Twilio One console, or facing 21215 errors / invalid signatures / calls that never arrive.
---

# Twilio — CALL-E receiver (calle-receiver)

Everything below was verified hands-on on 2026-08-16. The receiver app lives in
`apps/python/calle-receiver/`.

## Account and resources

- Account SID: `<ACCOUNT_SID>` — read it as `TWILIO_ACCOUNT_SID` from
  `apps/python/calle-receiver/.env`. Credentials (auth token, API keys) live in
  `apps/python/calle-receiver/.env` and `apps/python/ringdown/.env` — reference
  them by path, never paste them into versioned files.
- Number: `<TWILIO_NUMBER>` (US local, Voice channel) — read it as
  `TWILIO_NUMBER` from `apps/python/calle-receiver/.env`. Account already
  upgraded (Active) — no trial message plays.
- Flow: CALL-E / any caller → Twilio number → `POST /voice` → TwiML `<Dial>`
  to the Argentine cell (`FORWARD_TO`), with dual-channel recording and live
  transcription. Everything persists to `calls.db` (SQLite, tables `call` and
  `transcriptsegment`).
- Tests: `cd apps/python/calle-receiver && uv run pytest`.

## New console (Twilio One) — old deeplinks break

`console.twilio.com/...` redirects to `1console.twilio.com` and the
translation drops the `develop` segment → not-found page. Routes that work:

- Geo permissions: `1console.twilio.com/account/<SID>/us1/voice/settings/geo-permissions-settings/low-risk`
- Numbers: `1console.twilio.com/account/<SID>/us1/phone-numbers/manage/incoming`
  → click the number → Voice Configuration.
- If a route breaks, the search tool (magnifier, top right) finds any page by
  name.

UI gotchas:

- Geo permission toggles **save instantly** (there is no Save button).
- The "Enable continent" toggle is an aggregate of the filtered view: it shows
  blue when filtering by an enabled country, but it does NOT mean the whole
  continent is enabled.
- The number configuration page **does** have a "Save configuration" button;
  success is confirmed by the "Number was successfully updated" toast.
- The geo permissions table scrolls horizontally: the "Enable destination"
  column sits off-screen to the right.

## Geo permissions

- Only **Argentina (+54)** is enabled. Without it, `<Dial>` to +54 fails with
  **error 21215**.
- Forwarding cost to an AR mobile: US$0.060–0.353/min (Programmable Voice).

## Registrations you do NOT need

SHAKEN/STIR, Voice Integrity, Branded Calling and CNAM only improve the
reputation of **outbound calls to US numbers** (avoiding "Spam Likely"). For
receiving and forwarding to Argentina, skip them all.

## Production deploy (Render)

- Live at **https://calle-receiver.onrender.com** (free tier, Blueprint from
  `render.yaml` at the repo root, Docker build from
  `apps/python/calle-receiver/Dockerfile`). The number's webhooks point there.
- `calls.db` is **ephemeral**: wiped on every deploy/restart (no persistent
  disk on free tier). Fine for the demo; the dashboard fills live.
- Free tier sleeps after 15 min idle → first call times out. `curl` the URL to
  wake it before any demo.
- The number's webhooks can be updated via REST API without the console:
  `client.incoming_phone_numbers('PN939da01ace5684ac0edbff0d70deb11e').update(voice_url=..., status_callback=...)`
  — useful because Twilio console sessions expire.

## Local tunnel (dev only)

- ngrok v3 **will not start without an account authtoken** and none is
  configured on this machine. cloudflared is used instead (no account needed):
  ```bash
  /opt/homebrew/bin/cloudflared tunnel --url http://localhost:8000
  # the https://*.trycloudflare.com URL appears in the log
  cd apps/python/calle-receiver && uv run uvicorn app.main:app --port 8000
  ```
- The trycloudflare URL **changes on every tunnel restart**. When it changes,
  THREE things must happen: update `PUBLIC_BASE_URL` in `.env`, restart
  uvicorn (settings load at startup), and re-save the number's webhooks in the
  console (`A call comes in` → `<URL>/voice`, `Call status changes` →
  `<URL>/voice/status`, both HTTP POST).
- `/opt/homebrew/bin` may be missing from the sandbox PATH: use absolute paths
  for ngrok/cloudflared.

## Webhooks and signature

- The `X-Twilio-Signature` is validated against `PUBLIC_BASE_URL + path`
  (never `request.url`: behind the proxy it arrives as `http://` and
  validation fails). Implemented in `app/security.py` as the `twilio_form`
  dependency, which validates and returns the form.
- A POST without a valid signature returns 403 — that is the quick proof the
  tunnel→app circuit works: `curl -X POST <URL>/voice -d "CallSid=x"` → 403.
- Live transcription: the callback sends form-data with
  `TranscriptionEvent=transcription-content` and `TranscriptionData` as JSON
  (`{"transcript": ..., "confidence": ...}`); the track arrives in `Track`
  (`inbound_track` / `outbound_track`). Other events: `-started`, `-stopped`,
  `-error`.
- The end-of-`<Dial>` callback carries `DialCallStatus` and
  `DialCallDuration`.

## Recordings

The `RecordingUrl` delivered to the callback comes without an extension and
without auth. To download it: append `.mp3` and use basic auth
`ACCOUNT_SID:AUTH_TOKEN`.

## How to test without burning CALL-E credits

1. `PYTHONPATH=. uv run python scripts/test_outbound.py` — calls `FORWARD_TO`
   from the Twilio number; validates geo permissions (verified: call
   `completed`).
2. Manual inbound call: **never call from the phone that is `FORWARD_TO`**
   (Twilio tries to forward the call to the same phone that is busy calling →
   voicemail). Use another phone. From an Argentine landline dial `00` followed
   by the Twilio number without the `+` (requires international dialing
   enabled; international rates apply).
3. Speak **English** during the test: transcription is set to `en-US` and
   Spanish produces garbage, so you cannot validate it. Both sides should talk
   to cover both tracks. Verified end-to-end: 16s call, 3 segments,
   downloadable recording.

## CALL-E ↔ Twilio, confirmed

**CALL-E does dial VoIP/Twilio numbers** (verified 2026-08-16: call to the
Twilio number `completed` with `task_completed=True`; CALL-E's caller ID was
`+1832***3283`). The full loop CALL-E → Twilio → AR cell works end-to-end with
recording and both-track transcription. To place a CALL-E call, reuse
`RestClient` from `apps/python/ringdown/ringdown/calle.py`
(`POST https://api.heycall-e.com/v1/calls`, Bearer `CALLE_API_KEY` from
`apps/python/ringdown/.env`, payload `{task, recipients: [{phones: [...]}],
metadata}` plus an `Idempotency-Key` header; poll with `wait_for_result`).
