#!/usr/bin/env python3
"""
Devora WhatsApp Automation Bot
================================
Reads restaurant leads from Monday.com, sends the right message
(Intro → Follow-up 1 on day 3 → Follow-up 2 on day 7) through your own
WhatsApp via the local whatsapp-web.js bridge (the Auto Replier Node app),
and updates Monday.com with the status. 100% free — no paid gateway.

Run daily via Windows Task Scheduler (see SETUP_GUIDE.md).
The Auto Replier (start.bat) must be running — it holds the WhatsApp session.
"""

import os
import sys
import json
import time
import random
import logging
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Emoji/Urdu-safe console output — a stock Windows console is cp1252 and would
# otherwise throw UnicodeEncodeError on the emojis in our log lines.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "devora_bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
MONDAY_API_KEY   = os.getenv("MONDAY_API_KEY")        # Monday.com API v2 key
MONDAY_BOARD_ID  = 5029511591
# The local whatsapp-web.js bridge = the Auto Replier Node app (server.js).
WA_BRIDGE_URL    = os.getenv("WA_BRIDGE_URL", "http://127.0.0.1:3000")
YOUR_WHATSAPP    = os.getenv("YOUR_WHATSAPP_NUMBER")  # Your number for Message #3 CTA

STATE_FILE = Path(__file__).parent / "devora_state.json"

# ── Throttling / anti-ban safety (override in .env if needed) ────────────────
DAILY_CAP       = int(os.getenv("DAILY_CAP", "25"))        # max messages sent per day
MIN_DELAY_SEC   = int(os.getenv("MIN_DELAY_SEC", "30"))    # min gap between messages
MAX_DELAY_SEC   = int(os.getenv("MAX_DELAY_SEC", "90"))    # max gap between messages
SEND_START_HOUR = int(os.getenv("SEND_START_HOUR", "9"))   # don't send before this hour (24h)
SEND_END_HOUR   = int(os.getenv("SEND_END_HOUR", "21"))    # don't send after this hour (24h)

# Active pipeline groups to process (ignore Won, Lost, Archive)
ACTIVE_GROUPS = {
    "topics",           # Lead
    "group_mm4pz6ab",   # Qualified
    "group_mm4p6rw1",   # Proposal Sent
    "group_mm4pbhkv",   # Negotiation
}

# ── Message Templates ─────────────────────────────────────────────────────────
MSG_INTRO = """Assalam o Alaikum! 👋

Kya aap ka restaurant billing manually hoti hai? Ya end of day report ke liye aapko khud calculate karna parta hai?

Hamne dekha hai ke Faisalabad ke zyada tar restaurants mein 3 common masle hain:
❌ Billing mein galtiyan (especially rush hours mein)
❌ Din bhar ki sales ka koi record nahi
❌ Stock khatam hojata hai — pata nahi chalta

Hamara naam *Devora* hai — ek AI-powered restaurant & POS software jo in sab cheezon ko automatically handle karta hai. Billing, inventory, daily sales report, cash count, aur staff attendance — sab ek jagah.

Aur seedhi baat — aap ko koi demo charge nahi. Hum chahte hain aap khud dekhen ke yeh aap ke restaurant ke liye kaam karta hai ya nahi.

Kya main aap ko 15 minute ka free demo de sakta hoon? 🙏"""

MSG_FOLLOWUP1 = """Assalam o Alaikum! Zeeshan here from *Devora* 👋

Pichle hafte message kiya tha — shayad busy the, koi baat nahi!

Ek cheez share karna chahta tha: Devora ka AI bot automatically aap ko suggest karta hai ke kaunsa item zyada bik raha hai, kab rush aata hai, aur daily cash count bhi khud karta hai — owner ko manually kuch count nahi karna parta.

Agar 15 min nikal saken toh ek free demo schedule kar sakte hain. Koi commitment nahi — bas dekh len. 😊"""

