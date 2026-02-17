import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BudgetDashboard } from './pages/BudgetDashboard'
import { ContractsDashboard } from './pages/ContractsDashboard'
import { InvoicesDashboard } from './pages/InvoicesDashboard'
import { AlertsDashboard } from './pages/AlertsDashboard'
import { SimulationsDashboard } from './pages/SimulationsDashboard'
import { ChatDashboard } from './pages/ChatDashboard'
import { IntelligenceDashboard } from './pages/IntelligenceDashboard'
import { RecommendationsDashboard } from './pages/RecommendationsDashboard'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<BudgetDashboard />} />
          <Route path="/contracts" element={<ContractsDashboard />} />
          <Route path="/invoices" element={<InvoicesDashboard />} />
          <Route path="/alerts" element={<AlertsDashboard />} />
          <Route path="/simulations" element={<SimulationsDashboard />} />
          <Route path="/intelligence" element={<IntelligenceDashboard />} />
          <Route path="/recommendations" element={<RecommendationsDashboard />} />
          <Route path="/chat" element={<ChatDashboard />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
