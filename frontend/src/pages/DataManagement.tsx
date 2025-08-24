import React, { useState, useEffect } from 'react'
import { Card, Button, Table, Progress, Modal, Form, Select, DatePicker, InputNumber, Space, message, Tag } from 'antd'
import { DownloadOutlined, PlusOutlined, ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useDataStore, useAppStore } from '@/store'
import apiClient from '@/api/client'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const DataManagement: React.FC = () => {
  const [form] = Form.useForm()
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [loading, setLoading] = useState(false)
  
  const { labels, downloadTasks, addLabel, addDownloadTask } = useDataStore()
  const { dataStatus, setDataStatus } = useAppStore()

  // 预设标签规则
  const labelRules = [
    { value: '涨幅最大TOP20', label: '涨幅最大TOP20' },
    { value: '跌幅最大TOP20', label: '跌幅最大TOP20' },
    { value: '市值涨幅最大TOP20', label: '市值涨幅最大TOP20' },
    { value: '市值跌幅最大TOP20', label: '市值跌幅最大TOP20' },
    { value: '成交量最大TOP20', label: '成交量最大TOP20' },
    { value: '换手率最高TOP20', label: '换手率最高TOP20' }
  ]

  // 加载数据状态
  useEffect(() => {
    loadDataStatus()
    // 每30秒刷新一次数据状态
    const interval = setInterval(loadDataStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadDataStatus = async () => {
    try {
      const status = await apiClient.getDataStatus()
      setDataStatus({
        hasData: status.has_data,
        totalSymbols: status.total_symbols,
        dateRange: {
          start: status.date_range.start,
          end: status.date_range.end
        },
        lastUpdate: status.last_update
      })
    } catch (error) {
      console.error('获取数据状态失败:', error)
      setDataStatus({
        hasData: false,
        totalSymbols: 0,
        dateRange: { start: '', end: '' },
        lastUpdate: ''
      })
    }
  }

  // 执行下载
  const handleDownload = async (universe: 'nasdaq' | 'nyse') => {
    setLoading(true)
    try {
      const task = await apiClient.downloadData({
        universes: [universe],
        start_date: dayjs().subtract(2, 'year').format('YYYY-MM-DD'),
        end_date: dayjs().format('YYYY-MM-DD'),
        source: 'yfinance'
      })
      
      addDownloadTask({
        id: task.task_id,
        type: universe,
        status: task.status,
        progress: task.progress,
        message: task.message
      })
      
      message.success(`${universe.toUpperCase()}数据下载已开始`)
    } catch (error: any) {
      message.error(`下载失败: ${error.response?.data?.detail || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 创建标签
  const handleCreateLabel = async (values: any) => {
    try {
      const { rule, dateRange, topK, minMarketCap } = values
      const [startDate, endDate] = dateRange

      await apiClient.runLabelCalculation({
        rule,
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
        params: {
          top_k: topK || 20,
          min_market_cap: minMarketCap || 100000000
        }
      })

      const labelName = `${rule}_${startDate.format('YYYYMMDD')}_${endDate.format('YYYYMMDD')}`
      
      addLabel({
        name: labelName,
        rule,
        dateRange: `${startDate.format('YYYY-MM-DD')} 至 ${endDate.format('YYYY-MM-DD')}`,
        status: 'computing',
        recordCount: 0
      })

      message.success('标签计算已开始')
      setIsModalVisible(false)
      form.resetFields()
    } catch (error: any) {
      message.error(`创建标签失败: ${error.response?.data?.detail || error.message}`)
    }
  }

  // 标签表格列定义
  const labelColumns = [
    {
      title: '标签名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '筛选规则',
      dataIndex: 'rule',
      key: 'rule',
    },
    {
      title: '时间范围',
      dataIndex: 'dateRange',
      key: 'dateRange',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap = {
          'pending': { color: 'default', text: '等待中' },
          'computing': { color: 'processing', text: '计算中' },
          'completed': { color: 'success', text: '已完成' },
          'error': { color: 'error', text: '错误' }
        }
        const statusInfo = statusMap[status as keyof typeof statusMap] || statusMap.pending
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
      }
    },
    {
      title: '记录数',
      dataIndex: 'recordCount',
      key: 'recordCount',
      render: (count: number) => count.toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => handleUpdateLabel(record.name)}>
            更新计算
          </Button>
          <Button size="small" onClick={() => handleViewLabel(record.name)}>
            查看结果
          </Button>
        </Space>
      ),
    },
  ]

  const handleUpdateLabel = (_name: string) => {
    message.info('更新功能开发中')
  }

  const handleViewLabel = (_name: string) => {
    message.info('查看功能开发中')
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* 基础数据下载 */}
      <Card 
        title="基础数据下载" 
        className="content-card"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadDataStatus}>
            刷新状态
          </Button>
        }
      >
        <div style={{ marginBottom: '16px' }}>
          <div className="stat-card" style={{ marginBottom: '16px' }}>
            <div className="stat-value">{dataStatus.totalSymbols.toLocaleString()}</div>
            <div className="stat-label">股票总数</div>
          </div>
          {dataStatus.hasData && (
            <p>数据时间范围: {dataStatus.dateRange.start} 至 {dataStatus.dateRange.end}</p>
          )}
          {dataStatus.lastUpdate && (
            <p>最后更新: {dayjs(dataStatus.lastUpdate).format('YYYY-MM-DD HH:mm:ss')}</p>
          )}
        </div>
        
        <Space size="large">
          <div>
            <h4>纳斯达克数据</h4>
            <Button 
              type="primary" 
              icon={<DownloadOutlined />}
              loading={loading}
              onClick={() => handleDownload('nasdaq')}
            >
              执行下载
            </Button>
            <p style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
              约3000+股票
            </p>
          </div>
          
          <div>
            <h4>纽交所数据</h4>
            <Button 
              type="primary" 
              icon={<DownloadOutlined />}
              loading={loading}
              onClick={() => handleDownload('nyse')}
            >
              执行下载
            </Button>
            <p style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
              约2000+股票
            </p>
          </div>
        </Space>

        {/* 下载进度 */}
        {downloadTasks.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <h4>下载进度</h4>
            {downloadTasks.map(task => (
              <div key={task.id} style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>{task.type.toUpperCase()} - {task.message}</span>
                  <span>{task.progress}%</span>
                </div>
                <Progress percent={task.progress} status={task.status === 'failed' ? 'exception' : 'normal'} />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 数据标签管理 */}
      <Card 
        title="数据标签管理" 
        className="content-card"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalVisible(true)}>
            创建标签
          </Button>
        }
      >
        <Table
          columns={labelColumns}
          dataSource={labels}
          rowKey="name"
          pagination={{ pageSize: 10 }}
          className="data-table"
        />
      </Card>

      {/* 分钟级数据 */}
      <Card title="分钟级数据" className="content-card">
        <p style={{ color: '#666', marginBottom: '16px' }}>
          分钟级数据功能按需开发，当前版本主要支持日线数据。
        </p>
        <Button disabled>
          配置分钟数据 (按需)
        </Button>
      </Card>

      {/* 任务队列 */}
      <Card title="任务队列" className="content-card">
        <p style={{ color: '#666' }}>
          当前活跃任务将在此处显示，包括数据下载和标签计算任务。
        </p>
      </Card>

      {/* 创建标签模态框 */}
      <Modal
        title="创建数据标签"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateLabel}
          initialValues={{
            topK: 20,
            minMarketCap: 100000000
          }}
        >
          <Form.Item
            label="选择标签规则"
            name="rule"
            rules={[{ required: true, message: '请选择标签规则' }]}
          >
            <Select placeholder="选择筛选规则">
              {labelRules.map(rule => (
                <Select.Option key={rule.value} value={rule.value}>
                  {rule.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="计算时间范围"
            name="dateRange"
            rules={[{ required: true, message: '请选择时间范围' }]}
          >
            <RangePicker 
              style={{ width: '100%' }}
              defaultValue={[
                dayjs().subtract(2, 'year'),
                dayjs()
              ]}
            />
          </Form.Item>

          <Form.Item
            label="TOP K（保留数量）"
            name="topK"
            rules={[{ required: true, message: '请输入保留数量' }]}
          >
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="最小市值（美元）"
            name="minMarketCap"
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setIsModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />}>
                创建并计算
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataManagement