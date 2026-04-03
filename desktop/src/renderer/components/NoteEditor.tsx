import React, { useState } from "react";

export type GeneratedNotes = {
  summary: string;
  decisions: string[];
  action_items: string[];
  open_questions: string[];
  suggested_tags: string[];
};

type Props = {
  notes: GeneratedNotes;
  onSave: (notes: GeneratedNotes) => void;
  onCancel: () => void;
};

export function NoteEditor({ notes, onSave, onCancel }: Props): React.ReactElement {
  const [draft, setDraft] = useState<GeneratedNotes>({ ...notes });

  return (
    <div
      data-testid="note-editor"
      style={{
        border: "1px solid #ccc",
        borderRadius: 8,
        padding: 12,
        background: "#fafafa",
      }}
    >
      <h3 style={{ margin: "0 0 8px" }}>Edit Notes</h3>
      <label>
        Summary
        <textarea
          data-testid="note-summary"
          value={draft.summary}
          onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
          style={{ display: "block", width: "100%", marginBottom: 8, minHeight: 60 }}
        />
      </label>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button
          data-testid="note-save"
          onClick={() => onSave(draft)}
        >
          Save Notes
        </button>
        <button data-testid="note-cancel" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
