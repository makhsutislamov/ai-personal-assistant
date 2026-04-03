import React, { useState, useRef, useEffect, useCallback } from "react";
import { apiClient } from "../api/client";
import { MessageBubble } from "../components/MessageBubble";
import { SourceBadge } from "../components/SourceBadge";
import { MemoryConfirm } from "../components/MemoryConfirm";
import { NoteEditor } from "../components/NoteEditor";
import type { Message, Source } from "../components/MessageBubble";
import type { MemoryCandidate } from "../components/MemoryConfirm";
import type { GeneratedNotes } from "../components/NoteEditor";

type ChatResponse = {
  response: string;
  session_id: string;
  sources: Source[];
  model_used: string;
  grounded: boolean;
};

type MemoryCandidateOut = {
  candidate_id: string;
  content: string;
  source_type: string;
};

export function Chat(): React.ReactElement {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [pendingMemory, setPendingMemory] = useState<MemoryCandidate[]>([]);
  const [generatedNotes, setGeneratedNotes] = useState<GeneratedNotes | null>(null);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setLoading(true);

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text,
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const resp = await apiClient.post<ChatResponse>("/v1/chat/respond", {
        message: text,
        session_id: sessionId,
      });
      setSessionId(resp.session_id);
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: resp.response,
        sources: resp.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: "Sorry, something went wrong. Make sure the backend is running.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const confirmMemory = async (id: string) => {
    try {
      await apiClient.post("/v1/memory/confirm", { candidate_id: id });
    } catch {
      // best-effort
    }
    setPendingMemory((prev) => prev.filter((c) => c.candidate_id !== id));
  };

  const rejectMemory = async (id: string) => {
    try {
      await apiClient.post("/v1/memory/reject", { candidate_id: id });
    } catch {
      // best-effort
    }
    setPendingMemory((prev) => prev.filter((c) => c.candidate_id !== id));
  };

  const generateNotes = async () => {
    if (!sessionId) return;
    try {
      const notes = await apiClient.post<GeneratedNotes>(
        `/v1/chat/sessions/${sessionId}/notes`
      );
      setGeneratedNotes(notes);
      setShowNoteEditor(true);
    } catch {
      // best-effort
    }
  };

  const saveNotes = async (notes: GeneratedNotes) => {
    if (!sessionId) return;
    try {
      await apiClient.post(`/v1/chat/sessions/${sessionId}/notes/save`, notes);
    } catch {
      // best-effort
    }
    setShowNoteEditor(false);
    setGeneratedNotes(null);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          padding: "8px 16px",
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span style={{ fontWeight: 600 }}>AI Assistant</span>
        {sessionId && (
          <button onClick={generateNotes} style={{ marginLeft: "auto", fontSize: 12 }}>
            Generate Notes
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {messages.map((msg) => (
          <div key={msg.id}>
            <MessageBubble message={msg} />
            {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
              <div style={{ paddingLeft: 8, marginTop: -4, marginBottom: 6 }}>
                {msg.sources.map((src) => (
                  <SourceBadge key={src.memory_id} source={src} />
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ color: "#888", fontStyle: "italic", fontSize: 13 }}>
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Memory confirmations */}
      {pendingMemory.length > 0 && (
        <div style={{ padding: "0 16px" }}>
          {pendingMemory.map((c) => (
            <MemoryConfirm
              key={c.candidate_id}
              candidate={c}
              onConfirm={confirmMemory}
              onReject={rejectMemory}
            />
          ))}
        </div>
      )}

      {/* Note editor modal */}
      {showNoteEditor && generatedNotes && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div style={{ width: 500, maxWidth: "90vw" }}>
            <NoteEditor
              notes={generatedNotes}
              onSave={saveNotes}
              onCancel={() => setShowNoteEditor(false)}
            />
          </div>
        </div>
      )}

      {/* Input */}
      <div
        style={{
          padding: "8px 16px",
          borderTop: "1px solid #e0e0e0",
          display: "flex",
          gap: 8,
        }}
      >
        <textarea
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
          rows={2}
          style={{ flex: 1, resize: "none", borderRadius: 6, padding: 8, fontSize: 14 }}
          disabled={loading}
        />
        <button
          data-testid="chat-send"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          style={{ padding: "0 16px", borderRadius: 6 }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

