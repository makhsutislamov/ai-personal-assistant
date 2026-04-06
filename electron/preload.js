"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
// Values passed from main process via additionalArguments in webPreferences
const args = process.argv;
const portArg = args.find((a) => a.startsWith('--backend-port='));
const tokenArg = args.find((a) => a.startsWith('--auth-token='));
const backendPort = portArg ? parseInt(portArg.split('=')[1], 10) : 8000;
const authToken = tokenArg ? tokenArg.split('=')[1] : '';
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    backendUrl: `http://127.0.0.1:${backendPort}`,
    authToken,
});
