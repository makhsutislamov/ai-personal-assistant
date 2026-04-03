import React from "react";

export type MemoryCandidate = {
  candidate_id: string;
  content: string;
  source_type: string;
};

type Props = {
  candidate: MemoryCandidate;
  onConfirm: (id: string) => void;
  onReject: (id: string) => void;
};

export function MemoryConfirm({
  candidate,
  onConfirm,
  onReject,
}: Props): React.ReactElement {
  return (
    <div
      data-testid="memory-confirm"
      style={{
        border: "1px solid #f0a834",
        borderRadius: 8,
        padding: 8,
        margin: "4px 0",
        background: "#fffbf0",
        fontSize: 13,
      }}
    >
      <p style={{ margin: "0 0 6px" }}>
        <strong>Save to memory?</strong> ({candidate.source_type})
        <br />
        {candidate.content}
      </p>
      <button
        data-testid="memory-confirm-yes"
        onClick={() => onConfirm(candidate.candidate_id)}
        style={{ marginRight: 6 }}
      >
        Save
      </button>
      <button
        data-testid="memory-confirm-no"
        onClick={() => onReject(candidate.candidate_id)}
      >
        Discard
      </button>
    </div>
  );
}
