import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import DataWorkspace from './pages/DataWorkspace'
import MaterialRisk from './pages/MaterialRisk'
import ScenarioLab from './pages/ScenarioLab'
import SupplierComparison from './pages/SupplierComparison'
import EvidenceTrace from './pages/EvidenceTrace'
import DecisionReview from './pages/DecisionReview'
import Reports from './pages/Reports'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="data" element={<DataWorkspace />} />
          <Route path="risk" element={<MaterialRisk />} />
          <Route path="scenario" element={<ScenarioLab />} />
          <Route path="suppliers" element={<SupplierComparison />} />
          <Route path="evidence" element={<EvidenceTrace />} />
          <Route path="decisions" element={<DecisionReview />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
