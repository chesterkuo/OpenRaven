import { sendToOpenRaven } from "./api";

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
