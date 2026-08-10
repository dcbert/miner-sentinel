import { ThemeProvider } from '@/components/theme-provider'
import api from '@/lib/api'
import { AuthProvider } from '@/lib/AuthContext'
import { TimeRangeProvider } from '@/lib/TimeRangeContext'
import { TIME_RANGE_STORAGE_KEY } from '@/lib/timeRange'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OverviewDashboard from '../OverviewDashboard'

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

const mockAnalytics = {
  overview: {
    active_devices: 2,
    bitaxe_devices: 1,
    avalon_devices: 1,
    total_devices: 2,
  },
  mining: {
    current: {
      total_hashrate_ghs: 1234.56,
      acceptance_rate: 98.7,
      total_shares_accepted: 45678,
    },
    period: {
      hashrate_stability: 99.2,
      best_share_difficulty: 123456789,
      last_best_share_time: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    },
    efficiency: {},
  },
  hardware: {
    current: {
      total_power_watts: 850,
      avg_temperature_c: 58,
    },
    period: {},
    health: {
      power_efficiency_gh_per_watt: 1.45,
    },
  },
  pool: {
    current: {
      best_share: 987654321,
      best_share_time: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    },
    performance: {},
  },
  trends: {
    hourly_hashrate: [],
    hourly_hardware: [],
  },
}

function renderWithProviders(ui) {
  localStorage.setItem('sessionToken', 'test-token-123')

  const getMock = api.get
  getMock.mockImplementation((url) => {
    if (url.includes('/api/auth/user/')) {
      return Promise.resolve({ data: { authenticated: true, user: { id: 1, username: 'test' } } })
    }
    if (url.includes('/api/overview/analytics/')) {
      return Promise.resolve({ data: mockAnalytics })
    }
    return Promise.resolve({ data: {} })
  })

  return render(
    <MemoryRouter initialEntries={['/']}>
      <ThemeProvider defaultTheme="dark" storageKey="test-theme">
        <AuthProvider>
          <TimeRangeProvider>
            {ui}
          </TimeRangeProvider>
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('OverviewDashboard (smoke + global time range)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders header and loads analytics without local PeriodSelector', async () => {
    renderWithProviders(<OverviewDashboard />)

    expect(await screen.findByText('Overview')).toBeInTheDocument()
    expect(screen.getByText(/Live metrics now/i)).toBeInTheDocument()
    // Default global range is last 30 days
    expect(screen.queryAllByText(/last 30 days/i).length).toBeGreaterThan(0)

    await waitFor(() => {
      expect(screen.queryAllByText(/Total Hashrate/i).length).toBeGreaterThan(0)
    })

    expect(screen.queryAllByText(/1.23 TH\/s/i).length).toBeGreaterThan(0)
    expect(screen.queryAllByText(/Best Share/i).length).toBeGreaterThan(0)
  })

  it('refetches analytics when stored time range is 7d', async () => {
    localStorage.setItem(
      TIME_RANGE_STORAGE_KEY,
      JSON.stringify({ mode: 'preset', key: '7d' }),
    )
    renderWithProviders(<OverviewDashboard />)

    await screen.findByText('Overview')

    await waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url.includes('/api/overview/analytics/'))
      expect(calls.length).toBeGreaterThanOrEqual(1)
      const lastCall = calls[calls.length - 1]
      expect(lastCall[1].params).toMatchObject({ hours: 168, days: 7 })
      expect(lastCall[1].params.from).toBeTruthy()
      expect(lastCall[1].params.to).toBeTruthy()
    })

    expect(screen.queryAllByText(/last 7 days/i).length).toBeGreaterThan(0)
  })

  it('shows error state when analytics fetch fails', async () => {
    api.get.mockImplementation((url) => {
      if (url.includes('/api/auth/user/')) {
        return Promise.resolve({ data: { authenticated: true, user: null } })
      }
      if (url.includes('/api/overview/analytics/')) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.resolve({ data: {} })
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <ThemeProvider defaultTheme="dark" storageKey="test-theme">
          <AuthProvider>
            <TimeRangeProvider>
              <OverviewDashboard />
            </TimeRangeProvider>
          </AuthProvider>
        </ThemeProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText(/Unable to load analytics data/i)).toBeInTheDocument()
  })
})
