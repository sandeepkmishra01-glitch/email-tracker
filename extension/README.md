# Gmail + Outlook on the web extension

Works on `mail.google.com`, `outlook.office.com`, `outlook.office365.com` and `outlook.live.com`.

1. Chrome/Edge → `chrome://extensions` (or `edge://extensions`) → enable Developer mode → **Load unpacked** → select this folder.
2. Open the extension's **Options**: enter the tracker server URL and the `TRACKER_API_KEY`, then Save (approve the permission prompt).
3. Reload Gmail / Outlook. Anything you send (Send button or Ctrl/Cmd+Enter) is tracked automatically. A toast in the bottom-left corner confirms it.

Notes: one tracking token per sent message (all To/Cc/Bcc recipients share it). If the server is unreachable the email is sent untracked.

The mail client's DOM changes occasionally. Selectors live in per-client adapters (`gmail`, `outlook`) at the top of `content.js`. If Outlook shows "NOT tracked" or never shows a toast, open DevTools → Console and look for `[Email Tracker]` lines. Outlook's selectors are based on aria-labels (`Send`, `Message body`, `Add a subject`, `To`/`Cc`/`Bcc`), so a UI language other than English needs those strings changed.
