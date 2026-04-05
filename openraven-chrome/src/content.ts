function extractPageContent(): { title: string; url: string; text: string } {
  const article = document.querySelector("article") ?? document.querySelector("main") ?? document.body;

  const clone = article.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("script, style, nav, footer, header, aside, [role='navigation'], [role='banner']").forEach((el) => el.remove());

  const text = clone.innerText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");

  return {
    title: document.title,
    url: window.location.href,
    text,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "EXTRACT_CONTENT") {
    const content = extractPageContent();
    sendResponse(content);
  } else if (message.type === "EXTRACT_SELECTION") {
    const selection = window.getSelection()?.toString() ?? "";
    sendResponse({
      title: document.title,
      url: window.location.href,
      text: selection,
    });
  }
  return true;
});
