import { app, BrowserWindow, shell } from 'electron'
import * as path from 'path'
import * as crypto from 'crypto'
import { startPythonBackend, stopPythonBackend } from './python-manager'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let backendPort: number | null = null
const authToken: string = crypto.randomBytes(32).toString('hex')

function createWindow(port: number): void {
  mainWindow = new BrowserWindow({
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
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  // Open external links in the system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  try {
    console.log('[Main] Starting Python backend...')
    backendPort = await startPythonBackend(authToken)
    console.log(`[Main] Backend running on port ${backendPort}`)
    createWindow(backendPort)
  } catch (error) {
    console.error('[Main] Failed to start backend:', error)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  stopPythonBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (mainWindow === null && backendPort !== null) {
    createWindow(backendPort)
  }
})

app.on('before-quit', () => {
  stopPythonBackend()
})
