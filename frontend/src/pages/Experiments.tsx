import React, { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, Popconfirm, message, Modal, Descriptions, DatePicker, Select, Input } from 'antd'
import { EyeOutlined, PlayCircleOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { useExperimentStore } from '@/store'
import apiClient from '@/api/client'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const Experiments: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedExperiment, setSelectedExperiment] = useState<any>(null)
  const [filters, setFilters] = useState({
    strategyName: '',
    dateRange: null as any,
    minReturn: null as number | null
  })

  const { experiments, loadExperiments, removeExperiment } = useExperimentStore()

  useEffect(() => {
    loadExperimentData()
  }, [])

  const loadExperimentData = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getExperiments()
      loadExperiments(response.experiments)
    } catch (error) {
      console.error('加载实验数据失败:', error)
      message.error('加载实验数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetails = (experiment: any) => {
    setSelectedExperiment(experiment)
    setDetailVisible(true)
  }

  const handleRerun = async (experiment: any) => {
    try {
      message.loading({ content: '正在复跑实验...', key: 'rerun', duration: 0 })
      const result = await apiClient.rerunExperiment(experiment.id)
      
      // 验证result_hash是否一致
      if (result.result_hash === experiment.result_hash) {
        message.success({ content: '复跑成功，结果一致', key: 'rerun' })
      } else {
        message.warning({ 
          content: '复跑成功，但结果哈希值不一致，可能数据已更新', 
          key: 'rerun' 
        })
      }
    } catch (error: any) {
      message.error({ 
        content: `复跑失败: ${error.response?.data?.detail || error.message}`, 
        key: 'rerun' 
      })
    }
  }

  const handleDelete = async (experimentId: string) => {
    try {
      await apiClient.deleteExperiment(experimentId)
      removeExperiment(experimentId)
      message.success('实验已删除')
    } catch (error: any) {
      message.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  }

  const getReturnColor = (returnValue: number) => {
    if (returnValue > 0.1) return '#52c41a' // 绿色：>10%
    if (returnValue > 0) return '#1890ff'   // 蓝色：>0%
    return '#ff4d4f'                        // 红色：<0%
  }

  const getSharpeColor = (sharpe: number) => {
    if (sharpe > 1.5) return '#52c41a'      // 绿色：>1.5
    if (sharpe > 1) return '#1890ff'        // 蓝色：>1
    if (sharpe > 0.5) return '#faad14'      // 黄色：>0.5
    return '#ff4d4f'                        // 红色：<=0.5
  }

  // 筛选后的数据
  const filteredExperiments = experiments.filter(exp => {
    if (filters.strategyName && !exp.strategyName.includes(filters.strategyName)) {
      return false
    }
    if (filters.dateRange) {
      const [start, end] = filters.dateRange
      const expDate = dayjs(exp.createdAt)
      if (expDate.isBefore(start) || expDate.isAfter(end)) {
        return false
      }
    }
    if (filters.minReturn !== null && exp.metrics.totalReturn < filters.minReturn / 100) {
      return false
    }
    return true
  })

  // 表格列定义
  const columns = [
    {
      title: '编号',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => id.slice(-6).toUpperCase()
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
      sorter: (a: any, b: any) => dayjs(a.createdAt).valueOf() - dayjs(b.createdAt).valueOf(),
      defaultSortOrder: 'descend' as const
    },
    {
      title: '策略名称',
      dataIndex: 'strategyName',
      key: 'strategyName',
      width: 150,
      render: (name: string) => (
        <Tag color={name.includes('下跌') ? 'blue' : 'green'}>
          {name}
        </Tag>
      )
    },
    {
      title: '数据标签',
      dataIndex: 'labelName',
      key: 'labelName',
      width: 200,
      ellipsis: true
    },
    {
      title: '年化收益',
      dataIndex: ['metrics', 'annualReturn'],
      key: 'annualReturn',
      width: 120,
      render: (value: number) => (
        <span style={{ color: getReturnColor(value), fontWeight: 'bold' }}>
          {(value * 100).toFixed(2)}%
        </span>
      ),
      sorter: (a: any, b: any) => a.metrics.annualReturn - b.metrics.annualReturn
    },
    {
      title: '最大回撤',
      dataIndex: ['metrics', 'maxDrawdown'],
      key: 'maxDrawdown',
      width: 120,
      render: (value: number) => (
        <span style={{ color: value < -0.2 ? '#ff4d4f' : '#666' }}>
          {(value * 100).toFixed(2)}%
        </span>
      ),
      sorter: (a: any, b: any) => b.metrics.maxDrawdown - a.metrics.maxDrawdown
    },
    {
      title: '夏普比率',
      dataIndex: ['metrics', 'sharpeRatio'],
      key: 'sharpeRatio',
      width: 120,
      render: (value: number) => (
        <span style={{ color: getSharpeColor(value), fontWeight: 'bold' }}>
          {value.toFixed(2)}
        </span>
      ),
      sorter: (a: any, b: any) => a.metrics.sharpeRatio - b.metrics.sharpeRatio
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            查看
          </Button>
          <Button 
            size="small" 
            icon={<PlayCircleOutlined />}
            onClick={() => handleRerun(record)}
          >
            复跑
          </Button>
          <Popconfirm
            title="确定删除此实验吗？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okType="danger"
          >
            <Button 
              size="small" 
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2>历史实验</h2>
        <p style={{ color: '#666' }}>
          查看和管理所有保存的回测实验，支持复跑验证和结果对比分析。
        </p>
      </div>

      {/* 筛选条件 */}
      <Card title="筛选条件" className="content-card" style={{ marginBottom: '24px' }}>
        <Space size="large" wrap>
          <div>
            <label style={{ marginRight: '8px' }}>策略名称:</label>
            <Input
              placeholder="输入策略名称"
              value={filters.strategyName}
              onChange={(e) => setFilters(prev => ({ ...prev, strategyName: e.target.value }))}
              style={{ width: 200 }}
              allowClear
            />
          </div>
          
          <div>
            <label style={{ marginRight: '8px' }}>创建时间:</label>
            <RangePicker
              value={filters.dateRange}
              onChange={(dates) => setFilters(prev => ({ ...prev, dateRange: dates }))}
              style={{ width: 300 }}
            />
          </div>

          <div>
            <label style={{ marginRight: '8px' }}>最小收益率:</label>
            <Select
              placeholder="选择最小收益率"
              value={filters.minReturn}
              onChange={(value) => setFilters(prev => ({ ...prev, minReturn: value }))}
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value={0}>0%</Select.Option>
              <Select.Option value={5}>5%</Select.Option>
              <Select.Option value={10}>10%</Select.Option>
              <Select.Option value={20}>20%</Select.Option>
            </Select>
          </div>

          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => setFilters({ strategyName: '', dateRange: null, minReturn: null })}
          >
            重置
          </Button>
        </Space>
      </Card>

      {/* 实验列表 */}
      <Card 
        title={`实验列表 (${filteredExperiments.length}/${experiments.length})`}
        className="content-card"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadExperimentData} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredExperiments}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          className="data-table"
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 详情模态框 */}
      <Modal
        title={`实验详情 - ${selectedExperiment?.id?.slice(-6).toUpperCase()}`}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedExperiment && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="策略名称">
                {selectedExperiment.strategyName}
              </Descriptions.Item>
              <Descriptions.Item label="数据标签">
                {selectedExperiment.labelName}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedExperiment.createdAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="结果哈希">
                <code style={{ fontSize: '12px' }}>
                  {selectedExperiment.resultHash.slice(0, 16)}...
                </code>
              </Descriptions.Item>
              <Descriptions.Item label="总收益率">
                <span style={{ color: getReturnColor(selectedExperiment.metrics.totalReturn) }}>
                  {(selectedExperiment.metrics.totalReturn * 100).toFixed(2)}%
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="年化收益">
                <span style={{ color: getReturnColor(selectedExperiment.metrics.annualReturn) }}>
                  {(selectedExperiment.metrics.annualReturn * 100).toFixed(2)}%
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="最大回撤">
                {(selectedExperiment.metrics.maxDrawdown * 100).toFixed(2)}%
              </Descriptions.Item>
              <Descriptions.Item label="夏普比率">
                <span style={{ color: getSharpeColor(selectedExperiment.metrics.sharpeRatio) }}>
                  {selectedExperiment.metrics.sharpeRatio.toFixed(2)}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="卡尔玛比率">
                {selectedExperiment.metrics.calmarRatio?.toFixed(2) || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="胜率">
                {selectedExperiment.metrics.winRate ? 
                  `${(selectedExperiment.metrics.winRate * 100).toFixed(2)}%` : 'N/A'
                }
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <Space>
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />}
                  onClick={() => {
                    handleRerun(selectedExperiment)
                    setDetailVisible(false)
                  }}
                >
                  复跑实验
                </Button>
                <Button 
                  onClick={() => setDetailVisible(false)}
                >
                  关闭
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Experiments