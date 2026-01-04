import Layout from '@/components/layout/Layout';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/toaster';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import AnalyticsDashboard from '@/pages/AnalyticsDashboard';
import AvalonDeviceDetails from '@/pages/AvalonDeviceDetails';
import BitAxeDeviceDetails from '@/pages/BitAxeDeviceDetails';
import LoginPage from '@/pages/LoginPage';
import MiningDashboard from '@/pages/MiningDashboard';
import OverviewDashboard from '@/pages/OverviewDashboard';
import SettingsPage from '@/pages/SettingsPage';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';

function AppRoutes() {
  const { isAuthenticated, isLoading, login } = useAuth()

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={login} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewDashboard />} />
        <Route path="/mining" element={<MiningDashboard />} />
        <Route path="/bitaxe/device/:deviceId" element={<BitAxeDeviceDetails />} />
        <Route path="/avalon/device/:deviceId" element={<AvalonDeviceDetails />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <Router>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </Router>
      <Toaster />
    </ThemeProvider>
  )
}

export default App
