// Background service worker for AI Personal Assistant Capture
const BACKEND_PORT = 8765;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}/v1/integrations/browser-capture`;

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "capture-to-assistant",
    title: "Capture to AI Assistant",
    contexts: ["selection", "page"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "capture-to-assistant" || !tab) return;

  const selectedText = info.selectionText ?? "";

  // Get full page content if enabled (via content script message)
  let fullPageContent = null;
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => document.body.innerText,
    });
    if (results?.[0]?.result) {
      fullPageContent = results[0].result.slice(0, 50000);
    }
  } catch (_) {
    // Full page extraction optional — proceed without it
  }

  const payload = {
    url: tab.url ?? "",
    title: tab.title ?? "",
    selected_text: selectedText,
    full_page_content: fullPageContent,
    capture_mode: selectedText ? "selection" : "full_page",
  };

  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();

    // Notify popup of capture result
    chrome.storage.session.set({
      lastCapture: { success: result.success, message: result.message, timestamp: Date.now() },
    });
  } catch (err) {
    chrome.storage.session.set({
      lastCapture: { success: false, message: String(err), timestamp: Date.now() },
    });
  }
});
