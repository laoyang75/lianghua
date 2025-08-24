import axios, { AxiosResponse } from 'axios'
import { 
  ApiResponse, 
  HealthResponse, 
  DataStatusResponse,
  DataDownloadRequest,
  LabelRequest,
  Label,
  BacktestRequest,
  BacktestResult,
  Experiment,
  Task
} from '@/types/api'

class ApiClient {
  private baseURL: string
  private axiosInstance: any

  constructor() {
    this.baseURL = 'http://localhost:5318'
    this.setupAxios()
  }

  private setupAxios() {
    this.axiosInstance = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      (config: any) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error: any) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`[API] Response: ${response.status} ${response.config.url}`)
        return response
      },
      (error: any) => {
        console.error(`[API] Error: ${error.response?.status} ${error.config?.url}`, error.response?.data)
        return Promise.reject(error)
      }
    )
  }

  // 更新后端端口
  updatePort(port: number) {
    this.baseURL = `http://localhost:${port}`
    this.axiosInstance.defaults.baseURL = this.baseURL
  }

  // 健康检查
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.axiosInstance.get('/healthz')
    return response.data
  }

  // 获取数据状态
  async getDataStatus(): Promise<DataStatusResponse> {
    const response = await this.axiosInstance.get('/data/status')
    return response.data
  }

  // 数据下载
  async downloadData(request: DataDownloadRequest): Promise<Task> {
    const response = await this.axiosInstance.post('/data/download', request)
    return response.data
  }

  // 获取标签列表
  async getLabels(): Promise<{ labels: Label[] }> {
    const response = await this.axiosInstance.get('/labels/list')
    return response.data
  }

  // 运行标签计算
  async runLabelCalculation(request: LabelRequest): Promise<Task> {
    const response = await this.axiosInstance.post('/labels/run', request)
    return response.data
  }

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<Task> {
    const response = await this.axiosInstance.get(`/tasks/${taskId}`)
    return response.data
  }

  // 取消任务
  async cancelTask(taskId: string): Promise<ApiResponse> {
    const response = await this.axiosInstance.post(`/tasks/${taskId}/cancel`)
    return response.data
  }

  // 运行回测
  async runBacktest(request: BacktestRequest): Promise<BacktestResult> {
    const response = await this.axiosInstance.post('/backtest/run', request)
    return response.data
  }

  // 保存实验
  async saveExperiment(data: {
    strategy_name: string
    label_name: string
    cfg_json: any
    metrics_json: any
    result_hash: string
  }): Promise<Experiment> {
    const response = await this.axiosInstance.post('/experiments', data)
    return response.data
  }

  // 获取实验列表
  async getExperiments(params?: {
    offset?: number
    limit?: number
    strategy_name?: string
  }): Promise<{ experiments: Experiment[] }> {
    const response = await this.axiosInstance.get('/experiments', { params })
    return response.data
  }

  // 删除实验
  async deleteExperiment(experimentId: string): Promise<ApiResponse> {
    const response = await this.axiosInstance.delete(`/experiments/${experimentId}`)
    return response.data
  }

  // 复跑实验
  async rerunExperiment(experimentId: string): Promise<BacktestResult> {
    const response = await this.axiosInstance.post(`/experiments/${experimentId}/rerun`)
    return response.data
  }

  // 获取策略模板
  async getStrategyTemplates(): Promise<any> {
    const response = await this.axiosInstance.get('/strategies/templates')
    return response.data
  }

  // 导出报告
  async exportReport(data: {
    experiment_id?: string
    result_hash?: string
    format: 'png' | 'pdf'
  }): Promise<Blob> {
    const response = await this.axiosInstance.post('/export/report', data, {
      responseType: 'blob'
    })
    return response.data
  }
}

// WebSocket 客户端
export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private onMessageCallback: ((event: any) => void) | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 3000

  constructor(port: number = 5318) {
    this.url = `ws://localhost:${port}/ws/tasks`
  }

  connect(onMessage: (event: any) => void) {
    this.onMessageCallback = onMessage

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected')
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('[WebSocket] Message:', data)
          if (this.onMessageCallback) {
            this.onMessageCallback(data)
          }
        } catch (error) {
          console.error('[WebSocket] Parse error:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected')
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
      }
    } catch (error) {
      console.error('[WebSocket] Connection error:', error)
      this.attemptReconnect()
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`[WebSocket] Reconnect attempt ${this.reconnectAttempts}`)
      
      setTimeout(() => {
        if (this.onMessageCallback) {
          this.connect(this.onMessageCallback)
        }
      }, this.reconnectInterval)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.onMessageCallback = null
    this.reconnectAttempts = 0
  }

  updatePort(port: number) {
    this.url = `ws://localhost:${port}/ws/tasks`
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.disconnect()
      if (this.onMessageCallback) {
        this.connect(this.onMessageCallback)
      }
    }
  }
}

// 创建全局实例
export const apiClient = new ApiClient()
export const wsClient = new WebSocketClient()

// 导出默认实例
export default apiClient