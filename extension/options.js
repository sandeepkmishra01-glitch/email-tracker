const $ = (id) => document.getElementById(id);
chrome.storage.local.get(["serverUrl", "apiKey"]).then((v) => {
  $("url").value = v.serverUrl || "";
  $("key").value = v.apiKey || "";
});
$("save").onclick = async () => {
  const url = $("url").value.trim().replace(/\/+$/, "");
  try {
    const granted = await chrome.permissions.request({ origins: [new URL(url).origin + "/*"] });
    if (!granted) return ($("status").textContent = "Permission for server was denied");
  } catch {
    return ($("status").textContent = "Invalid URL");
  }
  await chrome.storage.local.set({ serverUrl: url, apiKey: $("key").value.trim() });
  $("status").textContent = "Saved";
};
