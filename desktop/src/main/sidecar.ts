import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as fs from "fs";

const HEALTH_CHECK_INTERVAL_MS = 500;
const HEALTH_CHECK_TIMEOUT_MS = 30_000;

export class SidecarManager {
  readonly port: number = 8765;
  private process: ChildProcess | null = null;

  async start(): Promise<void> {
    // If backend is already running (e.g. from a terminal), skip spawning.
    try {
      const res = await fetch(`http://127.0.0.1:${this.port}/health`);
      if (res.ok) {
        console.log("[sidecar] Backend already running, skipping spawn.");
        return;
      }
    } catch {
      // not running yet — proceed to spawn below
    }

    const pythonPath = this.resolvePythonPath();
    this.process = spawn(pythonPath, [
      "-m",
      "uvicorn",
      "assistant.main:create_app",
      "--factory",
      "--host",
      "127.0.0.1",
      "--port",
      String(this.port),
    ], {
      env: { ...process.env, PYTHONPATH: this.resolveSrcPath() },
      stdio: ["ignore", "pipe", "pipe"],
    });

    this.process.stdout?.on("data", (data: Buffer) => {
      console.log("[sidecar]", data.toString().trim());
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      console.error("[sidecar:err]", data.toString().trim());
    });

    await this.waitForHealth();
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill("SIGTERM");
      this.process = null;
    }
  }

  private async waitForHealth(): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < HEALTH_CHECK_TIMEOUT_MS) {
      try {
        const res = await fetch(`http://127.0.0.1:${this.port}/health`);
        if (res.ok) return;
      } catch {
        // not ready yet
      }
      await new Promise((resolve) => setTimeout(resolve, HEALTH_CHECK_INTERVAL_MS));
    }
    throw new Error("Backend sidecar failed to start within timeout");
  }

  private resolvePythonPath(): string {
    const candidates = [
      path.join(__dirname, "../../../backend/.venv/bin/python"),
      "python3",
      "python",
    ];
    for (const candidate of candidates) {
      if (!candidate.startsWith("python") && fs.existsSync(candidate)) {
        return candidate;
      }
      if (candidate.startsWith("python")) {
        return candidate;
      }
    }
    return "python3";
  }

  private resolveSrcPath(): string {
    return path.join(__dirname, "../../../backend/src");
  }
}
