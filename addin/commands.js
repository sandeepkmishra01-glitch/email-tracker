// Runs when you click Send in Outlook. Sends the body to the tracker, swaps in the tracked HTML,
// then lets the send continue. Fails open: any error means the email goes out untracked.
(function () {
  const get = (obj, fn) => new Promise((res) => obj[fn]((r) => res(r.status === Office.AsyncResultStatus.Succeeded ? r.value : null)));
  const getBody = () => new Promise((res) => Office.context.mailbox.item.body.getAsync(Office.CoercionType.Html, (r) => res(r.status === "succeeded" ? r.value : null)));
  const setBody = (html) => new Promise((res) => Office.context.mailbox.item.body.setAsync(html, { coercionType: Office.CoercionType.Html }, (r) => res(r.status === "succeeded")));
  const addr = (list) => (list || []).map((r) => r.emailAddress).filter(Boolean);

  async function onMessageSendHandler(event) {
    try {
      const item = Office.context.mailbox.item;
      const apiKey = Office.context.roamingSettings.get("apiKey");
      const html = await getBody();
      if (!apiKey || !html || !html.replace(/<[^>]*>/g, "").trim()) return event.completed({ allowEvent: true });
      if (html.indexOf("/t/") !== -1 && /\/t\/[A-Za-z0-9_-]+\.png/.test(html)) return event.completed({ allowEvent: true }); // already tracked
      const subject = (await get(item.subject, "getAsync")) || "";
      const [to, cc, bcc] = await Promise.all([get(item.to, "getAsync"), get(item.cc, "getAsync"), get(item.bcc, "getAsync")]);
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), 8000);
      const res = await fetch(location.origin + "/api/track", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ subject, recipients: [...addr(to), ...addr(cc), ...addr(bcc)], html }),
        signal: ctl.signal,
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        if (data && data.html) await setBody(data.html);
      }
    } catch (e) {
      console.warn("[Email Tracker] not tracked:", e);
    }
    event.completed({ allowEvent: true });
  }

  Office.onReady(() => {});
  Office.actions.associate("onMessageSendHandler", onMessageSendHandler);
})();
