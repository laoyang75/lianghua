import React from 'react'
import { Card, Button, Descriptions, Space, Tag } from 'antd'
import { PlayCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store'

const StrategyManagement: React.FC = () => {
  const navigate = useNavigate()
  const { setCurrentStrategy } = useAppStore()

  // 策略模板数据
  const strategies = [
    {
      name: '下跌买入策略',
      type: 'reversal',
      description: '逆向投资策略，在股票超跌时买入，等待反弹获利',
      parameters: {
        buy_timing: 'T+1开盘',
        sell_timing: '开盘',
        hold_days: 5,
        execution_frequency: 7,
        execution_count: 5,
        positioning: '等权分配',
        initial_capital: 100000,
        filter_rules: {
          min_market_cap: 100000000,
          max_drop_pct: -60,
          top_k: 5
        }
      }
    },
    {
      name: '上涨买入策略',
      type: 'momentum',
      description: '动量投资策略，追踪强势股，顺势而为',
      parameters: {
        buy_timing: 'T+1开盘',
        sell_timing: '开盘',
        hold_days: 5,
        execution_frequency: 7,
        execution_count: 5,
        positioning: '等权分配',
        initial_capital: 100000,
        filter_rules: {
          min_market_cap: 500000000,
          top_k: 5
        }
      }
    }
  ]

  const handleUseStrategy = (strategy: any) => {
    setCurrentStrategy(strategy)
    navigate('/backtest')
  }

  const handleViewDetails = (strategy: any) => {
    console.log('查看策略详情:', strategy)
  }

  const renderStrategyCard = (strategy: any, index: number) => (
    <Card
      key={index}
      title={
        <Space>
          <span>{strategy.name}</span>
          <Tag color={strategy.type === 'reversal' ? 'blue' : 'green'}>
            {strategy.type === 'reversal' ? '逆向策略' : '动量策略'}
          </Tag>
        </Space>
      }
      className="content-card"
      actions={[
        <Button 
          type="primary" 
          icon={<PlayCircleOutlined />}
          onClick={() => handleUseStrategy(strategy)}
        >
          使用此策略
        </Button>,
        <Button 
          icon={<InfoCircleOutlined />}
          onClick={() => handleViewDetails(strategy)}
        >
          查看详情
        </Button>
      ]}
    >
      <p style={{ marginBottom: '20px', color: '#666' }}>{strategy.description}</p>
      
      <Descriptions column={2} size="small">
        <Descriptions.Item label="买入时机">
          {strategy.parameters.buy_timing}
        </Descriptions.Item>
        <Descriptions.Item label="卖出时机">
          {strategy.parameters.sell_timing}
        </Descriptions.Item>
        <Descriptions.Item label="持仓天数">
          {strategy.parameters.hold_days}天
        </Descriptions.Item>
        <Descriptions.Item label="执行频率">
          每{strategy.parameters.execution_frequency}天
        </Descriptions.Item>
        <Descriptions.Item label="执行次数">
          {strategy.parameters.execution_count}次
        </Descriptions.Item>
        <Descriptions.Item label="仓位管理">
          {strategy.parameters.positioning}
        </Descriptions.Item>
        <Descriptions.Item label="初始资金">
          ${strategy.parameters.initial_capital.toLocaleString()}
        </Descriptions.Item>
        <Descriptions.Item label="保留股票数">
          {strategy.parameters.filter_rules.top_k}只
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: '16px' }}>
        <h4>筛选条件</h4>
        <ul style={{ paddingLeft: '20px', margin: '8px 0' }}>
          <li>最小市值: ${(strategy.parameters.filter_rules.min_market_cap / 1000000).toFixed(0)}M</li>
          {strategy.parameters.filter_rules.max_drop_pct && (
            <li>最大跌幅限制: {Math.abs(strategy.parameters.filter_rules.max_drop_pct)}%</li>
          )}
          <li>保留数量: TOP{strategy.parameters.filter_rules.top_k}</li>
        </ul>
      </div>
    </Card>
  )

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2>策略管理</h2>
        <p style={{ color: '#666' }}>
          选择预设的量化策略模板，配置参数后进行回测验证。每个策略都经过精心设计，
          体现不同的投资理念和市场观点。
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '24px' }}>
        {strategies.map((strategy, index) => renderStrategyCard(strategy, index))}
      </div>

      <Card title="策略说明" className="content-card" style={{ marginTop: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div>
            <h4 style={{ color: '#1890ff' }}>下跌买入策略（逆向投资）</h4>
            <p><strong>投资逻辑：</strong>在股票超跌时买入，等待反弹获利</p>
            <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
              <li>数据源：跌幅最大TOP20标签</li>
              <li>过滤条件：市值 {'>'} 1亿美金，跌幅 {'<'} 60%</li>
              <li>执行机制：每7天选择5只股票，持仓5天</li>
              <li>适用市场：震荡市、熊市后期</li>
            </ul>
          </div>
          
          <div>
            <h4 style={{ color: '#52c41a' }}>上涨买入策略（动量投资）</h4>
            <p><strong>投资逻辑：</strong>追踪强势股，顺势而为</p>
            <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
              <li>数据源：市值涨幅TOP20标签</li>
              <li>过滤条件：市值 {'>'} 5亿美金</li>
              <li>执行机制：每7天选择5只股票，持仓5天</li>
              <li>适用市场：牛市、趋势性上涨行情</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default StrategyManagement