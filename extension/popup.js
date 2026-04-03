// popup.js — shows status of last capture and manages full-page toggle
const statusEl = document.getElementById("status");
const fullPageToggle = document.getElementById("fullPageToggle");

// Load last capture status
chrome.storage.session.get(["lastCapture"], (result) => {
  if (result.lastCapture) {
    const { success, message, timestamp } = result.lastCapture;
    const age = Math.round((Date.now() - timestamp) / 1000);
    statusEl.textContent = `${success ? "✓" : "✗"} ${message} (${age}s ago)`;
    statusEl.className = success ? "success" : "error";
  }
});

// Persist full-page toggle preference
chrome.storage.local.get(["fullPage"], (result) => {
  if (result.fullPage !== undefined) {
    fullPageToggle.checked = result.fullPage;
  }
});

fullPageToggle.addEventListener("change", () => {
  chrome.storage.local.set({ fullPage: fullPageToggle.checked });
});
