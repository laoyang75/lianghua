import React from 'react'
import { Card, Button, Space, Alert } from 'antd'

const ServiceConsole: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Alert
        message="服务控制台"
        description="服务控制台功能正在开发中，请稍后再试。"
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />
      
      <Card title="系统信息" style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>系统状态：正常运行</div>
          <div>后端端口：5318</div>
          <div>数据库：已连接</div>
        </Space>
      </Card>
      
      <Card title="快速操作">
        <Space>
          <Button type="primary">重启服务</Button>
          <Button>清理缓存</Button>
          <Button>查看日志</Button>
        </Space>
      </Card>
    </div>
  )
}

export default ServiceConsole