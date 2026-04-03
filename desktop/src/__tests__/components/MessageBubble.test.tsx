import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "../../renderer/components/MessageBubble";
import type { Message } from "../../renderer/components/MessageBubble";

describe("MessageBubble", () => {
  it("renders user message", () => {
    const msg: Message = {
      id: "1",
      role: "user",
      text: "Hello, assistant!",
    };
    render(<MessageBubble message={msg} />);
    expect(screen.getByTestId("message-bubble")).toBeDefined();
    expect(screen.getByTestId("message-text").textContent).toBe("Hello, assistant!");
    expect(screen.getByTestId("message-bubble").getAttribute("data-role")).toBe("user");
  });

  it("renders assistant message", () => {
    const msg: Message = {
      id: "2",
      role: "assistant",
      text: "I can help with that.",
    };
    render(<MessageBubble message={msg} />);
    expect(screen.getByTestId("message-bubble").getAttribute("data-role")).toBe("assistant");
    expect(screen.getByTestId("message-text").textContent).toBe("I can help with that.");
  });
});
