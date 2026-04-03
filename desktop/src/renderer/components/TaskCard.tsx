import React from "react";

export type Task = {
  task_id: string;
  title: string;
  status: "created" | "in_progress" | "blocked" | "completed" | "cancelled";
  requires_confirmation: boolean;
};

const STATUS_COLORS: Record<Task["status"], string> = {
  created: "#888",
  in_progress: "#0078d4",
  blocked: "#d4380d",
  completed: "#52c41a",
  cancelled: "#aaa",
};

type Props = {
  task: Task;
};

export function TaskCard({ task }: Props): React.ReactElement {
  return (
    <div
      data-testid="task-card"
      style={{
        border: "1px solid #e0e0e0",
        borderRadius: 8,
        padding: "8px 12px",
        marginBottom: 6,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span
        data-testid="task-status-dot"
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: STATUS_COLORS[task.status],
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span data-testid="task-title" style={{ flex: 1 }}>
        {task.title}
      </span>
      <span
        data-testid="task-status-label"
        style={{ fontSize: 11, color: STATUS_COLORS[task.status] }}
      >
        {task.status.replace("_", " ")}
      </span>
      {task.requires_confirmation && (
        <span
          data-testid="task-confirmation-badge"
          style={{
            fontSize: 10,
            padding: "2px 5px",
            background: "#fff0e6",
            border: "1px solid #f0a834",
            borderRadius: 4,
          }}
        >
          Confirm
        </span>
      )}
    </div>
  );
}
