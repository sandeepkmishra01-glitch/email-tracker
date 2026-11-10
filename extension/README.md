# Gmail extension

1. Chrome → `chrome://extensions` → enable Developer mode → **Load unpacked** → select this folder.
2. Open the extension's **Options**: enter the tracker server URL and the `TRACKER_API_KEY`, then Save (approve the permission prompt).
3. Reload Gmail. Anything you send (Send button or Ctrl/Cmd+Enter) is tracked automatically.

Notes: one tracking token per sent message (all To/Cc/Bcc recipients share it). If the server is unreachable the email is sent untracked. Gmail's DOM changes occasionally; selectors are in `content.js`.
