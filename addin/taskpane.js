Office.onReady(() => {
  const rs = Office.context.roamingSettings;
  document.getElementById("status").textContent = rs.get("apiKey") ? "Key saved" : "No key yet";
  document.getElementById("save").onclick = () => {
    rs.set("apiKey", document.getElementById("key").value.trim());
    rs.saveAsync((r) => {
      document.getElementById("status").textContent = r.status === Office.AsyncResultStatus.Succeeded ? "Saved" : "Could not save";
      document.getElementById("key").value = "";
    });
  };
});
