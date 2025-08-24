import React, { useState, useEffect } from 'react'
import { Card, Button, Form, Select, DatePicker, InputNumber, Space, Alert, Progress, message, Table } from 'antd'
import { PlayCircleOutlined, SaveOutlined, ExportOutlined } from '@ant-design/icons'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useAppStore, useBacktestStore } from '@/store'
import apiClient from '@/api/client'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const Backtest: React.FC = () => {
  const [form] = Form.useForm()
  const [availableLabels, setAvailableLabels] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const { currentStrategy } = useAppStore()
  const { results, isRunning, progress, setResults, setRunning, setProgress } = useBacktestStore()

  useEffect(() => {
    loadAvailableLabels()
  }, [])

  const loadAvailableLabels = async () => {
    try {
      const response = await apiClient.getLabels()
      setAvailableLabels(response.labels.filter(label => label.status === 'done'))
    } catch (error) {
      console.error('加载标签失败:', error)
    }
  }

  const handleRunBacktest = async (values: any) => {
    if (!currentStrategy) {
      message.error('请先选择策略')
      return
    }

    setLoading(true)
    setRunning(true)
    setProgress(0)

    try {
      const { labelName, dateRange, filterRules } = values
      const [startDate, endDate] = dateRange

      const backtestRequest = {
        strategy_cfg: {
          name: currentStrategy.name,
          buy_timing: currentStrategy.parameters.buy_timing,
          sell_timing: currentStrategy.parameters.sell_timing,
          hold_days: currentStrategy.parameters.hold_days,
          execution_frequency: currentStrategy.parameters.execution_frequency,
          execution_count: currentStrategy.parameters.execution_count,
          positioning: currentStrategy.parameters.positioning,
          initial_capital: currentStrategy.parameters.initial_capital,
          filter_rules: {
            ...currentStrategy.parameters.filter_rules,
            ...filterRules
          }
        },
        label_name: labelName,
        date_range: {
          start: startDate.format('YYYY-MM-DD'),
          end: endDate.format('YYYY-MM-DD')
        }
      }

      // 模拟进度更新
      let currentProgress = progress
      const progressInterval = setInterval(() => {
        currentProgress = Math.min(currentProgress + 10, 90)
        setProgress(currentProgress)
      }, 500)

      const result = await apiClient.runBacktest(backtestRequest)
      
      clearInterval(progressInterval)
      setProgress(100)
      setResults(result)
      message.success('回测完成！')

    } catch (error: any) {
      message.error(`回测失败: ${error.response?.data?.detail || error.message}`)
    } finally {
      setLoading(false)
      setRunning(false)
      setTimeout(() => setProgress(0), 2000)
    }
  }

  const handleSaveExperiment = async () => {
    if (!results || !currentStrategy) {
      message.error('没有可保存的回测结果')
      return
    }

    try {
      const formValues = form.getFieldsValue()
      await apiClient.saveExperiment({
        strategy_name: currentStrategy.name,
        label_name: formValues.labelName,
        cfg_json: currentStrategy.parameters,
        metrics_json: results.metrics,
        result_hash: results.resultHash
      })
      message.success('实验已保存')
    } catch (error: any) {
      message.error(`保存失败: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleExportReport = async () => {
    if (!results) {
      message.error('没有可导出的结果')
      return
    }

    try {
      const blob = await apiClient.exportReport({
        result_hash: results.resultHash,
        format: 'png'
      })
      
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `回测报告_${dayjs().format('YYYYMMDD_HHmmss')}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      message.success('报告导出成功')
    } catch (error: any) {
      message.error(`导出失败: ${error.response?.data?.detail || error.message}`)
    }
  }

  // 交易明细表格列
  const tradeColumns = [
    { title: '批次', dataIndex: 'batch', key: 'batch' },
    { title: '股票代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '买入日期', dataIndex: 'buy_date', key: 'buy_date' },
    { title: '卖出日期', dataIndex: 'sell_date', key: 'sell_date' },
    { title: '买入价格', dataIndex: 'buy_price', key: 'buy_price', render: (value: number) => `$${value.toFixed(2)}` },
    { title: '卖出价格', dataIndex: 'sell_price', key: 'sell_price', render: (value: number) => `$${value.toFixed(2)}` },
    { title: '收益率', dataIndex: 'return_pct', key: 'return_pct', render: (value: number) => `${(value * 100).toFixed(2)}%` }
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 当前策略显示 */}
      {currentStrategy && (
        <Alert
          message={`当前策略: ${currentStrategy.name}`}
          description={`策略描述 | 持仓${currentStrategy.parameters.hold_days}天 | 每${currentStrategy.parameters.execution_frequency}天执行 | 共执行${currentStrategy.parameters.execution_count}次`}
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
          action={
            <Button size="small" onClick={() => window.location.href = '/strategy'}>
              🔄 更换策略
            </Button>
          }
        />
      )}

      {!currentStrategy && (
        <Alert
          message="请先选择策略"
          description="请前往策略管理页面选择一个策略模板"
          type="warning"
          showIcon
          style={{ marginBottom: '24px' }}
          action={
            <Button type="primary" size="small" onClick={() => window.location.href = '/strategy'}>
              选择策略
            </Button>
          }
        />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1fr) 2fr', gap: '24px' }}>
        {/* 配置面板 */}
        <div>
          <Card title="回测配置" className="content-card">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleRunBacktest}
              disabled={isRunning}
              initialValues={{
                dateRange: [dayjs().subtract(1, 'year'), dayjs()],
                minMarketCap: 100000000,
                maxDropPct: -60,
                topK: 5
              }}
            >
              {/* 步骤1：选择数据源 */}
              <div className="form-section">
                <div className="form-section-title">步骤1：选择数据源</div>
                <Form.Item
                  label="选择标签"
                  name="labelName"
                  rules={[{ required: true, message: '请选择数据标签' }]}
                >
                  <Select 
                    placeholder="选择已计算的标签"
                    loading={availableLabels.length === 0}
                    notFoundContent="暂无可用标签，请先到数据管理页面创建"
                  >
                    {availableLabels.map(label => (
                      <Select.Option key={label.name} value={label.name}>
                        {label.rule} ({label.date_range})
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  label="回测时间范围"
                  name="dateRange"
                  rules={[{ required: true, message: '请选择时间范围' }]}
                >
                  <RangePicker style={{ width: '100%' }} />
                </Form.Item>
              </div>

              {/* 步骤2：设置过滤规则 */}
              <div className="form-section">
                <div className="form-section-title">步骤2：设置过滤规则</div>
                <Form.Item label="最小市值（美元）" name={['filterRules', 'minMarketCap']}>
                  <InputNumber 
                    min={0} 
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Form.Item label="最大跌幅限制(%)" name={['filterRules', 'maxDropPct']}>
                  <InputNumber min={-100} max={0} style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item label="保留股票数" name={['filterRules', 'topK']}>
                  <InputNumber min={1} max={20} style={{ width: '100%' }} />
                </Form.Item>
              </div>

              {/* 步骤3：执行回测 */}
              <div className="form-section">
                <div className="form-section-title">步骤3：执行回测</div>
                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    loading={loading}
                    disabled={!currentStrategy}
                    icon={<PlayCircleOutlined />}
                    block
                    size="large"
                  >
                    ⚡ 运行回测
                  </Button>
                </Form.Item>

                {isRunning && (
                  <div className="progress-container">
                    <div className="progress-text">回测进度</div>
                    <Progress percent={progress} />
                  </div>
                )}
              </div>
            </Form>
          </Card>
        </div>

        {/* 结果展示 */}
        <div>
          {results ? (
            <div className="result-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3>回测结果</h3>
                <Space>
                  <Button icon={<SaveOutlined />} onClick={handleSaveExperiment}>
                    💾 保存为实验
                  </Button>
                  <Button icon={<ExportOutlined />} onClick={handleExportReport}>
                    📊 导出报告
                  </Button>
                </Space>
              </div>

              {/* 关键指标 */}
              <div className="result-metrics">
                <div className="metric-item">
                  <div className="metric-value">{results.metrics && (results.metrics.totalReturn * 100).toFixed(2)}%</div>
                  <div className="metric-label">总收益率</div>
                </div>
                <div className="metric-item">
                  <div className="metric-value">{results.metrics && (results.metrics.annualReturn * 100).toFixed(2)}%</div>
                  <div className="metric-label">年化收益</div>
                </div>
                <div className="metric-item">
                  <div className="metric-value">{results.metrics && (results.metrics.maxDrawdown * 100).toFixed(2)}%</div>
                  <div className="metric-label">最大回撤</div>
                </div>
                <div className="metric-item">
                  <div className="metric-value">{results.metrics && results.metrics.sharpeRatio.toFixed(2)}</div>
                  <div className="metric-label">夏普比率</div>
                </div>
              </div>

              {/* 净值曲线 */}
              <div className="chart-container">
                <h4>净值曲线</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={results.equityCurve}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#1890ff" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* 交易明细 */}
              <div style={{ marginTop: '24px' }}>
                <h4>交易明细</h4>
                <Table
                  columns={tradeColumns}
                  dataSource={results.trades}
                  rowKey={(record, index) => `${record.symbol}_${index}`}
                  pagination={{ pageSize: 10 }}
                  size="small"
                  className="data-table"
                />
              </div>
            </div>
          ) : (
            <Card className="content-card">
              <div className="loading-container">
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
                <div className="loading-text">配置参数并运行回测后，结果将在此处显示</div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default Backtest