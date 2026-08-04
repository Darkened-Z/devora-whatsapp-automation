const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// ─── CONFIGURATION ────────────────────────────────────────────────────────────

const AUTO_REPLY_MESSAGE = `Hi! I'm currently unavailable but I'll get back to you soon. 🙂`;

// Set to true to reply to group messages as well
const REPLY_TO_GROUPS = false;

// Cooldown in milliseconds — prevents spamming the same contact (default: 5 min)
const REPLY_COOLDOWN_MS = 5 * 60 * 1000;

// ─────────────────────────────────────────────────────────────────────────────

const client = new Client({
    authStrategy: new LocalAuth(), // saves session so you don't re-scan QR every time
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
});

// tracks who we last replied to and when
const lastReplied = new Map();

client.on('qr', (qr) => {
    console.log('\n📱 Scan this QR code with WhatsApp on your phone:\n');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('✅ Authenticated — session saved, no QR needed next time.');
});

client.on('ready', () => {
    console.log('🚀 WhatsApp bot is ready and listening for messages...');
});

client.on('message', async (msg) => {
    // ignore status broadcasts
    if (msg.from === 'status@broadcast') return;

    // optionally skip group messages
    const chat = await msg.getChat();
    if (chat.isGroup && !REPLY_TO_GROUPS) return;

    // cooldown check — don't reply to same contact too frequently
    const now = Date.now();
    const lastTime = lastReplied.get(msg.from) || 0;
    if (now - lastTime < REPLY_COOLDOWN_MS) return;

    lastReplied.set(msg.from, now);

    await msg.reply(AUTO_REPLY_MESSAGE);
    console.log(`↩️  Replied to ${msg.from} at ${new Date().toLocaleTimeString()}`);
});

client.on('auth_failure', (msg) => {
    console.error('❌ Authentication failed:', msg);
});

client.on('disconnected', (reason) => {
    console.log('⚠️  Client disconnected:', reason);
});

client.initialize();
