import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// 应用状态接口
interface AppState {
  // 系统状态
  backendPort: number
  serviceStatus: 'running' | 'error' | 'stopped'
  
  // 数据状态
  dataStatus: {
    hasData: boolean
    totalSymbols: number
    dateRange: {
      start: string
      end: string
    }
    lastUpdate: string
  }
  
  // 任务状态
  activeTasks: Array<{
    id: string
    type: string
    status: string
    progress: number
    message: string
  }>
  
  // 当前选择的策略
  currentStrategy: {
    name: string
    type: string
    parameters: Record<string, any>
  } | null
  
  // Actions
  setBackendPort: (port: number) => void
  setServiceStatus: (status: 'running' | 'error' | 'stopped') => void
  setDataStatus: (status: any) => void
  addTask: (task: any) => void
  updateTask: (id: string, updates: any) => void
  removeTask: (id: string) => void
  setCurrentStrategy: (strategy: any) => void
}

// 主应用状态
export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // 初始状态
        backendPort: 5318,
        serviceStatus: 'stopped',
        dataStatus: {
          hasData: false,
          totalSymbols: 0,
          dateRange: {
            start: '',
            end: ''
          },
          lastUpdate: ''
        },
        activeTasks: [],
        currentStrategy: null,

        // Actions
        setBackendPort: (port) => 
          set({ backendPort: port }, false, 'setBackendPort'),
        
        setServiceStatus: (status) => 
          set({ serviceStatus: status }, false, 'setServiceStatus'),
        
        setDataStatus: (status) => 
          set({ dataStatus: { ...get().dataStatus, ...status } }, false, 'setDataStatus'),
        
        addTask: (task) => 
          set((state) => ({ 
            activeTasks: [...state.activeTasks, task] 
          }), false, 'addTask'),
        
        updateTask: (id, updates) => 
          set((state) => ({
            activeTasks: state.activeTasks.map(task =>
              task.id === id ? { ...task, ...updates } : task
            )
          }), false, 'updateTask'),
        
        removeTask: (id) => 
          set((state) => ({
            activeTasks: state.activeTasks.filter(task => task.id !== id)
          }), false, 'removeTask'),
        
        setCurrentStrategy: (strategy) => 
          set({ currentStrategy: strategy }, false, 'setCurrentStrategy'),
      }),
      {
        name: 'quant-backtest-storage',
        partialize: (state) => ({
          currentStrategy: state.currentStrategy,
          dataStatus: state.dataStatus
        })
      }
    )
  )
)

// 数据管理状态
interface DataState {
  labels: Array<{
    name: string
    rule: string
    dateRange: string
    status: 'pending' | 'computing' | 'completed' | 'error'
    recordCount: number
  }>
  downloadTasks: Array<{
    id: string
    type: 'nasdaq' | 'nyse' | 'update'
    status: 'queued' | 'running' | 'completed' | 'failed'
    progress: number
    message: string
  }>
  
  // Actions
  addLabel: (label: any) => void
  updateLabel: (name: string, updates: any) => void
  removeLabel: (name: string) => void
  addDownloadTask: (task: any) => void
  updateDownloadTask: (id: string, updates: any) => void
}

export const useDataStore = create<DataState>()(
  devtools((set) => ({
    labels: [],
    downloadTasks: [],
    
    addLabel: (label) => 
      set((state) => ({ labels: [...state.labels, label] }), false, 'addLabel'),
    
    updateLabel: (name, updates) => 
      set((state) => ({
        labels: state.labels.map(label =>
          label.name === name ? { ...label, ...updates } : label
        )
      }), false, 'updateLabel'),
    
    removeLabel: (name) => 
      set((state) => ({
        labels: state.labels.filter(label => label.name !== name)
      }), false, 'removeLabel'),
    
    addDownloadTask: (task) => 
      set((state) => ({ downloadTasks: [...state.downloadTasks, task] }), false, 'addDownloadTask'),
    
    updateDownloadTask: (id, updates) => 
      set((state) => ({
        downloadTasks: state.downloadTasks.map(task =>
          task.id === id ? { ...task, ...updates } : task
        )
      }), false, 'updateDownloadTask'),
  }))
)

// 回测状态
interface BacktestState {
  results: {
    metrics: {
      totalReturn: number
      annualReturn: number
      maxDrawdown: number
      sharpeRatio: number
    } | null
    equityCurve: Array<{ date: string; value: number }>
    trades: Array<{
      batch: number
      symbol: string
      buyDate: string
      sellDate: string
      buyPrice: number
      sellPrice: number
      return: number
    }>
    resultHash: string
  } | null
  
  isRunning: boolean
  progress: number
  
  // Actions
  setResults: (results: any) => void
  setRunning: (running: boolean) => void
  setProgress: (progress: number) => void
  clearResults: () => void
}

export const useBacktestStore = create<BacktestState>()(
  devtools((set) => ({
    results: null,
    isRunning: false,
    progress: 0,
    
    setResults: (results) => 
      set({ results }, false, 'setResults'),
    
    setRunning: (isRunning) => 
      set({ isRunning }, false, 'setRunning'),
    
    setProgress: (progress) => 
      set({ progress }, false, 'setProgress'),
    
    clearResults: () => 
      set({ results: null, progress: 0 }, false, 'clearResults'),
  }))
)

// 实验管理状态
interface ExperimentState {
  experiments: Array<{
    id: string
    createdAt: string
    strategyName: string
    labelName: string
    metrics: {
      totalReturn: number
      annualReturn: number
      maxDrawdown: number
      sharpeRatio: number
    }
    resultHash: string
  }>
  
  // Actions
  addExperiment: (experiment: any) => void
  removeExperiment: (id: string) => void
  loadExperiments: (experiments: any[]) => void
}

export const useExperimentStore = create<ExperimentState>()(
  devtools(
    persist(
      (set) => ({
        experiments: [],
        
        addExperiment: (experiment) => 
          set((state) => ({ 
            experiments: [experiment, ...state.experiments] 
          }), false, 'addExperiment'),
        
        removeExperiment: (id) => 
          set((state) => ({
            experiments: state.experiments.filter(exp => exp.id !== id)
          }), false, 'removeExperiment'),
        
        loadExperiments: (experiments) => 
          set({ experiments }, false, 'loadExperiments'),
      }),
      {
        name: 'experiments-storage',
      }
    )
  )
)