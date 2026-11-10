// Content scripts are bound by page CORS, so the request to the tracker is made here.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "track") return;
  (async () => {
    try {
      const { serverUrl, apiKey } = await chrome.storage.local.get(["serverUrl", "apiKey"]);
      if (!serverUrl || !apiKey) return sendResponse({ ok: false, error: "Not configured" });
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), 6000);
      const res = await fetch(serverUrl.replace(/\/+$/, "") + "/api/track", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(msg.payload),
        signal: ctl.signal,
      });
      clearTimeout(timer);
      if (!res.ok) return sendResponse({ ok: false, error: "HTTP " + res.status });
      sendResponse({ ok: true, data: await res.json() });
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
  })();
  return true; // async response
});
