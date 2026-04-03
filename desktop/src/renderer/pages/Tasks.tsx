import React, { useState, useEffect } from "react";
import { apiClient } from "../api/client";
import { TaskCard } from "../components/TaskCard";
import type { Task } from "../components/TaskCard";

type StatusFilter = "all" | Task["status"];

export function Tasks(): React.ReactElement {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const r = await apiClient.get<Task[]>("/v1/tasks");
      setTasks(r);
    } catch {
      setError("Failed to load tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const confirmTask = async (taskId: string) => {
    try {
      await apiClient.patch(`/v1/tasks/${taskId}`, { status: "in_progress" });
      setTasks((prev) =>
        prev.map((t) => (t.task_id === taskId ? { ...t, status: "in_progress", requires_confirmation: false } : t))
      );
    } catch {
      setError("Failed to confirm task.");
    }
  };

  const filtered =
    statusFilter === "all" ? tasks : tasks.filter((t) => t.status === statusFilter);

  const STATUS_OPTIONS: StatusFilter[] = [
    "all",
    "created",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
  ];

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h2>Tasks</h2>
      {error && <div style={{ color: "red" }}>{error}</div>}

      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            data-testid={`filter-${s}`}
            onClick={() => setStatusFilter(s)}
            style={{
              padding: "4px 10px",
              borderRadius: 16,
              border: "1px solid #ccc",
              background: statusFilter === s ? "#0078d4" : "#fff",
              color: statusFilter === s ? "#fff" : "#333",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      {loading ? (
        <div>Loading…</div>
      ) : filtered.length === 0 ? (
        <div data-testid="tasks-empty">No tasks found.</div>
      ) : (
        <div>
          {filtered.map((task) => (
            <div key={task.task_id}>
              <TaskCard task={task} />
              {task.requires_confirmation && (
                <button
                  data-testid={`confirm-task-${task.task_id}`}
                  onClick={() => confirmTask(task.task_id)}
                  style={{ marginBottom: 8, fontSize: 12 }}
                >
                  Confirm and start
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
