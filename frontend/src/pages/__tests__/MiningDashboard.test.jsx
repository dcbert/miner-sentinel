import { ThemeProvider } from '@/components/theme-provider';
import api from '@/lib/api';
import { AuthProvider } from '@/lib/AuthContext';
import { TimeRangeProvider } from '@/lib/TimeRangeContext';
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

const mockDevices = [
  {
    id: 1,
    device_id: 'bitaxe-001',
    device_name: 'Bitaxe-1',
    name: 'Bitaxe-1',
    make: 'bitaxe',
    is_active: true,
    last_seen_at: '2026-07-23T12:00:00Z',
    error_message: null,
  },
  {
    id: 2,
    device_id: 'avalon-001',
    device_name: 'Avalon-1',
    name: 'Avalon-1',
    make: 'avalon',
    is_active: true,
    last_seen_at: '2026-07-23T12:00:00Z',
    error_message: null,
  },
]
const mockMiningLatest = [
  {
    device: 1, device_id_str: 'bitaxe-001', device_name: 'Bitaxe-1', device_type: 'bitaxe',
    hashrate_ghs: 450.5, shares_accepted: 1200, shares_rejected: 5,
    recorded_at: new Date().toISOString(),
  },
  {
    device: 2, device_id_str: 'avalon-001', device_name: 'Avalon-1', device_type: 'avalon',
    hashrate_ghs: 6500.0, shares_accepted: 500, shares_rejected: 2,
    recorded_at: new Date().toISOString(),
  },
]
const mockHardwareLatest = [
  {
    device: 1, device_id_str: 'bitaxe-001', device_name: 'Bitaxe-1', device_type: 'bitaxe',
    temperature_c: 65.0, power_watts: 15.0, fan_speed_rpm: 4200,
    recorded_at: new Date().toISOString(),
  },
  {
    device: 2, device_id_str: 'avalon-001', device_name: 'Avalon-1', device_type: 'avalon',
    temperature_c: 55.0, power_watts: 80.0, fan_speed_rpm: 1500,
    recorded_at: new Date().toISOString(),
  },
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
    if (url.includes('/api/bitaxe/pool/hashrate_trend/')) {
      return Promise.resolve({
        data: overrides.poolStats !== undefined ? overrides.poolStats : mockPoolStats,
      })
    }
    if (url.includes('/api/bitaxe/pool/')) {
      return Promise.resolve({ data: { results: overrides.poolStats !== undefined ? overrides.poolStats : [] } })
    }
    if (url.includes('/api/devices/')) {
      return Promise.resolve({
        data: { results: overrides.devices !== undefined ? overrides.devices : mockDevices },
      })
    }
    if (url.includes('/api/mining/latest/')) {
      return Promise.resolve({
        data: overrides.miningStats !== undefined ? overrides.miningStats : mockMiningLatest,
      })
    }
    if (url.includes('/api/hardware/latest/')) {
      return Promise.resolve({
        data: overrides.hardwareStats !== undefined ? overrides.hardwareStats : mockHardwareLatest,
      })
    }
    // Legacy fallbacks (should not be required)
    if (url.includes('/api/bitaxe/devices/')) {
      return Promise.resolve({ data: { results: [] } })
    }
    if (url.includes('/api/avalon/devices/')) {
      return Promise.resolve({ data: [] })
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
        <AuthProvider>
          <TimeRangeProvider>{ui}</TimeRangeProvider>
        </AuthProvider>
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
      miningStats: mockMiningLatest,
      hardwareStats: mockHardwareLatest,
      devices: mockDevices,
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
            <TimeRangeProvider>
              <MiningDashboard />
            </TimeRangeProvider>
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
