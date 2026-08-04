const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const fs = require('fs');
const path = require('path');
const net = require('net');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const CONFIG_PATH = path.join(__dirname, 'config.json');

function loadConfig() {
    try {
        return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    } catch {
        return { replyMessage: "Hi! I'm unavailable right now. I'll get back to you soon 🙂", replyToGroups: false, cooldownMinutes: 5, keywordRules: [] };
    }
}

let config = loadConfig();
let qrCodeData = null;
let status = 'loading';
let repliesSent = 0;
let readyAt = null;
const lastReplied = new Map();
const activityLog = [];

// Numbers that have messaged us — powers the marketing bot's reply-detection.
// Persisted so it survives restarts. Shape: { "<number>": "<ISO timestamp>" }
const REPLIES_PATH = path.join(__dirname, 'replies.json');
let inboundReplies = {};
try { inboundReplies = JSON.parse(fs.readFileSync(REPLIES_PATH, 'utf8')); } catch {}

function recordReply(waId) {
    // waId looks like "923001234567@c.us" — keep individual chats only (skip groups).
    if (!waId || !waId.endsWith('@c.us')) return;
    const number = waId.split('@')[0];
    inboundReplies[number] = new Date().toISOString();
    try { fs.writeFileSync(REPLIES_PATH, JSON.stringify(inboundReplies, null, 2)); } catch {}
}

function addLog(msg) {
    const entry = { time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }), message: msg };
    activityLog.unshift(entry);
    if (activityLog.length > 100) activityLog.pop();
    console.log(`[${entry.time}] ${msg}`);
}

// Find a Chromium-based browser to drive. Prefers Chrome; falls back to Edge,
// which ships with every Windows 10/11 machine.
function findBrowser() {
    const local = process.env.LOCALAPPDATA;
    const candidates = [
        local && path.join(local, 'Google', 'Chrome', 'Application', 'chrome.exe'),
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    ].filter(Boolean);
    for (const p of candidates) {
        try { if (fs.existsSync(p)) return p; } catch {}
    }
    return null;
}

const browserPath = findBrowser();
if (!browserPath) {
    console.error('\n  ❌ No compatible browser found (Chrome or Edge).');
    console.error('  Please install Google Chrome from https://www.google.com/chrome');
    console.error('  then start the Auto Replier again.\n');
    process.exit(1);
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: path.join(__dirname, '.session') }),
    puppeteer: {
        headless: true,
        executablePath: browserPath,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    },
});

client.on('qr', async (qr) => {
    status = 'qr';
    qrCodeData = await QRCode.toDataURL(qr);
    addLog('📱 QR code ready — scan with WhatsApp on your phone');
});

client.on('authenticated', () => {
    status = 'authenticated';
    qrCodeData = null;
    addLog('✅ Phone authenticated — starting up...');
});

client.on('ready', () => {
    status = 'ready';
    if (!readyAt) readyAt = Date.now();
    addLog('🚀 Bot is live and listening for messages');
});

