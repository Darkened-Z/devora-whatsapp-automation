========================================
  WhatsApp Auto Replier
========================================

WHAT IT DOES
------------
Automatically replies to incoming WhatsApp messages. You can set one
default reply, plus keyword-based replies (e.g. anyone who says "price"
gets your pricing message).


HOW TO START
------------
1. Double-click  start.bat
2. A dashboard opens in your browser (http://localhost:3000)
3. The first time, scan the QR code:
      Phone WhatsApp -> Menu -> Linked Devices -> Link a Device
4. That's it. The bot is now replying.

Keep the black window open while it runs. Close it to stop the bot.
(After the first scan, you won't need to scan again - the login is saved.)


THE DASHBOARD
-------------
- Status         : shows if the bot is Live, needs a QR scan, etc.
- Default reply  : the message sent when nothing else matches.
                   Leave it blank to ONLY reply to keywords.
- Cooldown       : how long to wait before sending the same person the
                   same reply again (stops spam).
- Reply to groups: on/off for group chats.
- Keyword Auto-Replies:
      Add rules like  keywords: price, cost   ->   reply: "Our price is..."
      Rules are checked top to bottom - the first match wins.

Click Save after changing anything.


START AUTOMATICALLY WHEN THE PC TURNS ON  (optional)
----------------------------------------------------
- To enable : double-click  install-autostart.bat
- To disable: double-click  uninstall-autostart.bat


IMPORTANT NOTES
---------------
- This uses your normal WhatsApp number via WhatsApp Web.
- Keep replies normal and human. Sending spam or bulk marketing can get
  a number banned by WhatsApp. Personal / customer-service use is fine.
- The .session folder contains your WhatsApp login - do NOT share it.


TROUBLESHOOTING
---------------
- "already running" message: it's already open. Just go to
  http://localhost:3000 in your browser.
- Bot stopped replying: close the window and run start.bat again.
- Need to log in with a different phone: delete the .session folder,
  then run start.bat and scan again.
