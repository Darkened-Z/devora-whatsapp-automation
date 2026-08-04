# Devora WhatsApp Automation

Two tools that share one free WhatsApp connection (via [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js)):

1. **Auto Replier** (`server.js`) — a Node app with a web dashboard that auto-replies to incoming WhatsApp messages (default + keyword rules). It also acts as a **local bridge** that holds the WhatsApp session.
2. **Devora Marketing Bot** (`devora_bot.py`) — a Python drip campaign that pulls restaurant leads from Monday.com, messages them (Intro → Day 3 → Day 7), auto-stops anyone who replies, and writes status back to Monday. Sends through the Auto Replier — **no paid gateway**.

## Quick start — Auto Replier
```bash
npm install
node server.js        # or double-click start.bat
```
Open `http://localhost:3000`, scan the QR once. Done.

## Quick start — Marketing Bot
```bash
pip install requests python-dotenv
cp .env.example .env   # add your Monday API key
python devora_bot.py   # Auto Replier must be running + "Live"
```
See [SETUP_GUIDE.md](SETUP_GUIDE.md) for the full walkthrough.

## How they connect
The Auto Replier exposes two **localhost-only** endpoints the bot uses:
- `POST /api/send` `{phone, message}` — send via the live session
- `GET /api/replies` — numbers that have messaged back (for reply-detection)

The server binds to `127.0.0.1` so these are never internet-reachable.

## Building the Windows installer
`installer.iss` (Inno Setup) bundles a self-contained installer. It needs `node.exe`
in the project root first (excluded from git — copy it from your system Node):
```bash
cp "$(dirname "$(which node)")/node.exe" .
```
Then compile `installer.iss` with Inno Setup → `installer-output/WhatsAppAutoReplier-Setup.exe`.

## ⚠️ Note on WhatsApp automation
This uses whatsapp-web.js (unofficial WhatsApp Web). Cold/bulk outreach can get a
number banned — the bot throttles (daily cap, randomized delays, business hours),
but keep messages personal and honor opt-outs. Not for spam.

## Stack
Node.js · Express · whatsapp-web.js · Python · Monday.com API · Inno Setup
