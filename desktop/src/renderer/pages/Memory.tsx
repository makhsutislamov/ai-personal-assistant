import React, { useState, useEffect } from "react";
import { apiClient } from "../api/client";

type MemoryRecord = {
  record_id: string;
  content: string;
  source_type: string;
  created_at: string;
};

export function Memory(): React.ReactElement {
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMemory = async () => {
    setLoading(true);
    try {
      const r = await apiClient.get<MemoryRecord[]>("/v1/memory");
      setRecords(r);
    } catch {
      setError("Failed to load memory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemory();
  }, []);

  const deleteRecord = async (id: string) => {
    try {
      await apiClient.delete(`/v1/memory?record_ids=${id}`);
      setRecords((prev) => prev.filter((r) => r.record_id !== id));
    } catch {
      setError("Delete failed.");
    }
  };

  const filtered = records.filter((r) => {
    const matchesSearch = !search || r.content.toLowerCase().includes(search.toLowerCase());
    const matchesSource = !sourceFilter || r.source_type === sourceFilter;
    return matchesSearch && matchesSource;
  });

  const allSources = [...new Set(records.map((r) => r.source_type))];

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h2>Memory</h2>
      {error && <div style={{ color: "red" }}>{error}</div>}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          data-testid="memory-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search memory…"
          style={{ flex: 1, padding: 6, borderRadius: 4, border: "1px solid #ccc" }}
        />
        <select
          data-testid="source-filter"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
        >
          <option value="">All sources</option>
          {allSources.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div>Loading…</div>
      ) : filtered.length === 0 ? (
        <div data-testid="memory-empty">No memory records found.</div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {filtered.map((r) => (
            <li
              key={r.record_id}
              data-testid="memory-item"
              style={{
                border: "1px solid #e0e0e0",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 6,
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: "#888", marginBottom: 2 }}>
                  {r.source_type} · {new Date(r.created_at).toLocaleDateString()}
                </div>
                <div style={{ fontSize: 14 }}>{r.content}</div>
              </div>
              <button
                data-testid="memory-delete-btn"
                onClick={() => deleteRecord(r.record_id)}
                style={{ fontSize: 12, color: "#d00", border: "none", background: "none", cursor: "pointer" }}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
