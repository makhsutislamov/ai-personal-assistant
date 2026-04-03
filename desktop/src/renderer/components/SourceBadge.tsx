import React, { useState } from "react";
import type { Source } from "./MessageBubble";

type Props = {
  source: Source;
};

export function SourceBadge({ source }: Props): React.ReactElement {
  const [expanded, setExpanded] = useState(false);

  return (
    <span data-testid="source-badge" style={{ display: "inline-block", marginRight: 4 }}>
      <button
        data-testid="source-badge-button"
        onClick={() => setExpanded((v) => !v)}
        style={{
          fontSize: 11,
          padding: "2px 6px",
          borderRadius: 4,
          border: "1px solid #ccc",
          background: "#f0f4ff",
          cursor: "pointer",
        }}
      >
        {source.title ?? source.source_type}
      </button>
      {expanded && source.snippet && (
        <div
          data-testid="source-snippet"
          style={{
            position: "absolute",
            background: "#fff",
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: 8,
            maxWidth: 320,
            fontSize: 12,
            zIndex: 10,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          }}
        >
          {source.snippet}
        </div>
      )}
    </span>
  );
}
