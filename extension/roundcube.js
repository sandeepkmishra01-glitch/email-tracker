// Roundcube (webmail) support: intercepts Send on the compose screen, asks the tracker to rewrite
// the HTML body, then sends for real. Fails open: if tracking fails the email goes out untracked.
// Tracking needs an HTML message. In plain-text mode there is no place for a pixel or tracked links,
// so the mail is sent untracked with a warning toast.
(() => {
  if (!/[?&]_action=compose\b/.test(location.search) && !document.querySelector('form[name="form"] [name="_subject"]')) return;
  console.log("[Email Tracker] Roundcube script loaded");

  function toast(msg, bad) {
    const t = document.createElement("div");
    t.textContent = "Email Tracker: " + msg;
    t.style.cssText =
      "position:fixed;left:16px;bottom:16px;z-index:2147483647;padding:10px 14px;border-radius:6px;" +
      "font:13px system-ui,sans-serif;color:#fff;background:" + (bad ? "#b00020" : "#1b7f3b");
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 6000);
  }

  // Roundcube's Elastic skin: <button class="btn btn-primary send"> ; Larry/Classic: <a class="button send">.
  toast("Roundcube tracking active");

  const SEND_SEL = "a.send, button.send, #rcmbtn_send, #compose-send, [data-command='send']";
  let busy = false;

  // HTML mode uses TinyMCE in an iframe (#composebody_ifr, same origin); plain mode uses a textarea.
  const htmlBody = () => {
    const f = document.querySelector("#composebody_ifr, iframe.mce-edit-area, .tox-edit-area__iframe");
    try { return f && f.contentDocument && f.contentDocument.body; } catch (_) { return null; }
  };

  function readCompose() {
    const subject = document.querySelector('[name="_subject"]');
    const emails = new Set();
    document.querySelectorAll('[name="_to"], [name="_cc"], [name="_bcc"]').forEach((i) => {
      (i.value || "").split(/[,;]/).forEach((v) => {
        const m = v.match(/[^\s<>"]+@[^\s<>"]+/);
        if (m) emails.add(m[0]);
      });
    });
    // Elastic's recipient widget also renders each address as a list item.
    document.querySelectorAll(".recipient .email, .recipient [title*='@']").forEach((s) => {
      const v = (s.getAttribute("title") || s.textContent || "").trim();
      if (/@/.test(v)) emails.add(v.replace(/[<>]/g, ""));
    });
    return { body: htmlBody(), subject: subject ? subject.value : "", recipients: [...emails] };
  }

  const ask = (payload) =>
    new Promise((resolve) =>
      chrome.runtime.sendMessage({ type: "track", payload }, (r) =>
        resolve(chrome.runtime.lastError ? { ok: false } : r || { ok: false })
      )
    );

  async function trackThenSend(doSend) {
    if (busy) return;
    busy = true;
    try {
      // Plain-text editor has no place for a pixel: switch to HTML first (Roundcube keeps the text).
      if (!htmlBody()) {
        const sel = document.querySelector('#editor-selector, select[name="editorSelector"]');
        if (sel) {
          sel.value = "html";
          sel.dispatchEvent(new Event("change", { bubbles: true }));
          for (let i = 0; i < 20 && !htmlBody(); i++) await new Promise((r) => setTimeout(r, 150));
        }
      }
      const { body, subject, recipients } = readCompose();
      if (!body) {
        toast("NOT tracked: switch the editor to HTML (Options > Editor type > HTML)", true);
      } else if (!body.dataset.etTracked && body.innerText.trim()) {
        const r = await ask({ subject, recipients, html: body.innerHTML });
        if (r.ok && r.data && r.data.html) {
          body.innerHTML = r.data.html;
          body.dataset.etTracked = "1";
          toast("tracked");
        } else {
          console.warn("[Email Tracker] not tracked:", r.error);
          toast("NOT tracked (" + (r.error || "unknown") + ")", true);
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
      trackThenSend(() => {
        btn.dataset.etBypass = "1";
        btn.click();
        setTimeout(() => delete btn.dataset.etBypass, 1000);
      });
    },
    true
  );
})();
