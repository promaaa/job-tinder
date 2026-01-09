import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import SwipePage from './pages/SwipePage'
import CRMPage from './pages/CRMPage'
import ProfilePage from './pages/ProfilePage'
import IngestionPage from './pages/IngestionPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/swipe" element={<SwipePage />} />
            <Route path="/ingestion" element={<IngestionPage />} />
            <Route path="/crm" element={<CRMPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App