MSG_FOLLOWUP2 = """Assalam o Alaikum! Last message — promise 😄

*Devora* ki taraf se — hum abhi Faisalabad ke kuch local restaurants ko free demo de rahe hain aur unke liye pehle month free setup kar rahe hain.

Agar kabhi bhi software ke baare mein baat karni ho, main yahan hoon. Apna time waste nahi karunga — seedha 15-min demo hoga aur aap khud decide karenge.

WhatsApp pe reply karen ya call karen: {phone} 📞"""


# ── State Management ──────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def days_since(date_str: str | None) -> int | None:
    """Return days since a 'YYYY-MM-DD' date string, or None if not set."""
    if not date_str:
        return None
    d = date.fromisoformat(date_str)
    return (date.today() - d).days


# ── Monday.com API ────────────────────────────────────────────────────────────
MONDAY_URL = "https://api.monday.com/v2"
MONDAY_HEADERS = {
    "Authorization": MONDAY_API_KEY,
    "Content-Type": "application/json",
    "API-Version": "2024-01",
}


def fetch_leads() -> list[dict]:
    """Fetch all active restaurant leads from Monday.com."""
    query = """
    query GetLeads($boardId: [ID!]!) {
      boards(ids: $boardId) {
        groups {
          id
          title
          items_page(limit: 200) {
            items {
              id
              name
              column_values(ids: ["phone_mm4pmmrs", "text_mm4pq5qr"]) {
                id
                text
              }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        MONDAY_URL,
        json={"query": query, "variables": {"boardId": [str(MONDAY_BOARD_ID)]}},
        headers=MONDAY_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        raise RuntimeError(f"Monday.com API error: {data['errors']}")

    leads = []
    for group in data["data"]["boards"][0]["groups"]:
        if group["id"] not in ACTIVE_GROUPS:
            continue
        for item in group["items_page"]["items"]:
            col = {cv["id"]: cv["text"] for cv in item["column_values"]}
            phone     = col.get("phone_mm4pmmrs", "") or ""
            next_step = col.get("text_mm4pq5qr", "")  or ""

            phone = phone.strip().replace(" ", "")
            leads.append({
                "id":        item["id"],
                "name":      item["name"],
                "phone":     phone,
                "next_step": next_step,
                "group":     group["id"],
            })
    return leads


def update_next_step(item_id: str, text: str):
    """Write a status note to the 'Next step' column in Monday.com."""
    mutation = """
    mutation UpdateNextStep($boardId: ID!, $itemId: ID!, $value: String!) {
      change_column_value(
        board_id: $boardId,
        item_id: $itemId,
        column_id: "text_mm4pq5qr",
        value: $value
      ) { id }
    }
    """
    requests.post(
        MONDAY_URL,
        json={
            "query": mutation,
            "variables": {
                "boardId": str(MONDAY_BOARD_ID),
                "itemId":  item_id,
                "value":   json.dumps(text),
            },
        },
        headers=MONDAY_HEADERS,
        timeout=30,
    )


# ── WhatsApp (local whatsapp-web.js bridge — free) ────────────────────────────
def send_whatsapp(phone: str, message: str) -> bool:
    """Send a WhatsApp message via the local bridge (the Auto Replier Node app)."""
    phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    if not phone:
        return False
    try:
        resp = requests.post(
            f"{WA_BRIDGE_URL}/api/send",
            json={"phone": phone, "message": message},
            timeout=60,   # sending through WhatsApp Web can take a few seconds
        )
        result = resp.json()
        if not result.get("sent"):
            log.error(f"Bridge could not send to {phone}: {result.get('error', 'unknown')}")
        return bool(result.get("sent"))
    except Exception as e:
        log.error(f"WhatsApp bridge error (is the Auto Replier running?): {e}")
        return False


def norm_number(raw: str) -> str:
    """Reduce a phone number to its last 10 digits for reliable matching —
    ignores country code, +, spaces, dashes and formatting differences."""
    digits = "".join(c for c in (raw or "") if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def fetch_replied_numbers() -> set[str]:
    """Ask the local bridge which numbers have messaged us back. Any lead in
    this set has replied, so we stop their sequence."""
    numbers: set[str] = set()
    try:
        resp = requests.get(f"{WA_BRIDGE_URL}/api/replies", timeout=30)
        data = resp.json()
        for n in data.get("numbers", []):
            nn = norm_number(str(n))
            if nn:
                numbers.add(nn)
    except Exception as e:
        log.error(f"Could not fetch replies from bridge: {e}")
    return numbers


# ── Skip Conditions ───────────────────────────────────────────────────────────
SKIP_KEYWORDS = ["landline", "not on whatsapp", "number not on whatsapp", "hotel script pending"]

def should_skip(lead: dict) -> str | None:
    """Return a reason string if this lead should be skipped, else None."""
    if not lead["phone"]:
        return "no phone number"
    ns = lead["next_step"].lower()
    for kw in SKIP_KEYWORDS:
        if kw in ns:
            return f"skip keyword: '{kw}'"
    return None


# ── Sequence Logic ────────────────────────────────────────────────────────────
def determine_action(lead: dict, state: dict) -> str | None:
    """
    Return 'intro' | 'followup1' | 'followup2' | None.

    State entry per lead:
      { "intro": "YYYY-MM-DD", "followup1": null, "followup2": null, "done": false }
    """
    entry = state.get(lead["id"], {})

    if entry.get("done"):
        return None  # Full sequence already complete

    intro_date     = entry.get("intro")
    followup1_date = entry.get("followup1")
    followup2_date = entry.get("followup2")

    # Never contacted
    if not intro_date:
        ns = lead["next_step"].lower()
        # Only send intro if the next step says to (or entry is blank)
        if "send whatsapp intro #1" in ns or "intro #1" in ns or not ns:
            return "intro"
        # If next step says intro already sent (manual update), infer intro was sent today
        if "intro sent" in ns:
            # Update state to track from today so follow-ups work
            entry["intro"] = date.today().isoformat()
            state[lead["id"]] = entry
            return None  # Don't double-send; follow-up logic will kick in tomorrow

    # Intro sent — check follow-ups
    d = days_since(intro_date)
    if followup2_date:
        return None  # Sequence complete; mark done
    if followup1_date:
        if days_since(followup1_date) >= 4:
            return "followup2"
    elif d is not None and d >= 3:
        return "followup1"

    return None


# ── Main Run ──────────────────────────────────────────────────────────────────
def run():
    log.info("=" * 55)
    log.info(f"  Devora Bot starting — {datetime.now().strftime('%d %b %Y %H:%M')}")
    log.info("=" * 55)

    if not MONDAY_API_KEY:
        log.error("MONDAY_API_KEY not set in .env — aborting.")
        return

    # The WhatsApp bridge (Auto Replier Node app) must be running AND connected.
    try:
        st = requests.get(f"{WA_BRIDGE_URL}/api/status", timeout=10).json()
        if st.get("status") != "ready":
            log.error(f"WhatsApp bridge not ready (status: {st.get('status')}). "
                      f"Open the Auto Replier, scan the QR, then re-run.")
            return
    except Exception:
        log.error(f"Can't reach the WhatsApp bridge at {WA_BRIDGE_URL}. "
                  f"Start the Auto Replier (start.bat) first, then re-run.")
        return

    state = load_state()
    today_str = date.today().isoformat()

    # Daily send counter — resets each day, survives multiple runs on the same day.
    meta = state.get("__meta__", {})
    if meta.get("date") != today_str:
        meta = {"date": today_str, "sent_today": 0}
    state["__meta__"] = meta

    leads = fetch_leads()
    log.info(f"Fetched {len(leads)} leads from Monday.com")

    # ── Step 1: detect replies and STOP those sequences ──────────────────────
    replied_numbers = fetch_replied_numbers()
    log.info(f"Found {len(replied_numbers)} numbers with incoming replies")

    replied_count = 0
    for lead in leads:
        entry = state.get(lead["id"], {})
        if entry.get("done"):
            continue
        if norm_number(lead["phone"]) in replied_numbers:
            entry = state.setdefault(lead["id"], {"intro": None, "followup1": None, "followup2": None, "done": False})
            entry["name"]    = lead["name"]
            entry["replied"] = True
            entry["done"]    = True
            save_state(state)
            update_next_step(lead["id"], f"💬 Replied {date.today().strftime('%d-%b')} — sequence stopped. Follow up personally!")
            log.info(f"  💬  REPLY {lead['name']} — replied, sequence stopped")
            replied_count += 1

    # ── Step 2: only send during business hours ──────────────────────────────
    now_hour = datetime.now().hour
    if not (SEND_START_HOUR <= now_hour < SEND_END_HOUR):
        log.info(f"  ⏰  Outside send window ({SEND_START_HOUR:02d}:00–{SEND_END_HOUR:02d}:00). "
                 f"Reply-check done; will send at the next scheduled run.")
        log.info("-" * 55)
        log.info(f"  Done. Replies: {replied_count} | Sent: 0 (outside window)")
        log.info("=" * 55 + "\n")
        return

    # ── Step 3: send scheduled messages (capped + randomized delays) ──────────
    sent_count    = 0
    skipped_count = 0

    for lead in leads:
        name = lead["name"]
        entry = state.get(lead["id"], {})
        if entry.get("done"):
            continue

        if meta["sent_today"] >= DAILY_CAP:
            log.info(f"  ⏸  Daily cap reached ({DAILY_CAP}/day). Remaining leads continue tomorrow.")
            break

        # Skip landlines, no-WA numbers, etc.
        reason = should_skip(lead)
        if reason:
            log.info(f"  ⏭  SKIP  {name} ({reason})")
            skipped_count += 1
            continue

        action = determine_action(lead, state)
        if not action:
            continue

        # Build the message
        if action == "intro":
            msg = MSG_INTRO
            crm_note = f"Intro sent {date.today().strftime('%d-%b')} via WhatsApp. Follow up day 3 if no reply."
        elif action == "followup1":
            msg = MSG_FOLLOWUP1
            crm_note = f"Follow-up 1 sent {date.today().strftime('%d-%b')} via WhatsApp. Follow up day 7 if no reply."
        else:  # followup2
            msg = MSG_FOLLOWUP2.format(phone=YOUR_WHATSAPP or "[your number]")
            crm_note = f"Full sequence complete. Last message sent {date.today().strftime('%d-%b')}. No reply = move to cold."

        log.info(f"  📨  SEND  {name} ({lead['phone']}) — {action}")
        success = send_whatsapp(lead["phone"], msg)

        if success:
            entry = state.setdefault(lead["id"], {"intro": None, "followup1": None, "followup2": None, "done": False})
            entry["name"]  = name
            entry[action]  = today_str
            if action == "followup2":
                entry["done"] = True
            meta["sent_today"] += 1
            save_state(state)
            update_next_step(lead["id"], crm_note)
            log.info(f"  ✅  SENT  {name} — CRM updated ({meta['sent_today']}/{DAILY_CAP} today)")
            sent_count += 1

            # Randomized, human-like delay before the next message (anti-ban)
            delay = random.randint(MIN_DELAY_SEC, MAX_DELAY_SEC)
            log.info(f"      ⏳ waiting {delay}s before next message…")
            time.sleep(delay)
        else:
            log.error(f"  ❌  FAIL  {name} — message not sent, will retry next run")

    log.info("-" * 55)
    log.info(f"  Done. Replies: {replied_count} | Sent: {sent_count} | "
             f"Skipped: {skipped_count} | Today: {meta['sent_today']}/{DAILY_CAP}")
    log.info("=" * 55 + "\n")


if __name__ == "__main__":
    run()
