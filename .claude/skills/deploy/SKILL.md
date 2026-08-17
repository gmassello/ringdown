---
name: deploy
description: How calle-receiver is deployed and operated on Render. Use for deploy/redeploy requests, production issues (service asleep, cold start, empty dashboard after deploy), changing env vars or secrets, reading production behavior, or anything touching render.yaml, the Dockerfile, or the public URL.
---

# Deploy — calle-receiver on Render

All verified hands-on on 2026-08-16. Twilio-side details (webhooks, signature,
local tunnel) live in the `twilio` skill — cross-referenced, not duplicated.

## What is deployed

- **Service**: `calle-receiver`, Render **free tier**, live at
  **https://calle-receiver.onrender.com**.
- Created as Blueprint **`ringdown`** from `render.yaml` at the repo root;
  the service builds `apps/python/calle-receiver/Dockerfile` (uv/python3.12
  image, `uv sync --frozen --no-dev --no-install-project`, uvicorn on `$PORT`).
- Render account: Germán's workspace, login via GitHub (`@gmassello`).

## How to deploy

**Push to `main` on `gmassello/ringdown`. That's it.** Render auto-syncs the
Blueprint and auto-deploys on every push. There is no manual step. Edits to
`render.yaml` also sync automatically — Render warns this "may change your
costs", so review plan/instance changes before pushing.

## Env vars and secrets

- ALL env vars (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `PUBLIC_BASE_URL`,
  `TWILIO_NUMBER`, `FORWARD_TO`, `DASHBOARD_PASSWORD`) are `sync: false` in
  `render.yaml`: their values live **only in the Render dashboard**
  (service → Environment), never in the repo. Never paste the auth token
  anywhere — the user enters it in the dashboard themselves.
- `DASHBOARD_PASSWORD` protects `GET /calls` and the recording proxy (Basic
  Auth, any username) and is **required at startup** — a deploy that can't
  find it crashes in seconds with a pydantic validation error. If a deploy
  fails right after changing env vars, check this one first.
- `PUBLIC_BASE_URL` is currently `https://calle-receiver.onrender.com`.

## Free-tier gotchas

- **SQLite is ephemeral**: `calls.db` is wiped on every deploy and restart.
  An empty dashboard after a deploy is normal, not a bug. Persistent disks are
  a paid feature.
- **The service sleeps after 15 min idle.** Cold start is ~30s; Twilio times
  out webhooks at 15s, so a call that arrives while asleep fails. **Before any
  demo or expected call**: `curl -s https://calle-receiver.onrender.com/calls`
  to wake it, then wait for the response (401 without credentials is fine —
  the service is awake).

## If the public URL ever changes

Three steps, all required: (1) update `PUBLIC_BASE_URL` in the Render
dashboard, (2) redeploy so settings reload, (3) re-point the Twilio number's
webhooks via REST API (console sessions expire; the API always works):

```python
client.incoming_phone_numbers("PN939da01ace5684ac0edbff0d70deb11e").update(
    voice_url=f"{url}/voice", voice_method="POST",
    status_callback=f"{url}/voice/status", status_callback_method="POST",
)
```

## Post-deploy verification

1. `curl <url>/calls` → **401** (service up, dashboard auth active).
2. `curl -u "x:$DASHBOARD_PASSWORD" <url>/calls` → 200 (password loaded).
3. `curl -X POST <url>/voice -d "CallSid=x"` → **403** — proves the Twilio
   credentials loaded and signature validation is active.
4. A real call to +1 364 365 8544 appears in `/calls` with recording and
   transcript.

## Local notes

- `docker build` does not work on this machine (colima VM is broken) — rely on
  Render's build; the Dockerfile is simple enough that Render is the test.
- Local development runs uvicorn + cloudflared, not Render — see the `twilio`
  skill.
