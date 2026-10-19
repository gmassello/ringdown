# Pending — after CALL-E

CALL-E closed on **14 September 2026**; the winners were announced and Ringdown was not one of them
(see [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md)). What follows is what the hackathon left
running.

## Billable resources

This repository never had a `PENDING.md`, so this list was reconstructed from what the repo shows —
`render.yaml`, the deploy and keepalive workflows, `## Commands`, and the environment variables the
code reads. **It may be incomplete**: anything provisioned by hand in a provider console and never
written down here is not on it.

| Resource | Where it is declared | Cost | Status |
|---|---|---|---|
| Render web service `calle-receiver` | `render.yaml:2-5` (plan: free) | Free tier; spends monthly instance hours while awake | **kept alive** — it is linked from the README; answered 200 in 21.9 s on 2026-10-19 (cold start) |
| GitHub Actions `keepalive` cron | `.github/workflows/keepalive.yml` | Free on a public repo; its purpose is to spend Render's instance hours | **deleted 2026-10-19** — had been throttled by GitHub to roughly every 5 h instead of every 5 min |
| Twilio US phone number | `render.yaml:7-12` (`TWILIO_NUMBER`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`) | **Recurring monthly charge per number**, plus per-minute on any call | **unverified** — not visible from this repo; check the Twilio console |
| Gemini API key | `GEMINI_API_KEY`, read by `ringdown/suggest.py` | Pay-per-use; no charge while idle | **unverified** — the key lives outside the repo |
| CALL-E credits | the hackathon account | Prepaid, no recurring charge | no action |
| GitHub Pages | `.github/workflows/deploy.yml` | Free | keep — it is the project's public page |

## What to do with each

Nothing below has been run. **Each deletion needs its own confirmation; none of it can be undone.**

1. **Keep the Render service and the Pages site.** Both are linked from the root README and from the
   project page, and the README's own portfolio value depends on the sample call at
   `calle-receiver.onrender.com/demo` answering. Free tier, no charge.

2. ~~**Delete the keepalive workflow.**~~ **Done on 2026-10-19.** Its own comment asked for it:
   *"Staying awake around the clock also
   spends most of the free tier's monthly instance hours, so delete this workflow once the receiver
   stops needing an audience."* That audience left five weeks ago, and GitHub has throttled the cron
   to roughly every five hours anyway — so it is burning instance hours without actually keeping the
   service warm. The README already documents the 30-second wake.

   ```bash
   git rm .github/workflows/keepalive.yml
   ```

   The sentence in `README.md:232` about giving it thirty seconds to wake stays true, and becomes
   the only story.

3. **Check the Twilio number in the console.** It is the one resource here with a real recurring
   charge, and it cannot be verified from this repository. If the bridge is no longer needed, release
   the number; if the demo should keep working, it has to stay.

4. **Revoke the keys regardless of what stays alive**: the Twilio auth token and the Gemini API key.
   Both were issued for a hackathon that is over. Revoking them does not take the demo down — the
   demo call is a recording; only a new outbound bridge would need the Twilio credentials.

## Not resolved, and out of our hands

- Nothing. The upstream PR that was open on the last day, `CALLE-AI/awesome-phone-call-agents#512`,
  was **merged on 14 September at 08:26 UTC**.