client.on('message', async (msg) => {
  try {
    if (msg.from === 'status@broadcast') return;

    // Record the sender so the marketing bot knows this lead replied.
    recordReply(msg.from);

    config = loadConfig();

    const chat = await msg.getChat();
    if (chat.isGroup && !config.replyToGroups) return;

    // Decide which reply to send: first matching keyword rule wins,
    // otherwise fall back to the default message.
    const body = (msg.body || '').toLowerCase();
    let replyText = config.replyMessage || '';
    let matchedKeyword = null;

    if (Array.isArray(config.keywordRules)) {
        for (const rule of config.keywordRules) {
            if (!rule || !rule.reply || !Array.isArray(rule.keywords)) continue;
            const hit = rule.keywords.find(k => k && body.includes(String(k).toLowerCase().trim()));
            if (hit) {
                replyText = rule.reply;
                matchedKeyword = hit;
                break;
            }
        }
    }

    // Nothing to send (e.g. default message left blank and no keyword matched)
    if (!replyText.trim()) return;

    // Cooldown is per-contact-per-reply: the same answer won't repeat-spam a
    // person, but a different keyword answer can still go out right away.
    const now = Date.now();
    const cooldown = (config.cooldownMinutes || 5) * 60 * 1000;
    const cooldownKey = msg.from + '::' + replyText;
    const lastTime = lastReplied.get(cooldownKey) || 0;
    if (now - lastTime < cooldown) return;

    lastReplied.set(cooldownKey, now);
    await msg.reply(replyText);
    repliesSent++;

    try {
        const contact = await msg.getContact();
        const name = contact.pushname || contact.number || msg.from;
        const tag = matchedKeyword ? ` (matched "${matchedKeyword}")` : '';
        addLog(`↩️  Replied to ${name}${tag}`);
    } catch {
        addLog(`↩️  Replied to ${msg.from}`);
    }
  } catch (err) {
    const m = (err && err.message ? err.message : String(err)).split('\n')[0];
    addLog(`⚠️  Could not handle a message: ${m}`);
  }
});

client.on('auth_failure', () => {
    status = 'disconnected';
    addLog('❌ Authentication failed — please restart and scan QR again');
});

client.on('disconnected', (reason) => {
    status = 'disconnected';
    addLog(`⚠️  Disconnected: ${reason}`);
});

// ─── API ──────────────────────────────────────────────────────────────────────

app.get('/api/status', (req, res) => {
    const uptimeMs = readyAt ? Date.now() - readyAt : 0;
    res.json({ status, qr: qrCodeData, logs: activityLog, repliesSent, uptimeMs });
});

app.get('/api/config', (req, res) => {
    res.json(loadConfig());
});

app.post('/api/config', (req, res) => {
    // Merge with existing config so a partial update (e.g. just keyword rules)
    // doesn't wipe out the other settings.
    const updated = loadConfig();

    if (typeof req.body.replyMessage === 'string') updated.replyMessage = req.body.replyMessage;
    if ('replyToGroups' in req.body) updated.replyToGroups = !!req.body.replyToGroups;
    if ('cooldownMinutes' in req.body) updated.cooldownMinutes = Number(req.body.cooldownMinutes) || 5;

    if (Array.isArray(req.body.keywordRules)) {
        // Sanitise: keep only rules that have at least one keyword and a reply.
        updated.keywordRules = req.body.keywordRules
            .map(r => ({
                keywords: Array.isArray(r.keywords)
                    ? r.keywords.map(k => String(k).trim()).filter(Boolean)
                    : [],
                reply: typeof r.reply === 'string' ? r.reply.trim() : '',
            }))
            .filter(r => r.keywords.length > 0 && r.reply.length > 0);
    }

    fs.writeFileSync(CONFIG_PATH, JSON.stringify(updated, null, 2));
    config = updated;
    addLog('⚙️  Settings updated and saved');
    res.json({ ok: true });
});

// ─── Marketing bridge (used by devora_bot.py — localhost only) ──────────────────

// Send a WhatsApp message to a raw number via the live session.
async function sendToNumber(phone, message) {
    if (status !== 'ready') throw new Error('WhatsApp not connected yet — scan the QR first');
    const digits = String(phone || '').replace(/[^0-9]/g, '');
    if (!digits) throw new Error('empty phone number');
    const numberId = await client.getNumberId(digits);   // also verifies it's on WhatsApp
    if (!numberId) throw new Error('number is not on WhatsApp');
    await client.sendMessage(numberId._serialized, message);
}

app.post('/api/send', async (req, res) => {
    const { phone, message } = req.body || {};
    if (!phone || !message) return res.status(400).json({ sent: false, error: 'phone and message required' });
    try {
        await sendToNumber(phone, message);
        addLog(`📤 Sent campaign message to ${phone}`);
        res.json({ sent: true });
    } catch (err) {
        const m = (err && err.message) ? err.message : String(err);
        res.json({ sent: false, error: m });
    }
});

