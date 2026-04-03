const DEFAULT_PORT = 8765;

let resolvedPort: number | null = null;

async function getPort(): Promise<number> {
  if (resolvedPort !== null) return resolvedPort;
  if (typeof window !== "undefined" && (window as any).electronAPI) {
    resolvedPort = await (window as any).electronAPI.getBackendPort();
  } else {
    resolvedPort = DEFAULT_PORT;
  }
  return resolvedPort;
}

export type ApiError = {
  status: number;
  message: string;
};

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const port = await getPort();
  const url = `http://127.0.0.1:${port}${path}`;
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    const err: ApiError = { status: res.status, message: text };
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string): Promise<T> => request<T>("GET", path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>("PATCH", path, body),
  delete: <T>(path: string): Promise<T> => request<T>("DELETE", path),
};
