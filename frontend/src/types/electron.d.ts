// Electron API 类型声明
export interface ElectronAPI {
  getBackendPort: () => Promise<number>
  getServiceStatus: () => Promise<{
    status: 'running' | 'error' | 'stopped'
    port?: number
    pid?: number
    started_at?: string
  }>
  restartService: () => Promise<boolean>
  onServiceStatusChange: (callback: (status: any) => void) => void
  removeAllListeners: (channel: string) => void
}

export interface ServiceAPI {
  getSystemInfo: () => {
    platform: string
    arch: string
    nodeVersion: string
    electronVersion: string
  }
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
    serviceAPI: ServiceAPI
  }
}