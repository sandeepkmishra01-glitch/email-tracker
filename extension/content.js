// Intercepts Gmail's Send, asks the tracker to rewrite the body, then sends for real.
// Fails open: if tracking fails, the email is sent untracked rather than blocked.
(() => {
  const SEND_SEL = 'div[role="button"][data-tooltip^="Send"]';
  const BODY_SEL = 'div[aria-label="Message Body"][contenteditable="true"], div[role="textbox"][g_editable="true"]';
  let busy = false;

  const findCompose = (el) =>
    el.closest('div[role="dialog"]') || el.closest("table.aoP") || el.closest(".nH.Hd") || document;

  function readCompose(root) {
    const body = root.querySelector(BODY_SEL);
    const subject = root.querySelector('input[name="subjectbox"]');
    const emails = new Set();
    root.querySelectorAll('input[name="to"], input[name="cc"], input[name="bcc"]').forEach((i) => {
      (i.value || "").split(",").forEach((v) => v.trim() && emails.add(v.trim()));
    });
    root.querySelectorAll("span[email], [data-hovercard-id*='@']").forEach((s) => {
      const v = s.getAttribute("email") || s.getAttribute("data-hovercard-id");
      if (v) emails.add(v);
    });
    return { body, subject: subject ? subject.value : "", recipients: [...emails] };
  }

  const ask = (payload) =>
    new Promise((resolve) =>
      chrome.runtime.sendMessage({ type: "track", payload }, (r) =>
        resolve(chrome.runtime.lastError ? { ok: false } : r || { ok: false })
      )
    );

  async function trackThenSend(root, doSend) {
    if (busy) return;
    busy = true;
    try {
      const { body, subject, recipients } = readCompose(root);
      if (body && !body.dataset.etTracked && body.innerText.trim()) {
        const r = await ask({ subject, recipients, html: body.innerHTML });
        if (r.ok && r.data && r.data.html) {
          body.innerHTML = r.data.html;
          body.dataset.etTracked = "1";
        } else {
          console.warn("[Email Tracker] not tracked:", r.error);
        }
      }
    } finally {
      busy = false;
    }
    doSend();
  }

  document.addEventListener(
    "click",
    (e) => {
      const btn = e.target.closest && e.target.closest(SEND_SEL);
      if (!btn || btn.dataset.etBypass) return;
      e.stopImmediatePropagation();
      e.preventDefault();
      trackThenSend(findCompose(btn), () => {
        btn.dataset.etBypass = "1";
        btn.click();
        setTimeout(() => delete btn.dataset.etBypass, 500);
      });
    },
    true
  );

  // Ctrl/Cmd+Enter shortcut
  document.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Enter" || !(e.ctrlKey || e.metaKey) || e.__etReplay) return;
      const root = findCompose(e.target);
      const btn = root.querySelector(SEND_SEL);
      if (!btn || !e.target.closest(BODY_SEL)) return;
      e.stopImmediatePropagation();
      e.preventDefault();
      trackThenSend(root, () => {
        btn.dataset.etBypass = "1";
        btn.click();
        setTimeout(() => delete btn.dataset.etBypass, 500);
      });
    },
    true
  );
})();
