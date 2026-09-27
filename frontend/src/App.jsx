import Layout from '@/components/layout/Layout';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/toaster';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import { TimeRangeProvider } from '@/lib/TimeRangeContext';
import ActivityPage from '@/pages/ActivityPage';
import AnalyticsDashboard from '@/pages/AnalyticsDashboard';
import AvalonDeviceDetails from '@/pages/AvalonDeviceDetails';
import BitAxeDeviceDetailsRedirect from '@/pages/BitAxeDeviceDetailsRedirect';
import DeviceDetails from '@/pages/DeviceDetails';
import LoginPage from '@/pages/LoginPage';
import MiningDashboard from '@/pages/MiningDashboard';
import OverviewDashboard from '@/pages/OverviewDashboard';
import SettingsPage from '@/pages/SettingsPage';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';

function AppRoutes() {
  const { isAuthenticated, isLoading, login } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border/80 bg-card shadow-sm">
          <img
            src="/logo.svg"
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 rounded-md object-cover"
            draggable={false}
          />
        </div>
        <p className="text-sm text-muted-foreground">Loading MinerSentinel…</p>
      </div>
    )
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
    <TimeRangeProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<OverviewDashboard />} />
          <Route path="/mining" element={<MiningDashboard />} />
          <Route path="/activity" element={<ActivityPage />} />
          {/* Unified device detail (all makes) */}
          <Route path="/devices/:make/:deviceId" element={<DeviceDetails />} />
          {/* Legacy detail routes → unified path */}
          <Route path="/bitaxe/device/:deviceId" element={<BitAxeDeviceDetailsRedirect />} />
          <Route path="/avalon/device/:deviceId" element={<AvalonDeviceDetails />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </TimeRangeProvider>
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
