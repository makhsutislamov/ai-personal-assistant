"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.findFreePort = findFreePort;
exports.startPythonBackend = startPythonBackend;
exports.waitForHealth = waitForHealth;
exports.stopPythonBackend = stopPythonBackend;
const net = __importStar(require("net"));
const http = __importStar(require("http"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
let backendProcess = null;
let restartCount = 0;
const MAX_RESTARTS = 3;
/**
 * Find a free TCP port by creating a temporary server.
 */
function findFreePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            if (!address || typeof address === 'string') {
                server.close();
                reject(new Error('Failed to get port'));
                return;
            }
            const port = address.port;
            server.close(() => resolve(port));
        });
        server.on('error', reject);
    });
}
/**
 * Resolve the path to the Python executable.
 * In production (packaged), looks for the PyInstaller bundle in extraResources.
 * In development, uses the venv.
 */
function resolvePythonPath(isDev) {
    if (isDev) {
        const venvPython = path.join(__dirname, '..', 'backend', '.venv', 'bin', 'python3');
        if (fs.existsSync(venvPython))
            return venvPython;
        return 'python3';
    }
    // In packaged app, PyInstaller bundle is at Resources/backend/backend
    const bundledBackend = path.join(process.resourcesPath, 'backend', 'backend');
    if (fs.existsSync(bundledBackend))
        return bundledBackend;
    return 'python3';
}
/**
 * Start the FastAPI Python backend.
 * Returns the port it's listening on.
 */
async function startPythonBackend(authToken) {
    const port = await findFreePort();
    const isDev = process.env.NODE_ENV === 'development' || !process.resourcesPath;
    const pythonPath = resolvePythonPath(isDev);
    const args = isDev
        ? ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)]
        : ['--host', '127.0.0.1', '--port', String(port)];
    const cwd = isDev
        ? path.join(__dirname, '..', 'backend')
        : path.join(process.resourcesPath, 'backend');
    console.log(`[PythonManager] Starting backend: ${pythonPath} ${args.join(' ')} (cwd: ${cwd})`);
    backendProcess = (0, child_process_1.spawn)(pythonPath, args, {
        cwd,
        env: {
            ...process.env,
            AUTH_TOKEN: authToken,
            PYTHONUNBUFFERED: '1',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    backendProcess.stdout?.on('data', (data) => {
        console.log(`[Backend] ${data.toString().trim()}`);
    });
    backendProcess.stderr?.on('data', (data) => {
        console.error(`[Backend ERR] ${data.toString().trim()}`);
    });
    backendProcess.on('exit', (code, signal) => {
        console.warn(`[PythonManager] Backend exited (code=${code}, signal=${signal})`);
        if (restartCount < MAX_RESTARTS && code !== 0) {
            restartCount++;
            console.log(`[PythonManager] Restarting backend (attempt ${restartCount}/${MAX_RESTARTS})`);
            startPythonBackend(authToken).catch(console.error);
        }
    });
    await waitForHealth(port);
    return port;
}
/**
 * Poll the health endpoint until the backend is ready.
 */
function waitForHealth(port, maxRetries = 50, intervalMs = 100) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const poll = () => {
            attempts++;
            const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                }
                else if (attempts < maxRetries) {
                    setTimeout(poll, intervalMs);
                }
                else {
                    reject(new Error(`Backend unhealthy after ${maxRetries} attempts`));
                }
            });
            req.on('error', () => {
                if (attempts < maxRetries) {
                    setTimeout(poll, intervalMs);
                }
                else {
                    reject(new Error(`Backend unreachable after ${maxRetries} attempts`));
                }
            });
            req.end();
        };
        poll();
    });
}
/**
 * Gracefully stop the backend process.
 */
function stopPythonBackend() {
    if (!backendProcess)
        return;
    console.log('[PythonManager] Stopping backend...');
    backendProcess.kill('SIGTERM');
    const forceKillTimer = setTimeout(() => {
        if (backendProcess && !backendProcess.killed) {
            console.warn('[PythonManager] Force killing backend process');
            backendProcess.kill('SIGKILL');
        }
    }, 5000);
    backendProcess.once('exit', () => {
        clearTimeout(forceKillTimer);
        backendProcess = null;
        console.log('[PythonManager] Backend stopped.');
    });
}
