import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import DataManagement from '@/pages/DataManagement'
import StrategyManagement from '@/pages/StrategyManagement'
import Backtest from '@/pages/Backtest'
import DeepTest from '@/pages/DeepTest'
import Experiments from '@/pages/Experiments'
import ServiceConsole from '@/pages/ServiceConsole'

const App: React.FC = () => {
  return (
    <Router>
      <MainLayout>
        <Routes>
          <Route path="/" element={<DataManagement />} />
          <Route path="/data" element={<DataManagement />} />
          <Route path="/strategy" element={<StrategyManagement />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/deeptest" element={<DeepTest />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/console" element={<ServiceConsole />} />
        </Routes>
      </MainLayout>
    </Router>
  )
}

export default App