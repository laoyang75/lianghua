const { contextBridge, ipcRenderer } = require('electron');
const os = require('os');
const process = require('process');

// 暴露API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 获取后端端口
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
  
  // 获取服务状态
  getServiceStatus: () => ipcRenderer.invoke('get-service-status'),
  
  // 重启服务
  restartService: () => ipcRenderer.invoke('restart-service'),
  
  // 监听服务状态变化
  onServiceStatusChange: (callback) => {
    ipcRenderer.on('service-status-change', (event, status) => {
      callback(status);
    });
  },
  
  // 监听日志更新
  onLogUpdate: (callback) => {
    ipcRenderer.on('log-update', callback);
  },
  
  // 移除监听器
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },
  
  // 系统信息
  getSystemInfo: () => ({
    platform: os.platform(),
    arch: os.arch(),
    nodeVersion: process.versions.node,
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome
  })
});

// 为服务控制台提供额外的API（向后兼容）
contextBridge.exposeInMainWorld('serviceAPI', {
  getSystemInfo: () => ({
    platform: os.platform(),
    arch: os.arch(),
    nodeVersion: process.versions.node,
    electronVersion: process.versions.electron
  })
});

console.log('服务控制台预加载脚本已加载');