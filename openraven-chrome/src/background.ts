import { sendToOpenRaven } from "./api";

// Register context menus on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "Save page to OpenRaven",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "save-selection",
    title: "Save selection to OpenRaven",
    contexts: ["selection"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) return;
  if (info.menuItemId === "save-page") {
    await handleSavePage(tab.id);
  } else if (info.menuItemId === "save-selection" && info.selectionText) {
    const title = tab.title || "Selection";
    const url = tab.url || "";
    try {
      await sendToOpenRaven(title, url, info.selectionText);
    } catch {}
  }
});

// Handle keyboard shortcut
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "save-page") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) await handleSavePage(tab.id);
  }
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "SAVE_PAGE") {
    handleSavePage(message.tabId).then(sendResponse).catch((err) =>
      sendResponse({ success: false, error: err.message })
    );
    return true;
  }
});

async function handleSavePage(tabId: number): Promise<{ success: boolean; result?: any; error?: string }> {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });

    const [response] = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_CONTENT" }) as any[];
    if (!response?.text) {
      return { success: false, error: "Could not extract page content" };
    }

    const result = await sendToOpenRaven(response.title, response.url, response.text);
    return { success: true, result };
  } catch (err) {
    return { success: false, error: (err as Error).message };
  }
}
