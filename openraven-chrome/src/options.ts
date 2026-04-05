const apiUrlInput = document.getElementById("api-url") as HTMLInputElement;
const authModeSelect = document.getElementById("auth-mode") as HTMLSelectElement;
const cloudInfo = document.getElementById("cloud-info") as HTMLDivElement;
const saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
const testBtn = document.getElementById("test-btn") as HTMLButtonElement;
const statusMsg = document.getElementById("status-msg") as HTMLDivElement;

chrome.storage.sync.get(["apiUrl", "authMode"], (data) => {
  if (data.apiUrl) apiUrlInput.value = data.apiUrl;
  if (data.authMode) authModeSelect.value = data.authMode;
  toggleCloudInfo();
});

authModeSelect.addEventListener("change", toggleCloudInfo);

function toggleCloudInfo() {
  cloudInfo.classList.toggle("hidden", authModeSelect.value !== "cloud");
}

saveBtn.addEventListener("click", () => {
  chrome.storage.sync.set({
    apiUrl: apiUrlInput.value.replace(/\/+$/, ""),
    authMode: authModeSelect.value,
  }, () => {
    showStatus("Settings saved!", "ok");
  });
});

testBtn.addEventListener("click", async () => {
  const url = apiUrlInput.value.replace(/\/+$/, "");
  try {
    const res = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) showStatus("Connected to OpenRaven!", "ok");
    else showStatus(`Connection failed: HTTP ${res.status}`, "err");
  } catch {
    showStatus("Cannot reach OpenRaven at this URL", "err");
  }
});

function showStatus(msg: string, type: "ok" | "err") {
  statusMsg.textContent = msg;
  statusMsg.className = `status status-${type}`;
  statusMsg.classList.remove("hidden");
}