app.get('/api/replies', (req, res) => {
    res.json({ numbers: Object.keys(inboundReplies), replies: inboundReplies });
});

// ─── START ────────────────────────────────────────────────────────────────────

const PORT = 3000;

// Probe whether something is already listening on the port BEFORE we start the
// WhatsApp client. This prevents a second (accidental double-click) launch from
// ever calling client.initialize() — which would spawn a second Chrome against
// the shared .session folder and corrupt the saved login.
function isPortInUse(port) {
    return new Promise((resolve) => {
        const socket = net.connect({ port, host: '127.0.0.1' });
        socket.on('connect', () => { socket.destroy(); resolve(true); });
        socket.on('error', () => resolve(false));
        socket.setTimeout(1500, () => { socket.destroy(); resolve(false); });
    });
}

// Start (or restart) the WhatsApp client, recovering from transient startup
// errors (WhatsApp Web occasionally throws during injection) instead of letting
// them crash the whole app with a raw stack trace.
// The port-probe guarantees we are the only running instance, so any leftover
// browser lock in the session folder must be stale (from a previous unclean
// shutdown / PC crash). Clearing it prevents a "browser is already running" error.
function clearStaleLocks() {
    try {
        const sessDir = path.join(__dirname, '.session', 'session');
        for (const f of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
            try { fs.rmSync(path.join(sessDir, f), { force: true }); } catch {}
        }
    } catch {}
}

let initAttempts = 0;
function startClient() {
    initAttempts++;
    client.initialize().catch(async (err) => {
        const m = (err && err.message ? err.message : String(err)).split('\n')[0];
        addLog(`⚠️  Startup hiccup: ${m}`);
        // Close the half-open browser from this failed attempt so its session
        // lock is released — otherwise every retry hits "browser already running".
        try { await client.destroy(); } catch {}
        clearStaleLocks();
        if (initAttempts < 6) {
            const delaySec = Math.min(30, initAttempts * 5);
            addLog(`🔄 Retrying in ${delaySec}s (attempt ${initAttempts} of 5)...`);
            setTimeout(startClient, delaySec * 1000);
        } else {
            addLog('❌ Could not connect after several tries. Close this window and run start.bat again.');
        }
    });
}

// Last-resort safety nets: keep the app alive on unexpected errors so the
// dashboard stays up and the bot can recover, rather than dying silently.
process.on('unhandledRejection', (reason) => {
    const m = (reason && reason.message ? reason.message : String(reason)).split('\n')[0];
    addLog(`⚠️  Recovered from a background error: ${m}`);
});
process.on('uncaughtException', (err) => {
    const m = (err && err.message ? err.message : String(err)).split('\n')[0];
    addLog(`⚠️  Recovered from an error: ${m}`);
});

isPortInUse(PORT).then((inUse) => {
    if (inUse) {
        console.log(`\n  ⚠️  The Auto Replier is already running!`);
        console.log(`  Open your browser to  →  http://localhost:${PORT}`);
        console.log(`\n  (You can close this window.)\n`);
        process.exit(1);
        return;
    }

    // Bind to localhost only — the /api/send endpoint can message through your
    // number, so it must never be reachable from the internet (e.g. on a VPS).
    const httpServer = app.listen(PORT, '127.0.0.1', () => {
        console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
        console.log(`  WhatsApp Auto Replier`);
        console.log(`  Dashboard → http://localhost:${PORT}`);
        console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);

        addLog('⏳ Starting WhatsApp client...');
        clearStaleLocks();
        startClient();
    });

    // Safety net in case the port is taken in the split second after probing.
    httpServer.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
            console.log(`\n  ⚠️  The Auto Replier is already running!`);
            console.log(`  Open your browser to  →  http://localhost:${PORT}\n`);
        } else {
            console.error('Server error:', err);
        }
        process.exit(1);
    });
});
