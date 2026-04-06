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
const electron_1 = require("electron");
const path = __importStar(require("path"));
const crypto = __importStar(require("crypto"));
const python_manager_1 = require("./python-manager");
const isDev = process.env.NODE_ENV === 'development' || !electron_1.app.isPackaged;
let mainWindow = null;
let backendPort = null;
const authToken = crypto.randomBytes(32).toString('hex');
function createWindow(port) {
    mainWindow = new electron_1.BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 400,
        minHeight: 500,
        titleBarStyle: 'hiddenInset',
        backgroundColor: '#000000',
        show: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            additionalArguments: [
                `--backend-port=${port}`,
                `--auth-token=${authToken}`,
            ],
        },
    });
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools();
    }
    else {
        mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
    }
    mainWindow.once('ready-to-show', () => {
        mainWindow?.show();
    });
    // Open external links in the system browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        electron_1.shell.openExternal(url);
        return { action: 'deny' };
    });
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}
electron_1.app.whenReady().then(async () => {
    // Set Content-Security-Policy
    electron_1.session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        const csp = isDev
            ? "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:* ws://localhost:* http://localhost:*; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:"
            : "default-src 'self'; script-src 'self'; connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:*; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:";
        callback({
            responseHeaders: {
                ...details.responseHeaders,
                'Content-Security-Policy': [csp],
            },
        });
    });
    try {
        console.log('[Main] Starting Python backend...');
        backendPort = await (0, python_manager_1.startPythonBackend)(authToken);
        console.log(`[Main] Backend running on port ${backendPort}`);
        createWindow(backendPort);
    }
    catch (error) {
        console.error('[Main] Failed to start backend:', error);
        electron_1.app.quit();
    }
});
electron_1.app.on('window-all-closed', () => {
    (0, python_manager_1.stopPythonBackend)();
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
electron_1.app.on('activate', () => {
    if (mainWindow === null && backendPort !== null) {
        createWindow(backendPort);
    }
});
electron_1.app.on('before-quit', () => {
    (0, python_manager_1.stopPythonBackend)();
});
