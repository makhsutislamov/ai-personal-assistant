import { app, BrowserWindow, ipcMain } from "electron";
import * as path from "path";
import { SidecarManager } from "./sidecar";

let mainWindow: BrowserWindow | null = null;
let sidecar: SidecarManager | null = null;

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  if (process.env["NODE_ENV"] === "development") {
    await mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    await mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  sidecar = new SidecarManager();
  await sidecar.start();

  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("window-all-closed", async () => {
  if (sidecar) {
    await sidecar.stop();
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("get-backend-port", () => {
  return sidecar?.port ?? 8765;
});
