// Intercepts Gmail's Send, asks the tracker to rewrite the body, then sends for real.
// Fails open: if tracking fails, the email is sent untracked rather than blocked.
(() => {
  const VERSION = "1.1.0-diag";
  console.log("[Email Tracker] content script loaded, v" + VERSION);
  function toast(msg, bad) {
    const t = document.createElement("div");
    t.textContent = "Email Tracker: " + msg;
    t.style.cssText =
      "position:fixed;left:16px;bottom:16px;z-index:2147483647;padding:10px 14px;border-radius:6px;" +
      "font:13px system-ui,sans-serif;color:#fff;background:" + (bad ? "#b00020" : "#1b7f3b");
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 6000);
  }
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
          // Gmail may re-linkify the compose body and revert hrefs (esp. when the link text is
          // the URL itself). Re-apply the tracked hrefs, then once more after Gmail settles.
          const tmp = document.createElement("div");
          tmp.innerHTML = r.data.html;
          const wanted = [...tmp.querySelectorAll("a[href]")].map((a) => a.getAttribute("href"));
          const apply = () =>
            [...body.querySelectorAll("a[href]")].forEach((a, i) => {
              if (wanted[i] && a.getAttribute("href") !== wanted[i]) a.setAttribute("href", wanted[i]);
              // Keep URL-looking link text from being re-linkified by Gmail (invisible word joiner).
              if (/^https?:\/\//i.test(a.textContent.trim()) && !a.textContent.includes("⁠"))
                a.textContent = a.textContent.replace("://", "://⁠");
            });
          apply();
          await new Promise((res) => setTimeout(res, 400));
          apply();
          const now = [...body.querySelectorAll("a[href]")].map((a) => a.getAttribute("href"));
          const ok = wanted.filter((w, i) => now[i] === w).length;
          console.log("[Email Tracker] v" + VERSION + " links wanted:", wanted, "actual:", now);
          toast(
            wanted.length
              ? ok + "/" + wanted.length + " links tracked" + (ok === wanted.length ? "" : " (some links reverted!)")
              : "tracked (no links in this message)",
            wanted.length > 0 && ok !== wanted.length
          );
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
