const { app, BrowserWindow, Menu, dialog, shell, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');
const os = require('os');

// 开发环境检测
const isDev = process.env.NODE_ENV === 'development';

// 全局变量
let mainWindow;
let serviceConsoleWindow;
let backendProcess;
let backendPort = 5317;
let lockFilePath;

// 端口池
const PORT_POOL = [5317, ...Array.from({length: 30}, (_, i) => 5320 + i)];

// 初始化锁文件路径
function initLockFilePath() {
  const userDataPath = app.getPath('userData');
  const configDir = path.join(userDataPath, '.quant-backtest');
  
  // 确保配置目录存在
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }
  
  lockFilePath = path.join(configDir, 'service.lock');
}

// 端口检测
function isPortInUse(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(port, (err) => {
      if (err) {
        resolve(true); // 端口被占用
      } else {
        server.once('close', () => {
          resolve(false); // 端口空闲
        });
        server.close();
      }
    });
    server.on('error', (err) => {
      resolve(true); // 端口被占用
    });
  });
}

// 查找可用端口
async function findAvailablePort() {
  for (const port of PORT_POOL) {
    const inUse = await isPortInUse(port);
    if (!inUse) {
      return port;
    }
  }
  return null;
}

// 读取锁文件
function readLockFile() {
  try {
    if (fs.existsSync(lockFilePath)) {
      const content = fs.readFileSync(lockFilePath, 'utf8');
      return JSON.parse(content);
    }
  } catch (error) {
    console.error('读取锁文件失败:', error);
  }
  return null;
}

// 写入锁文件
function writeLockFile(port, pid) {
  try {
    const lockData = {
      pid,
      port,
      started_at: new Date().toISOString()
    };
    fs.writeFileSync(lockFilePath, JSON.stringify(lockData, null, 2));
    return true;
  } catch (error) {
    console.error('写入锁文件失败:', error);
    return false;
  }
}

// 删除锁文件
function removeLockFile() {
  try {
    if (fs.existsSync(lockFilePath)) {
      fs.unlinkSync(lockFilePath);
    }
  } catch (error) {
    console.error('删除锁文件失败:', error);
  }
}

// 检查进程是否存在
function isProcessRunning(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return false;
  }
}

// 健康检查
async function healthCheck(port) {
  return new Promise((resolve) => {
    const http = require('http');
    const req = http.get(`http://localhost:${port}/healthz`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => {
      resolve(false);
    });
    req.setTimeout(5000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// 启动后端服务
async function startBackendService() {
  // 检查现有锁文件
  const lockData = readLockFile();
  if (lockData) {
    // 检查进程是否仍在运行
    if (isProcessRunning(lockData.pid)) {
      // 检查端口健康状态
      const isHealthy = await healthCheck(lockData.port);
      if (isHealthy) {
        backendPort = lockData.port;
        console.log(`后端服务已在端口 ${lockData.port} 运行，PID: ${lockData.pid}`);
        return true;
      }
    }
    // 清理过期锁文件
    removeLockFile();
  }

  // 查找可用端口
  const availablePort = await findAvailablePort();
  if (!availablePort) {
    dialog.showErrorBox('端口冲突', '无法找到可用端口，请检查端口占用情况');
    return false;
  }

  // 启动新的后端进程
  try {
    const pythonCommand = process.platform === 'win32' ? 'py' : 'python3';
    const backendPath = isDev 
      ? path.join(process.cwd(), '..', 'backend')
      : path.join(process.resourcesPath, 'backend');

    backendProcess = spawn(pythonCommand, ['-m', 'app.main', '--port', availablePort.toString()], {
      cwd: backendPath,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // 监听进程输出
    backendProcess.stdout.on('data', (data) => {
      console.log(`后端输出: ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`后端错误: ${data}`);
    });

    backendProcess.on('close', (code) => {
      console.log(`后端进程退出，代码: ${code}`);
      removeLockFile();
      backendProcess = null;
    });

    // 等待服务启动
    await new Promise(resolve => setTimeout(resolve, 3000));

    // 健康检查
    const isHealthy = await healthCheck(availablePort);
    if (isHealthy) {
      backendPort = availablePort;
      writeLockFile(availablePort, backendProcess.pid);
      console.log(`后端服务成功启动在端口 ${availablePort}`);
      return true;
    } else {
      throw new Error('后端服务启动失败');
    }

  } catch (error) {
    console.error('启动后端服务失败:', error);
    dialog.showErrorBox('服务启动失败', `无法启动后端服务: ${error.message}`);
    return false;
  }
}

// 停止后端服务
function stopBackendService() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
  removeLockFile();
}

// 创建主窗口
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../assets/icon.png') // 如果有图标
  });

  // 加载应用
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // 窗口事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 创建服务控制台窗口
function createServiceConsoleWindow() {
  if (serviceConsoleWindow) {
    serviceConsoleWindow.focus();
    return;
  }

  serviceConsoleWindow = new BrowserWindow({
    width: 800,
    height: 600,
    parent: mainWindow,
    modal: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  serviceConsoleWindow.loadFile(path.join(__dirname, 'service-console.html'));

  serviceConsoleWindow.on('closed', () => {
    serviceConsoleWindow = null;
  });
}

// 创建菜单
function createMenu() {
  const template = [
    {
      label: '文件',
      submenu: [
        {
          label: '退出',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          }
        }
      ]
    },
    {
      label: '系统',
      submenu: [
        {
          label: '服务控制台',
          click: () => {
            createServiceConsoleWindow();
          }
        }
      ]
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: '关于量化回测系统',
              message: '量化回测系统 v1.0.0',
              detail: '基于Electron + FastAPI + DuckDB构建的桌面量化回测工具'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// IPC 处理程序
ipcMain.handle('get-backend-port', () => {
  return backendPort;
});

ipcMain.handle('get-service-status', async () => {
  const lockData = readLockFile();
  if (!lockData) {
    return { status: 'stopped' };
  }

  const isRunning = isProcessRunning(lockData.pid);
  const isHealthy = isRunning ? await healthCheck(lockData.port) : false;

  return {
    status: isHealthy ? 'running' : 'error',
    port: lockData.port,
    pid: lockData.pid,
    started_at: lockData.started_at
  };
});

ipcMain.handle('restart-service', async () => {
  stopBackendService();
  await new Promise(resolve => setTimeout(resolve, 2000));
  return await startBackendService();
});

// 应用事件
app.whenReady().then(async () => {
  initLockFilePath();
  
  // 启动后端服务
  const serviceStarted = await startBackendService();
  if (!serviceStarted) {
    console.error('后端服务启动失败，应用将退出');
    app.quit();
    return;
  }

  createMainWindow();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopBackendService();
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackendService();
});

// 防止多个实例
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  dialog.showErrorBox('重复启动', '量化回测系统已经在运行中');
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}