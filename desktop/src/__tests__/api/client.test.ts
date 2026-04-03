import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "../../renderer/api/client";

describe("apiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset port cache between tests
    (globalThis as any).electronAPI = undefined;
  });

  it("GET constructs correct URL and returns parsed JSON", async () => {
    const mockResponse = { status: "ok" };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(mockResponse), { status: 200 }));

    const result = await apiClient.get("/health");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({ method: "GET" })
    );
    expect(result).toEqual(mockResponse);
  });

  it("POST sends JSON body with correct content-type", async () => {
    const payload = { message: "hello" };
    const mockResponse = { id: "1", response: "hi" };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(mockResponse), { status: 200 }));

    await apiClient.post("/v1/chat/respond", payload);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/v1/chat/respond"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  });

  it("throws ApiError on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Not found", { status: 404 })
    );

    await expect(apiClient.get("/v1/missing")).rejects.toMatchObject({
      status: 404,
      message: "Not found",
    });
  });

  it("returns undefined for 204 No Content", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 })
    );

    const result = await apiClient.delete("/v1/memory");
    expect(result).toBeUndefined();
  });
});
