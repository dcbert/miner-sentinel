import { ThemeProvider } from '@/components/theme-provider';
import api from '@/lib/api';
import { AuthProvider } from '@/lib/AuthContext';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OverviewDashboard from '../OverviewDashboard';

// Mock the api module (used for analytics + auth check inside AuthProvider)
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
  // Ensure auth passes (token + mocked /api/auth/user/ response)
  localStorage.setItem('sessionToken', 'test-token-123')

  // Make api.get resolve for both auth check and the page's analytics call
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
          {ui}
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>
  )
}

describe('OverviewDashboard (smoke + integration with mocks)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders header, PeriodSelector, and loads analytics data without crashing', async () => {
    renderWithProviders(<OverviewDashboard />)

    // Header
    expect(await screen.findByText('Overview')).toBeInTheDocument()
    expect(screen.getByText(/Real-time mining operations at a glance/i)).toBeInTheDocument()

    // PeriodSelector buttons (may appear multiple times in dashboard sections; use queryAll safe)
    expect(screen.queryAllByText('24 Hours').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('7 Days').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('30 Days').length).toBeGreaterThan(0)

    // Wait for data load (replaces skeleton)
    await waitFor(() => {
      expect(screen.queryByText(/Loading|DashboardSkeleton/i)).not.toBeInTheDocument()
    })

    // Key metrics from mock data (may render in multiple KPI/sections; use queryAll for smoke test)
    expect(screen.queryAllByText(/Total Hashrate/i).length).toBeGreaterThan(0)
    // Value formatted by formatHashrate
    expect(screen.queryAllByText(/1.23 TH\/s/i).length).toBeGreaterThan(0)

    // Share / acceptance metrics (labels may vary; assert stable ones from mock + best share)
    expect(screen.queryAllByText(/Best Share/i).length).toBeGreaterThan(0)
    expect(screen.queryAllByText(/98.7|Acceptance|Performance/i).length).toBeGreaterThan(0)
  })

  it('changes period and refetches analytics with correct params', async () => {
    const user = userEvent.setup()
    renderWithProviders(<OverviewDashboard />)

    await screen.findByText('Overview')

    // Click 7 Days (use first if multiple instances)
    const sevenDayBtns = screen.queryAllByText('7 Days')
    const sevenDayBtn = sevenDayBtns[0]
    await user.click(sevenDayBtn)

    // Should trigger new api call with days=7, hours=168
    await waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url.includes('/api/overview/analytics/'))
      expect(calls.length).toBeGreaterThanOrEqual(2)
      const lastCall = calls[calls.length - 1]
      expect(lastCall[1]).toMatchObject({
        params: { hours: 168, days: 7 },
      })
    })
  })

  it('shows error state when analytics fetch fails (after initial load attempt)', async () => {
    // Override to reject for this test
    api.get.mockImplementation((url) => {
      if (url.includes('/api/auth/user/')) {
        return Promise.resolve({ data: { authenticated: true, user: null } })
      }
      if (url.includes('/api/overview/analytics/')) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.resolve({ data: {} })
    })
    localStorage.setItem('sessionToken', 'test')

    render(
      <MemoryRouter>
        <ThemeProvider defaultTheme="dark" storageKey="test-theme">
          <AuthProvider>
            <OverviewDashboard />
          </AuthProvider>
        </ThemeProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Unable to load analytics data/i)).toBeInTheDocument()
      // Icon is svg, not text "AlertTriangle"; check for error styling or alert presence
      expect(document.querySelector('.text-destructive') || screen.queryByRole('alert')).toBeTruthy()
    })
  })
})
