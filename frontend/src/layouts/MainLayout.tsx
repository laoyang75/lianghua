import React, { useState, useEffect } from 'react'
import { Layout, Menu, Badge, Tooltip, Spin } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { 
  DatabaseOutlined, 
  SettingOutlined, 
  LineChartOutlined, 
  ExperimentOutlined, 
  HistoryOutlined,
  LoadingOutlined,
  MonitorOutlined
} from '@ant-design/icons'
import { useAppStore } from '@/store'
import { wsClient } from '@/api/client'

const { Sider, Content, Footer } = Layout

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed] = useState(false)

  const { 
    serviceStatus, 
    activeTasks, 
    backendPort,
    setServiceStatus, 
    updateTask, 
    removeTask 
  } = useAppStore()

  // 获取后端端口并连接WebSocket
  useEffect(() => {
    const initializeConnection = async () => {
      try {
        // 从Electron获取后端端口
        if (window.electronAPI) {
          const port = await window.electronAPI.getBackendPort()
          if (port !== backendPort) {
            // 更新端口并重新连接WebSocket
            wsClient.updatePort(port)
          }
        }

        // 连接WebSocket监听任务状态
        wsClient.connect((event) => {
          console.log('[DEBUG] WebSocket消息:', event)
          handleWebSocketMessage(event)
        })

        // 定期检查服务状态
        checkServiceStatus()
        const statusInterval = setInterval(checkServiceStatus, 30000)

        return () => {
          clearInterval(statusInterval)
          wsClient.disconnect()
        }
      } catch (error) {
        console.error('初始化连接失败:', error)
      }
    }

    initializeConnection()
  }, [])

  const checkServiceStatus = async () => {
    try {
      if (window.electronAPI) {
        const status = await window.electronAPI.getServiceStatus()
        setServiceStatus(status.status)
      }
    } catch (error) {
      console.error('检查服务状态失败:', error)
      setServiceStatus('error')
    }
  }

  const handleWebSocketMessage = (event: any) => {
    const { type, task_id, progress, message } = event

    switch (type) {
      case 'task_progress':
        updateTask(task_id, { progress, message })
        break
      case 'task_completed':
        updateTask(task_id, { status: 'completed', progress: 100, message })
        // 3秒后移除已完成的任务
        setTimeout(() => removeTask(task_id), 3000)
        break
      case 'task_failed':
        updateTask(task_id, { status: 'failed', message })
        break
      case 'task_cancelled':
        removeTask(task_id)
        break
    }
  }

  // 菜单项配置
  const menuItems = [
    {
      key: '/data',
      icon: <DatabaseOutlined />,
      label: '数据管理',
    },
    {
      key: '/strategy',
      icon: <SettingOutlined />,
      label: '策略管理',
    },
    {
      key: '/backtest',
      icon: <LineChartOutlined />,
      label: '回测',
    },
    {
      key: '/deeptest',
      icon: <ExperimentOutlined />,
      label: '深度测试',
    },
    {
      key: '/experiments',
      icon: <HistoryOutlined />,
      label: '历史实验',
    },
    {
      key: '/console',
      icon: <MonitorOutlined />,
      label: '服务控制台',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  const getSelectedKey = () => {
    const path = location.pathname
    if (path === '/' || path === '/data') return '/data'
    return path
  }

  const getServiceStatusInfo = () => {
    switch (serviceStatus) {
      case 'running':
        return { color: '#52c41a', text: '服务正常', icon: null }
      case 'error':
        return { color: '#ff4d4f', text: '服务异常', icon: <LoadingOutlined spin /> }
      case 'stopped':
      default:
        return { color: '#d9d9d9', text: '服务停止', icon: <LoadingOutlined spin /> }
    }
  }

  const statusInfo = getServiceStatusInfo()
  const runningTasks = activeTasks.filter(task => task.status === 'running' || task.status === 'queued')

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={240}
        style={{
          background: '#001529',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          boxShadow: '2px 0 8px rgba(0,0,0,0.15)'
        }}
      >
        {/* Logo区域 */}
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          borderBottom: '1px solid #374151'
        }}>
          <h3 style={{ 
            color: 'white', 
            margin: 0,
            fontSize: collapsed ? '14px' : '16px',
            transition: 'font-size 0.2s'
          }}>
            {collapsed ? '量化' : '量化回测系统'}
          </h3>
        </div>

        {/* 导航菜单 */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          onClick={handleMenuClick}
          style={{ 
            background: '#001529', 
            border: 'none',
            padding: '16px 0',
            color: '#ffffff'
          }}
          className="sidebar-menu"
          items={menuItems.map(item => ({
            ...item,
            label: (
              <Badge 
                count={
                  item.key === '/data' && runningTasks.length > 0 
                    ? runningTasks.length 
                    : 0
                } 
                size="small"
                offset={[10, 0]}
              >
                {item.label}
              </Badge>
            )
          }))}
        />

        {/* 底部状态栏 */}
        {!collapsed && (
          <div style={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            right: 16,
            padding: '12px',
            background: 'rgba(0, 21, 41, 0.8)',
            borderRadius: '6px',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center',
              justifyContent: 'space-between',
              color: 'white',
              fontSize: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div 
                  className="status-indicator" 
                  style={{ 
                    backgroundColor: statusInfo.color,
                    marginRight: '6px',
                    width: '8px',
                    height: '8px' 
                  }}
                />
                <span>{statusInfo.text}</span>
                {statusInfo.icon && <span style={{ marginLeft: '4px' }}>{statusInfo.icon}</span>}
              </div>
              {serviceStatus === 'running' && (
                <Tooltip title={`端口: ${backendPort}`}>
                  <span style={{ opacity: 0.7 }}>:{backendPort}</span>
                </Tooltip>
              )}
            </div>
          </div>
        )}
      </Sider>

      {/* 主内容区 */}
      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: 'margin-left 0.2s' }}>
        {/* 顶部区域 - 可以用于显示任务进度等信息 */}
        {runningTasks.length > 0 && (
          <div style={{
            background: '#f0f2f5',
            padding: '8px 24px',
            borderBottom: '1px solid #e8e8e8'
          }}>
            {runningTasks.map(task => (
              <div key={task.id} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                fontSize: '12px',
                color: '#666'
              }}>
                <Spin size="small" />
                <span>{task.message}</span>
                <span>{task.progress}%</span>
              </div>
            ))}
          </div>
        )}

        {/* 页面内容 */}
        <Content
          className="main-content"
          style={{
            margin: 0,
            minHeight: 'calc(100vh - 64px)',
            background: '#f0f2f5',
            overflow: 'auto'
          }}
        >
          {children}
        </Content>

        {/* 底部信息 */}
        <Footer style={{ 
          textAlign: 'center', 
          background: '#f0f2f5',
          borderTop: '1px solid #e8e8e8',
          padding: '12px 24px'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>
            量化回测系统 v1.0.0 | 基于 Electron + FastAPI + DuckDB 构建
          </div>
        </Footer>
      </Layout>
    </Layout>
  )
}

export default MainLayout