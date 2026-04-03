import React, { useState, useEffect } from "react";
import { apiClient } from "../api/client";

type SettingsMap = Record<string, string>;

type IntegrationStatus = {
  apple_notes: "connected" | "disconnected";
  browser: "installed" | "not_installed";
};

export function Settings(): React.ReactElement {
  const [settings, setSettings] = useState<SettingsMap>({});
  const [integration, setIntegration] = useState<IntegrationStatus>({
    apple_notes: "disconnected",
    browser: "not_installed",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get<{ settings: SettingsMap }>("/v1/settings").then((r) =>
      setSettings(r.settings)
    ).catch(() => {});

    apiClient.get<{ apple_notes: string; browser: string }>("/v1/integrations/status").then((r) => {
      setIntegration({
        apple_notes: r.apple_notes === "connected" ? "connected" : "disconnected",
        browser: r.browser === "installed" ? "installed" : "not_installed",
      });
    }).catch(() => {});
  }, []);

  const applyPatch = async (path: string, value: string) => {
    setSaving(true);
    setError(null);
    try {
      const result = await apiClient.patch<{ settings: SettingsMap }>(path, { value });
      setSettings(result.settings);
    } catch {
      setError("Failed to save setting.");
    } finally {
      setSaving(false);
    }
  };

  const connectAppleNotes = async () => {
    try {
      await apiClient.post("/v1/integrations/apple-notes/connect");
      setIntegration((prev) => ({ ...prev, apple_notes: "connected" }));
    } catch {
      setError("Failed to connect Apple Notes.");
    }
  };

  const disconnectAppleNotes = async () => {
    try {
      await apiClient.post("/v1/integrations/apple-notes/disconnect");
      setIntegration((prev) => ({ ...prev, apple_notes: "disconnected" }));
    } catch {
      setError("Failed to disconnect Apple Notes.");
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 560 }}>
      <h2>Settings</h2>

      {error && (
        <div style={{ color: "red", marginBottom: 12 }} data-testid="settings-error">
          {error}
        </div>
      )}

      {/* Memory mode */}
      <section style={{ marginBottom: 24 }}>
        <h3>Memory</h3>
        <label>
          Mode
          <select
            data-testid="memory-mode-select"
            value={settings.memory_mode ?? "ask"}
            onChange={(e) => applyPatch("/v1/settings/memory-mode", e.target.value)}
            disabled={saving}
            style={{ marginLeft: 8 }}
          >
            <option value="ask">Ask (confirm each write)</option>
            <option value="auto">Auto (always save)</option>
            <option value="manual">Manual (never auto-save)</option>
          </select>
        </label>
      </section>

      {/* Model routing */}
      <section style={{ marginBottom: 24 }}>
        <h3>Model Routing</h3>
        <label>
          Preference
          <select
            data-testid="routing-select"
            value={settings.routing_preference ?? "ollama"}
            onChange={(e) => applyPatch("/v1/settings/model-routing", e.target.value)}
            disabled={saving}
            style={{ marginLeft: 8 }}
          >
            <option value="ollama">Local (Ollama)</option>
            <option value="azure_openai">Azure OpenAI</option>
            <option value="auto">Auto (prefer Azure, fallback local)</option>
          </select>
        </label>
      </section>

      {/* Integrations */}
      <section>
        <h3>Integrations</h3>
        <div style={{ marginBottom: 12 }}>
          <strong>Apple Notes</strong>{" "}
          <span
            data-testid="apple-notes-status"
            style={{
              color: integration.apple_notes === "connected" ? "green" : "#888",
            }}
          >
            {integration.apple_notes}
          </span>{" "}
          {integration.apple_notes === "disconnected" ? (
            <button data-testid="apple-notes-connect" onClick={connectAppleNotes}>
              Connect
            </button>
          ) : (
            <button data-testid="apple-notes-disconnect" onClick={disconnectAppleNotes}>
              Disconnect
            </button>
          )}
        </div>
        <div>
          <strong>Browser Extension</strong>{" "}
          <span
            data-testid="browser-status"
            style={{
              color: integration.browser === "installed" ? "green" : "#888",
            }}
          >
            {integration.browser === "installed" ? "installed" : "not installed"}
          </span>
        </div>
      </section>
    </div>
  );
}

