import { Route, Routes } from 'react-router'
import { ProtectedRoute, PublicOnlyRoute, RootRedirect } from './components/layout/RouteGuards'
import type { AuthClient } from './lib/auth/AuthContext'
import { AuthProvider } from './lib/auth/AuthProvider'
import type { AppConfig } from './lib/config'
import DashboardPage from './pages/DashboardPage'
import AnalysisTargetWorkspacePage from './pages/AnalysisTargetWorkspacePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import TargetWorkflowPage from './pages/TargetWorkflowPage'
import RegisterPage from './pages/RegisterPage'

interface AppProps {
  config: AppConfig
  authClient: AuthClient
}

export default function App({ config, authClient }: AppProps) {
  return (
    <AuthProvider client={authClient}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/targets/new" element={<TargetWorkflowPage apiBaseUrl={config.apiBaseUrl} />} />
          <Route path="/targets/:targetId" element={<TargetWorkflowPage apiBaseUrl={config.apiBaseUrl} />} />
          <Route path="/dashboard" element={<DashboardPage apiBaseUrl={config.apiBaseUrl} />} />
          <Route path="/targets/:targetId" element={<AnalysisTargetWorkspacePage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
