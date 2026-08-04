# Devora Bot — Setup Guide
**Total setup time: ~30 minutes**

---

## What this bot does

Runs every morning, checks your Monday.com CRM, and:
- **Detects replies first** — any restaurant that messaged you back is auto-marked "Replied" and taken **out** of the sequence (no more follow-ups to warm leads)
- Sends **Intro message** to new restaurant leads
- Sends **Follow-up 1** on day 3 (only if they haven't replied)
- Sends **Follow-up 2** on day 7 (only if still no reply)
- Sends at most **25 messages/day** with **random 30–90s gaps**, business hours only — to stay under WhatsApp's spam radar
- Updates the "Next step" column in Monday.com automatically
- Logs everything to `devora_bot.log`

---

## Step 1 — Install Python

1. Go to [python.org/downloads](https://python.org/downloads)
2. Download Python 3.11 or newer
3. **Important:** Check "Add Python to PATH" during install
4. Open Command Prompt and verify: `python --version`

---

## Step 2 — Install dependencies

Open Command Prompt in the folder where you saved `devora_bot.py` and run:

```
pip install requests python-dotenv
```

---

## Step 3 — Get your Monday.com API key

1. Log in to monday.com
2. Click your **profile picture** (top right) → **Administration**
3. Go to **API** (left sidebar)
4. Click **Copy** under "Personal API Token"
5. Paste it into `.env` as `MONDAY_API_KEY`

---

## Step 4 — Start the Auto Replier (your free WhatsApp bridge)

> **What is this?** The Auto Replier (the Node app / `start.bat`) holds your
> WhatsApp session and does the actual sending — for free, through your own
> number. No paid gateway, no new number, no Meta verification. The Devora bot
> just tells it who to message.

1. Double-click **`start.bat`** — the dashboard opens at `http://localhost:3000`
2. **Scan the QR code** with your WhatsApp phone (Linked Devices → Link a Device). One time only.
3. Wait until the status badge shows **"Live"**.
4. **Leave it running.** It must stay open for the Devora bot to send. (Tip: run `install-autostart.bat` so it starts with the PC.)

That's it — no keys to copy. The bot talks to it automatically at `http://127.0.0.1:3000`.

---

## Step 5 — Create your `.env` file

1. In the same folder as `devora_bot.py`, copy `.env.example` → rename to `.env`
2. Open `.env` in Notepad and fill in your values:
   ```
   MONDAY_API_KEY=your_monday_key
   YOUR_WHATSAPP_NUMBER=923001234567
   ```
   (`WA_BRIDGE_URL` is already set to the local Auto Replier — leave it as-is.)
3. Save and close

---

## Step 6 — Test run

Make sure the Auto Replier is running and shows **"Live"**, then open Command
Prompt in the bot folder and run:

```
python devora_bot.py
```

You should see output like:
```
2026-08-04 09:00:00  INFO      Devora Bot starting — 04 Aug 2026 09:00
2026-08-04 09:00:01  INFO      Fetched 24 leads from Monday.com
2026-08-04 09:00:01  INFO        📨  SEND  Sample Restaurant (923001234567) — intro
2026-08-04 09:00:04  INFO        ✅  SENT  Sample Restaurant — CRM updated
...
```

Check your WhatsApp phone — you should see the messages going out.

> If you see **"Can't reach the WhatsApp bridge"** or **"bridge not ready"**,
> the Auto Replier isn't running or isn't scanned yet. Fix that first.

---

## Step 7 — Automate with Windows Task Scheduler

So the bot runs every morning without you doing anything:

1. Press **Win + S**, search **"Task Scheduler"**, open it
2. Click **"Create Basic Task"** (right panel)
3. Name: `Devora WhatsApp Bot`
4. Trigger: **Daily** → Set time to `09:00 AM`
5. Action: **Start a program**
   - Program: `python`
   - Arguments: `C:\path\to\your\devora_bot.py`
   - Start in: `C:\path\to\your\folder\`
6. Finish → right-click the task → **Run** to test it once

> **Tip:** Change `C:\path\to\your\` to the actual folder path where you saved the files.

---

## How the sequence works

| Day | What happens |
|-----|-------------|
| Day 0 | Bot detects new lead → sends **Intro** → notes it in CRM |
| Day 3 | Bot sees intro was sent 3 days ago, no follow-up yet → sends **Follow-up 1** |
| Day 7 | Bot sees follow-up 1 was sent 4 days ago → sends **Follow-up 2** (final) |
| Day 7+ | Lead marked "done" in state file. No more messages sent. |
| **Any day** | **If the restaurant replies, their sequence stops immediately** — no follow-ups to someone who's already talking to you. |

State is stored in `devora_state.json` in the same folder.

---

## Reply detection (so you don't spam warm leads)

The Auto Replier sees every incoming WhatsApp message and records who messaged
you. Before sending anything, each run asks it who has replied. If a lead's
number is in that list, the bot:
1. Marks them `replied` + `done` in the state file
2. Writes "💬 Replied — sequence stopped" to their Monday "Next step"
3. Never sends them another automated message — **you take over personally**

> Matching ignores formatting, so `+92 300 1234567`, `0300 1234567`, and
> `923001234567` all match the same restaurant.

Because the Auto Replier is always listening, reply-detection is effectively
real-time — a lead who answers won't get tomorrow's follow-up.

---

## Anti-ban throttling

Cold WhatsApp is the #1 way to get a number banned. The bot limits the blast:

| Setting | Default | What it does |
|---------|---------|--------------|
| `DAILY_CAP` | 25 | Stops after N messages/day; the rest continue tomorrow |
| `MIN_DELAY_SEC` / `MAX_DELAY_SEC` | 30 / 90 | Random human-like gap between messages |
| `SEND_START_HOUR` / `SEND_END_HOUR` | 9 / 21 | Only sends during business hours |

All optional — override any of them in `.env`. Start conservative (cap 20–25/day)
on a fresh number and raise it slowly over a couple of weeks.

> ⚠️ Even with throttling, cold WhatsApp outreach can still get a number
> flagged. Keep messages personal, honor opt-outs, and don't reuse the same
> copy-paste at high volume.

---

## Manual overrides

**Skip a lead:** Add the word `landline` or `not on whatsapp` to their "Next step" in Monday.com — the bot will skip them.

**Reset a lead:** Delete their entry from `devora_state.json` (open in Notepad) — the bot will start their sequence fresh.

**Stop the bot:** Delete or disable the Task Scheduler task.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "MONDAY_API_KEY not set" | Check your `.env` file is saved and in the right folder |
| "Can't reach the WhatsApp bridge" | Start the Auto Replier (`start.bat`) first — it must be running |
| "bridge not ready" | Open the Auto Replier dashboard and scan the QR until it shows "Live" |
| "number is not on WhatsApp" | That lead's number isn't on WhatsApp — bot skips it, nothing to fix |
| "ModuleNotFoundError" | Run `pip install requests python-dotenv` again |
| Bot runs but sends nothing | Check `devora_bot.log`; confirm the Auto Replier shows "Live" |
| Monday.com not updating | Check your API key has write permissions |

---

## Costs

| Item | Cost |
|------|------|
| WhatsApp sending (via the Auto Replier / whatsapp-web.js) | **Free** |
| Python | Free |
| Monday.com | Your existing plan |
| Always-on host to run it | Free (a PC you have, or a free Oracle Cloud VM) |
| **Total** | **$0/month** |

---

## Files in this package

| File | Purpose |
|------|---------|
| `devora_bot.py` | Main automation script (drip + reply-detection) |
| `server.js` + `start.bat` | The Auto Replier — your free WhatsApp bridge (must be running) |
| `.env.example` | Template for your Monday key |
| `SETUP_GUIDE.md` | This file |
| `devora_restaurant_pitch_kit.md` | Message templates reference |
| `devora_restaurant_onepager.html` | Visual flyer for restaurants |
