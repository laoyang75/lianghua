const { contextBridge, ipcRenderer } = require('electron');

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
  
  // 移除监听器
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});

// 为服务控制台提供额外的API
if (window.location.pathname.includes('service-console')) {
  contextBridge.exposeInMainWorld('serviceAPI', {
    getSystemInfo: () => ({
      platform: process.platform,
      arch: process.arch,
      nodeVersion: process.versions.node,
      electronVersion: process.versions.electron
    })
  });
}