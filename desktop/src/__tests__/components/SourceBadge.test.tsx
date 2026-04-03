import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SourceBadge } from "../../renderer/components/SourceBadge";
import type { Source } from "../../renderer/components/MessageBubble";

describe("SourceBadge", () => {
  const source: Source = {
    memory_id: "m-1",
    source_type: "apple_notes",
    title: "Meeting Notes",
    snippet: "We discussed the Q3 roadmap.",
  };

  it("renders badge with title", () => {
    render(<SourceBadge source={source} />);
    expect(screen.getByTestId("source-badge-button").textContent).toBe("Meeting Notes");
  });

  it("expands snippet on click", () => {
    render(<SourceBadge source={source} />);
    expect(screen.queryByTestId("source-snippet")).toBeNull();
    fireEvent.click(screen.getByTestId("source-badge-button"));
    expect(screen.getByTestId("source-snippet").textContent).toBe(
      "We discussed the Q3 roadmap."
    );
  });

  it("collapses snippet on second click", () => {
    render(<SourceBadge source={source} />);
    fireEvent.click(screen.getByTestId("source-badge-button"));
    fireEvent.click(screen.getByTestId("source-badge-button"));
    expect(screen.queryByTestId("source-snippet")).toBeNull();
  });

  it("renders source_type when title is null", () => {
    const noTitle: Source = { ...source, title: null };
    render(<SourceBadge source={noTitle} />);
    expect(screen.getByTestId("source-badge-button").textContent).toBe("apple_notes");
  });
});
