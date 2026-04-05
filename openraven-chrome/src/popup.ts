import { checkConnection, getSettings } from "./api";

const saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
const pageTitle = document.getElementById("page-title") as HTMLDivElement;
const statusLoading = document.getElementById("status-loading") as HTMLDivElement;
const statusSuccess = document.getElementById("status-success") as HTMLDivElement;
const statusError = document.getElementById("status-error") as HTMLDivElement;
const errorMessage = document.getElementById("error-message") as HTMLSpanElement;
const statEntities = document.getElementById("stat-entities") as HTMLDivElement;
const statArticles = document.getElementById("stat-articles") as HTMLDivElement;
const statFiles = document.getElementById("stat-files") as HTMLDivElement;
const authStatus = document.getElementById("auth-status") as HTMLDivElement;
const loginLink = document.getElementById("login-link") as HTMLAnchorElement;

function hideAll() {
  statusLoading.classList.add("hidden");
  statusSuccess.classList.add("hidden");
  statusError.classList.add("hidden");
}

function showError(msg: string) {
  hideAll();
  errorMessage.textContent = msg;
  statusError.classList.remove("hidden");
}

function showSuccess(entities: number, articles: number, files: number) {
  hideAll();
  statEntities.textContent = String(entities);
  statArticles.textContent = String(articles);
  statFiles.textContent = String(files);
  statusSuccess.classList.remove("hidden");
}

function showLoading() {
  hideAll();
  statusLoading.classList.remove("hidden");
}

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]?.title) {
    pageTitle.textContent = tabs[0].title;
  }
});

checkConnection().then(({ connected, authenticated }) => {
  if (!connected) {
    showError("OpenRaven is not running. Check settings.");
    saveBtn.disabled = true;
    return;
  }
  getSettings().then((settings) => {
    if (settings.authMode === "cloud" && !authenticated) {
      authStatus.classList.remove("hidden");
      loginLink.addEventListener("click", (e) => {
        e.preventDefault();
        chrome.tabs.create({ url: `${settings.apiUrl}/login` });
      });
    }
  });
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;
  showLoading();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    showError("No active tab");
    saveBtn.disabled = false;
    return;
  }

  chrome.runtime.sendMessage({ type: "SAVE_PAGE", tabId: tab.id }, (response) => {
    if (response?.success) {
      const r = response.result;
      showSuccess(r.entities_extracted, r.articles_generated, r.files_processed);
    } else {
      showError(response?.error ?? "Unknown error");
      saveBtn.disabled = false;
    }
  });
});
