import React from "react";

export type MessageRole = "user" | "assistant";

export type Source = {
  memory_id: string;
  source_type: string;
  title: string | null;
  snippet: string | null;
};

export type Message = {
  id: string;
  role: MessageRole;
  text: string;
  sources?: Source[];
};

type Props = {
  message: Message;
};

export function MessageBubble({ message }: Props): React.ReactElement {
  const isUser = message.role === "user";
  return (
    <div
      data-testid="message-bubble"
      data-role={message.role}
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 8,
      }}
    >
      <div
        style={{
          maxWidth: "70%",
          padding: "8px 12px",
          borderRadius: 12,
          background: isUser ? "#0078d4" : "#f3f3f3",
          color: isUser ? "#fff" : "#1a1a1a",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        <span data-testid="message-text">{message.text}</span>
      </div>
    </div>
  );
}
