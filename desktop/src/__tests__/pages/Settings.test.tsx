import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Settings } from "../../renderer/pages/Settings";

vi.mock("../../renderer/api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ settings: { memory_mode: "ask", routing_preference: "ollama" } }),
    post: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({ settings: { memory_mode: "auto", routing_preference: "ollama" } }),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

describe("Settings page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders memory mode selector", async () => {
    render(<Settings />);
    await waitFor(() => {
      expect(screen.getByTestId("memory-mode-select")).toBeDefined();
    });
  });

  it("renders routing preference selector", async () => {
    render(<Settings />);
    await waitFor(() => {
      expect(screen.getByTestId("routing-select")).toBeDefined();
    });
  });

  it("calls PATCH when memory mode changes", async () => {
    const { apiClient } = await import("../../renderer/api/client");
    render(<Settings />);
    await waitFor(() => screen.getByTestId("memory-mode-select"));
    fireEvent.change(screen.getByTestId("memory-mode-select"), {
      target: { value: "auto" },
    });
    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        "/v1/settings/memory-mode",
        { value: "auto" }
      );
    });
  });

  it("renders integration status section", async () => {
    render(<Settings />);
    await waitFor(() => {
      expect(screen.getByTestId("apple-notes-status")).toBeDefined();
      expect(screen.getByTestId("browser-status")).toBeDefined();
    });
  });
});
