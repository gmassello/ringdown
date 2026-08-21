# Plan: a Twilio call receiver for the CALL-E hackathon

> **Status (16 Aug 2026):** implemented in `apps/python/calle-receiver/` (forward mode).
> Number `+13643658544` purchased, account upgraded, Argentina enabled, webhook
> configured, outbound test OK, inbound flow validated (§7.2) and the **full
> CALL-E → Twilio → Argentine mobile flow validated end to end** (§7.3–7.4:
> CALL-E does dial VoIP; recording and transcription land in `calls.db`). The
> `/calls` dashboard is done (§5.8) and it is **deployed on Render** (§6):
> `https://calle-receiver.onrender.com`, with the number's webhooks pointing
> there. cloudflared is only for local development. What was learned lives in the
> `.claude/skills/twilio/` skill. Browser mode (§5.7) was **discarded**.

> **Update (20 Aug 2026):** delivered. Six real calls were placed through this
> bridge (see `docs/plan.md`, Stage 10), the demo video is published at
> [youtu.be/WIYBWFslix4](https://youtu.be/WIYBWFslix4), and the pull request is
> open as
> [CALLE-AI/awesome-phone-call-agents#205](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/205).
> What is left is the Devpost submission itself.

> **Goal:** have a United States phone number that can receive the CALL-E agent's
> calls, forward them to an Argentine mobile or to a softphone in the browser, and
> keep a recording and a transcript of each one.
>
> **Context:** CALL-E supports these recipient regions:
> `US, SG, MY, IN, AE, AU, CA, GB, VN, DE, JP, FR, MX, BR, ID, PH, KE`.
> Argentina and Chile are **not** on the list, so an Argentine mobile cannot
> receive the agent's calls directly. This project closes that gap.
>
> **Stack:** Python 3.11+ / FastAPI / Twilio SDK.
> **Hackathon deadline:** 14 September 2026, 23:45 SGT.

---

## 0. Preflight checks (do these BEFORE writing code)

These two can invalidate the whole plan. Settle them first.

### 0.1 Does CALL-E dial VoIP numbers? — ✅ RESOLVED (16 Aug: yes it does; call `call_Fl_CuNVz...` completed, task_completed=True)

Twilio hands out VoIP numbers. Some voice platforms block them for fraud reasons.
**Ask in the CALL-E Discord** (https://discord.gg/6AbXUzUV8w) or spend one call
testing against the freshly purchased number.

- If it **does** dial → carry on with this plan.
- If it **does not** → plan B: a real prepaid US eSIM (Ultra Mobile PayGo ~US$3/month,
  US Mobile, Tello). Requires activation under US coverage, or buying a pre-activated
  eSIM. Slower and more expensive, but it is a legitimate mobile line.

### 0.2 Voice geographic permissions in Twilio — ✅ DONE (16 Aug, Argentina only)

Twilio **blocks international outbound calls by default**. For the forward to `+54`
to work, Argentina has to be enabled by hand:

`Console → Voice → Settings → Geographic Permissions → tick Argentina → Save`

Without this, the `<Dial>` to the Argentine mobile fails with error `21215`.

---

## 1. Architecture

```
┌──────────────┐    calls     ┌─────────────────┐   webhook    ┌──────────────┐
│  CALL-E      │─────────────▶│  Twilio number  │─────────────▶│   FastAPI    │
│  agent       │              │  +1 (XXX) ...   │   POST       │   /voice     │
└──────────────┘              └─────────────────┘              └──────┬───────┘
                                                                      │
                                                            returns TwiML
                                                                      │
                                        ┌─────────────────────────────┴──┐
                                        │                                │
                             MODE=forward│                    MODE=browser│
                                        ▼                                ▼
                              ┌──────────────────┐         ┌──────────────────────┐
                              │ AR mobile (+54)  │         │ Softphone in the     │
                              │ actually rings   │         │ browser (Voice SDK)  │
                              └──────────────────┘         └──────────────────────┘

        In parallel: <Start><Transcription> → POST /voice/transcription  (live text)
                     record="record-from-answer-dual" → POST /voice/recording (audio)
                     → both persist to SQLite → dashboard at /calls
```

**Two receive modes, selectable by environment variable:**

| Mode | When to use it | Termination cost |
|---|---|---|
| `forward` | Demo video: you see a real call arriving at a real phone | ~US$0.06–0.35/min to an AR mobile |
| `browser` | Development and fast iteration; easy to screen-record | US$0.004/min (Client) |

---

## 2. Estimated costs

| Item | Price |
|---|---|
| US local number | ~US$1.15/month |
| Inbound call (local) | ~US$0.0085/min |
| Forward to an Argentine mobile | ~US$0.06–0.353/min (verified hands-on; the Twilio calculator understates it) |
| Forward to `<Client>` (browser) | ~US$0.004/min |
| Recording plus storage | ~US$0.0025/min each |
| Real-time transcription | ~US$0.05/min |
| CALL-E calls | billed against a credit balance, ~US$0.05 per connected call; failed calls are not billed |

**Realistic budget for the whole hackathon: under US$15.**
Twilio asks for an upgrade with US$20 of balance (see §3.2); that balance is spent, not lost.

> Correction observed on 20 Aug: CALL-E does not give "20 free calls", it runs on a
> credit balance. A US$1.00 top-up covered every call this project made, and only
> connected calls were charged.

---

## 3. Manual Twilio setup (before the code)

### 3.1 Create an account and buy a number — ✅ DONE (`+13643658544`, Voice channel)

1. Create an account at twilio.com (works from Argentina, with an Argentine card).
2. `Console → Phone Numbers → Buy a number`
3. Filter: **Country = United States**, capabilities **Voice** ✅
4. Buy any local number (~US$1.15/month). The area code does not matter.
5. Write the number down in E.164 form: `+1XXXXXXXXXX`.

### 3.2 Upgrade the account (important for the video) — ✅ DONE (Active, ~US$18.85 balance)

Twilio trial accounts:
- can only call numbers **verified** in advance, and
- play a **pre-recorded "trial account" message** before every call.

That message ruins the demo video. Top up US$20 and upgrade.
(If you want to test on trial anyway: `Console → Phone Numbers → Verified Caller IDs`
and verify your Argentine mobile.)

### 3.3 Enable geographic permissions — ✅ DONE

See §0.2. Tick **Argentina** in Geographic Permissions.

### 3.4 Credentials to keep — ✅ DONE (in `apps/python/calle-receiver/.env`; the browser-mode API keys were never needed)

From `Console → Account Info`:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

Browser mode would also need (`Console → Account → API keys & tokens`):
- `TWILIO_API_KEY_SID` and `TWILIO_API_KEY_SECRET` (create a Standard API Key)
- `TWILIO_TWIML_APP_SID` (create it under `Voice → TwiML → TwiML Apps`)

---

## 4. Project structure

```
calle-receiver/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app plus router registration
│   ├── config.py            # Settings with pydantic-settings
│   ├── security.py          # X-Twilio-Signature validation
│   ├── db.py                # SQLite plus SQLModel
│   ├── models.py            # Call, TranscriptSegment
│   └── routes/
│       ├── voice.py         # /voice, /voice/status, /voice/recording, /voice/transcription
│       ├── token.py         # /token  (browser mode only)
│       └── dashboard.py     # /calls  (simple HTML to review calls)
├── static/
│   └── softphone.html       # Voice SDK client (browser mode only)
├── scripts/
│   └── test_outbound.py     # validates geo permissions by calling your AR mobile
├── .env.example
├── requirements.txt
└── README.md
```

---

## 5. Step-by-step implementation

### Step 1 — Scaffolding — ✅ DONE (in `apps/python/calle-receiver/`, with `uv` instead of venv+pip)

```bash
mkdir calle-receiver && cd calle-receiver
python -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" twilio pydantic-settings sqlmodel python-multipart jinja2
pip freeze > requirements.txt
```

### Step 2 — Configuration (`app/config.py`) — ✅ DONE (without the browser-mode vars; E.164 validation added for the numbers)

Required environment variables:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_NUMBER=+1XXXXXXXXXX

# Receive mode: "forward" | "browser"
RECEIVE_MODE=forward

# forward mode only
FORWARD_TO=+54911XXXXXXXX

# browser mode only
TWILIO_API_KEY_SID=SKxxxxxxxx
TWILIO_API_KEY_SECRET=xxxxxxxx
TWILIO_TWIML_APP_SID=APxxxxxxxx
CLIENT_IDENTITY=german

# Extras
PUBLIC_BASE_URL=https://xxxx.ngrok-free.app
ENABLE_RECORDING=true
ENABLE_TRANSCRIPTION=true
TRANSCRIPTION_LANGUAGE=en-US
VALIDATE_TWILIO_SIGNATURE=true
```

> `TRANSCRIPTION_LANGUAGE`: the CALL-E agent speaks English when the recipient
> region is `US`, so `en-US` is the right value. Change it to `es-MX` only when
> testing against the `MX` region.

### Step 3 — Models and persistence (`app/models.py`, `app/db.py`) — ✅ DONE (`call_sid` as the PK; `mode` and `is_final` dropped until browser mode exists)

```python
class Call(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    call_sid: str = Field(index=True, unique=True)
    from_number: str
    to_number: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    status: str                      # ringing, in-progress, completed, failed...
    recording_url: str | None = None
    mode: str                        # forward | browser

class TranscriptSegment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    call_sid: str = Field(index=True)
    track: str                       # inbound_track | outbound_track
    text: str
    confidence: float | None = None
    is_final: bool = True
    created_at: datetime
```

SQLite via `sqlmodel.create_engine("sqlite:///calls.db")`. Enough for a hackathon.

### Step 4 — Signature validation (`app/security.py`) — ✅ DONE (as a FastAPI dependency that validates and returns the form; the proxy gotcha is handled)

Twilio signs every webhook with `X-Twilio-Signature`. Without validation, anyone
can POST to your public endpoint.

```python
from twilio.request_validator import RequestValidator

async def verify_twilio(request: Request) -> None:
    if not settings.validate_twilio_signature:
        return
    validator = RequestValidator(settings.twilio_auth_token)
    form = await request.form()
    url = str(request.url)               # must match EXACTLY what was configured
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(url, dict(form), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
```

> **Gotcha:** behind ngrok or Render, `request.url` can arrive as `http://` while
> Twilio signed `https://`. Rebuild the URL from `PUBLIC_BASE_URL` +
> `request.url.path` instead of trusting `request.url`.

### Step 5 — The main webhook (`app/routes/voice.py`) — ✅ DONE (forward mode only)

`POST /voice` — this is what Twilio calls when a call comes in.

```python
@router.post("/voice")
async def incoming_call(request: Request):
    await verify_twilio(request)
    form = await request.form()
    call_sid = form["CallSid"]
    save_call_start(call_sid, form["From"], form["To"], settings.receive_mode)

    vr = VoiceResponse()

    # 1) Real-time transcription (starts before the Dial)
    if settings.enable_transcription:
        start = Start()
        start.transcription(
            status_callback_url=f"{settings.public_base_url}/voice/transcription",
            language_code=settings.transcription_language,
            track="both_tracks",
            partial_results=False,
            transcription_engine="google",
        )
        vr.append(start)

    # 2) Routing by mode
    dial_kwargs = {
        "answer_on_bridge": True,
        "caller_id": settings.twilio_number,
        "action": f"{settings.public_base_url}/voice/status",
    }
    if settings.enable_recording:
        dial_kwargs.update(
            record="record-from-answer-dual",
            recording_status_callback=f"{settings.public_base_url}/voice/recording",
            recording_status_callback_event="completed",
        )

    dial = Dial(**dial_kwargs)
    if settings.receive_mode == "browser":
        dial.client(settings.client_identity)
    else:
        dial.number(settings.forward_to)
    vr.append(dial)

    return Response(content=str(vr), media_type="application/xml")
```

**Design notes:**
- `answer_on_bridge=True` keeps the caller from hearing "connecting" and stops billing
  before you pick up. It matters for a clean-looking video.
- `caller_id` has to be the Twilio number: CALL-E's number cannot be spoofed.
- `record="record-from-answer-dual"` records **two separate channels** (the agent and
  you). Much better for the video and for debugging than mono.

### Step 6 — Secondary callbacks — ✅ DONE (with tests: 5 passed)

```python
@router.post("/voice/status")        # end of the Dial: duration, final status
@router.post("/voice/recording")     # RecordingUrl, RecordingDuration
@router.post("/voice/transcription") # events: started | content | stopped | error
```

The transcription one receives JSON in the `TranscriptionData` field, shaped as
`{"transcript": "...", "confidence": 0.93}`. Parse it with `json.loads` and store one
`TranscriptSegment` per `content` event.

> The recording URL comes without an extension; append `.mp3` to download it.
> It needs basic auth with `ACCOUNT_SID:AUTH_TOKEN`.

### Step 7 — Browser mode: token and softphone — ❌ DISCARDED (19 Aug 2026)

Not implemented. `forward` mode is already validated end to end and it is the one that
serves the video: a real phone ringing looks better than a softphone in a tab. The saving
(US$0.004/min against US$0.06–0.35/min) is irrelevant at this project's scale, and it
would have required three more Twilio credentials. What follows stays as reference in
case it is ever needed.

`GET /token` returns an access JWT:

```python
token = AccessToken(
    settings.twilio_account_sid,
    settings.twilio_api_key_sid,
    settings.twilio_api_key_secret,
    identity=settings.client_identity,
    ttl=3600,
)
token.add_grant(VoiceGrant(
    outgoing_application_sid=settings.twilio_twiml_app_sid,
    incoming_allow=True,          # essential in order to RECEIVE
))
return {"token": token.to_jwt()}
```

`static/softphone.html`: load the SDK from
`https://sdk.twilio.com/js/voice/releases/2.11.0/twilio.min.js`, do
`const device = new Twilio.Device(token)`, `device.register()` and handle
`device.on("incoming", call => call.accept())`. An "Answer" button and a `<div>` with the
status are enough.

### Step 8 — Dashboard (`/calls`) — ✅ DONE (16 Aug: template string instead of Jinja2, 5s auto-refresh, player through a `/calls/{sid}/recording.mp3` proxy with Twilio auth)

A Jinja2 template with one table: date, duration, status, an `<audio>` player for the
recording, and the transcript expandable. **This is direct material for the three-minute
video** — showing the dashboard filling up while the agent calls is a much stronger demo
than a terminal log.

### Step 9 — Point the number at the webhook — ✅ DONE (16 Aug, pointing at the cloudflared URL; redo it if the tunnel restarts)

`Console → Phone Numbers → your number → Voice Configuration`:

- **A call comes in:** Webhook → `https://YOUR_URL/voice` → HTTP POST
- **Call status changes:** `https://YOUR_URL/voice/status` → HTTP POST

---

## 6. Local development and deployment

### Local — ✅ DONE (with cloudflared instead of ngrok: ngrok v3 requires an account authtoken; `cloudflared tunnel --url http://localhost:8000` gives a public URL with no account)

```bash
uvicorn app.main:app --reload --port 8000
ngrok http 8000
```

Copy the ngrok URL into `PUBLIC_BASE_URL` **and** into the number's Twilio config.
The ngrok URL changes on every restart (unless you pay) — reconfigure both sides.

### Deployment for the demo — ✅ DONE (16 Aug: Render free tier via the `render.yaml` Blueprint, Docker with uv. URL: `https://calle-receiver.onrender.com`, the number's webhooks pointed there through the API. `calls.db` is ephemeral: wiped on every deploy and restart)

Render (free tier) or Fly.io. A minimal `Dockerfile` with `uvicorn` is enough.
The advantage is a stable URL, so the Twilio config never has to be touched again.

> Render's free tier sleeps after 15 minutes of inactivity and takes ~30s to wake.
> Twilio times the webhook out at 15s → **the first call fails**. Before recording
> the video, hit the service with a `curl` to wake it, or use an UptimeRobot cron.

---

## 7. Test plan (in order, without burning CALL-E credits)

1. ✅ **`scripts/test_outbound.py`** — DONE (16 Aug): a 5s `completed` call to the
   Argentine mobile. Geo permissions validated. Does not involve CALL-E.
2. ✅ **Manual inbound call** — DONE (16 Aug): a call from an Argentine landline,
   forwarded to the mobile, `completed` with 16s bridged; a downloadable dual-channel
   recording and 3 transcript segments (both tracks) in `calls.db`.
   Gotcha learned: never call from the same phone that is `FORWARD_TO`.
3. ✅ **First CALL-E call** — DONE (16 Aug): CALL-E dialled the VoIP number without
   being blocked (caller `+18325903283`), `completed` with `task_completed=True`.
4. ✅ **Full flow** — DONE (16 Aug, same call): CALL-E agent → Twilio number → Argentine
   mobile, 18s bridged, dual-channel recording and both transcript tracks in `calls.db`.
5. ✅ **Video rehearsal** — DONE (20 Aug): the trial message does not appear (the account
   is upgraded) and the service was woken with a `curl` immediately before each take.

---

## 8. Known gotchas

| Problem | Cause | Fix |
|---|---|---|
| Error `21215` on the Dial | Argentina not enabled in geo permissions | §0.2 |
| "Trial account" message before the call | Account not upgraded | Top up US$20 |
| Invalid signature on the webhooks | URL rebuilt as `http://` behind the proxy | Use `PUBLIC_BASE_URL` + path |
| The recording will not download | Missing `.mp3` and basic auth | `f"{url}.mp3"` + `(SID, TOKEN)` |
| The transcript never arrives | `statusCallbackUrl` relative or not public | Absolute HTTPS URL |
| First call times out | Free tier asleep | Wake it before the demo |
| CALL-E will not dial the number | VoIP anti-fraud block | Plan B: a real eSIM (§0.1) |
| Calls die 3s after `status=calling` | Provider-side, intermittent, reported as `DECLINED (Hangup by: user)` on a zero-second call the carrier never saw | None found. Four of six calls on 20 Aug died this way; retry, and see ceiling 16 in the app README |

**Compliance note:** recording calls requires consent in several jurisdictions. For test
calls between your own agent and your own phone there is no issue, but do not record
calls to third parties without telling them.

---

## 9. Hackathon delivery checklist

- [x] Uses CALL-E's SDK / API / MCP / CLI / SKILL — REST plus MCP plus a Skill
- [x] Pull request to `CALLE-AI/awesome-phone-call-agents` — [#205](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/205)
- [x] ~3 minute demo video (YouTube or Vimeo) — [youtu.be/WIYBWFslix4](https://youtu.be/WIYBWFslix4), 2:50, unlisted
- [ ] Email tied to the CALL-E account included in the submission
- [ ] Working demo URL (optional but it helps)
- [ ] Submitted before **14 Sep 2026, 23:45 SGT** (= 12:45 on 14 Sep in Argentina)

> The prize categories are "Most Practical Use Case" (US$4,000) and "Most Innovative Use
> Case" (US$3,000), plus 2 mentions of US$1,000 and 5 prizes of US$200 for "Most Valuable
> Feedback". The feedback one is the easiest to win: documenting the problems found during
> the build well is, literally, a prize category. Ours is in `docs/calle-feedback.md`.
