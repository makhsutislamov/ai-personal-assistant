import { contextBridge, ipcRenderer } from "electron";

const validChannels = ["get-backend-port"] as const;
type ValidChannel = (typeof validChannels)[number];

contextBridge.exposeInMainWorld("electronAPI", {
  getBackendPort: (): Promise<number> =>
    ipcRenderer.invoke("get-backend-port" satisfies ValidChannel),
});

export type ElectronAPI = {
  getBackendPort: () => Promise<number>;
};
