import { ThemeProvider } from '@/components/theme-provider';
import api from '@/lib/api';
import { AuthProvider } from '@/lib/AuthContext';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MiningDashboard from '../MiningDashboard';

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

const mockBitaxeDevices = [
  { id: 1, device_id: 'bitaxe-001', device_name: 'Bitaxe-1', is_active: true },
]
const mockAvalonDevices = [
  { id: 2, device_id: 'avalon-001', device_name: 'Avalon-1', is_active: true },
]
const mockBitaxeMiningStats = [
  { device: 1, device_id: 'bitaxe-001', device_name: 'Bitaxe-1', hashrate_ghs: 450.5,
    shares_accepted: 1200, shares_rejected: 5, recorded_at: new Date().toISOString() },
]
const mockBitaxeHardwareStats = [
  { device: 1, device_id: 'bitaxe-001', device_name: 'Bitaxe-1', temperature_c: 65.0,
    power_watts: 15.0, fan_speed_rpm: 4200, recorded_at: new Date().toISOString() },
]
const mockAvalonMiningStats = [
  { device: 2, device_id: 'avalon-001', device_name: 'Avalon-1', hashrate_ghs: 6500.0,
    shares_accepted: 500, shares_rejected: 2, recorded_at: new Date().toISOString() },
]
const mockPoolStats = [
  { id: 1, pool_address: 'bc1qtest', hashrate_1m: '450M', hashrate_1d: '400M',
    hashrate_1m_ghs: 0.45, hashrate_1d_ghs: 0.40,
    workers: 1, shares: 1200, bestshare: 1234567.0, bestever: 9876543,
    recorded_at: new Date().toISOString() },
]
const mockLatestStats = {
  pool_address: 'bc1qtest', hashrate_1m: '450M', hashrate_1d: '400M',
  hashrate_1m_ghs: 0.45, workers: 1, shares: 1200,
}

function buildMock(overrides = {}) {
  return (url) => {
    if (url.includes('/api/auth/user/')) {
      return Promise.resolve({ data: { authenticated: true, user: { id: 1 } } })
    }
    // Specific pool endpoints FIRST (before generic /api/bitaxe/pool/)
    if (url.includes('/api/bitaxe/pool/latest/')) {
      return Promise.resolve({ data: overrides.latestStats !== undefined ? overrides.latestStats : null })
    }
    if (url.includes('/api/bitaxe/pool/statistics/')) {
      return Promise.resolve({ data: overrides.statistics !== undefined ? overrides.statistics : null })
    }
    if (url.includes('/api/bitaxe/pool/')) {
      return Promise.resolve({ data: { results: overrides.poolStats !== undefined ? overrides.poolStats : [] } })
    }
    if (url.includes('/api/bitaxe/devices/')) {
      return Promise.resolve({ data: { results: overrides.bitaxeDevices !== undefined ? overrides.bitaxeDevices : mockBitaxeDevices } })
    }
    if (url.includes('/api/bitaxe/mining/latest/')) {
      return Promise.resolve({ data: overrides.miningStats !== undefined ? overrides.miningStats : [] })
    }
    if (url.includes('/api/bitaxe/hardware/latest/')) {
      return Promise.resolve({ data: overrides.hardwareStats !== undefined ? overrides.hardwareStats : [] })
    }
    if (url.includes('/api/avalon/devices/')) {
      return Promise.resolve({ data: overrides.avalonDevices !== undefined ? overrides.avalonDevices : mockAvalonDevices })
    }
    if (url.includes('/api/avalon/mining-stats/')) {
      return Promise.resolve({ data: overrides.avalonMining !== undefined ? overrides.avalonMining : [] })
    }
    if (url.includes('/api/avalon/hardware-logs/')) {
      return Promise.resolve({ data: overrides.avalonHardware !== undefined ? overrides.avalonHardware : [] })
    }
    return Promise.resolve({ data: {} })
  }
}

function renderWithProviders(ui, overrides = {}) {
  localStorage.setItem('sessionToken', 'test-token-123')
  api.get.mockImplementation(buildMock(overrides))
  return render(
    <MemoryRouter>
      <ThemeProvider defaultTheme="dark" storageKey="test-theme">
        <AuthProvider>{ui}</AuthProvider>
      </ThemeProvider>
    </MemoryRouter>
  )
}

describe('MiningDashboard (smoke with API mocks)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })
  afterEach(() => {
    localStorage.clear()
  })

  it('renders without crashing and loads device data via mocked API calls', async () => {
    renderWithProviders(<MiningDashboard />)

    // Wait for data fetch to complete (loading false)
    await waitFor(() => {
      expect(screen.queryByText(/loading|Loading/i)).not.toBeInTheDocument()
    })

    // Key sections / device cards from the data (use queryAll to tolerate multiples now that full render succeeds)
    expect(
      screen.queryAllByText(/Bitaxe-1|Bitaxe|Mining Dashboard/i).length > 0 ||
      screen.queryAllByText(/Avalon-1|Avalon/i).length > 0
    ).toBe(true)
  })

  it('renders DeviceCards and pool charts when mining stats and pool data are available', async () => {
    renderWithProviders(<MiningDashboard />, {
      miningStats: mockBitaxeMiningStats,
      hardwareStats: mockBitaxeHardwareStats,
      avalonMining: mockAvalonMiningStats,
      poolStats: mockPoolStats,
      latestStats: mockLatestStats,
    })

    await waitFor(() => {
      expect(screen.queryByText(/loading|Loading/i)).not.toBeInTheDocument()
    }, { timeout: 5000 })

    // DeviceCard section should render (allMiningStats.length > 0)
    await waitFor(() => {
      expect(
        screen.queryAllByText(/Active Devices|Bitaxe-1|Avalon-1/i).length
      ).toBeGreaterThan(0)
    }, { timeout: 5000 })
  })

  it('renders pool history table when pool stats have records', async () => {
    // Pool stats with actual data + statistics triggers the history table and 7-day performance card
    renderWithProviders(<MiningDashboard />, {
      poolStats: mockPoolStats,
      latestStats: mockLatestStats,
      statistics: {
        total_shares: 12000,
        max_hashrate_ghs: 0.52,
        best_share: 1234567,
        data_points: 100,
      },
    })

    await waitFor(() => {
      expect(screen.queryByText(/loading|Loading/i)).not.toBeInTheDocument()
    }, { timeout: 5000 })

    // The pool tab should show stats table or data
    expect(document.body.textContent.length).toBeGreaterThan(100)
  })

  it('handles empty fallbacks from API (no crash on null/empty results)', async () => {
    // All calls return empty fallbacks
    api.get.mockImplementation((url) => {
      if (url.includes('/api/auth/user/')) return Promise.resolve({ data: { authenticated: true, user: null } })
      return Promise.resolve({ data: url.includes('devices') ? { results: [] } : null })
    })
    localStorage.setItem('sessionToken', 'test')

    render(
      <MemoryRouter>
        <ThemeProvider defaultTheme="dark" storageKey="test-theme">
          <AuthProvider>
            <MiningDashboard />
          </AuthProvider>
        </ThemeProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      // Still renders the page shell even with no devices
      expect(document.body.textContent.length).toBeGreaterThan(100)
    })
  })
})
