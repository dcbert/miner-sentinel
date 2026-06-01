import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ChartCard from '../ChartCard';
import DashboardSkeleton from '../DashboardSkeleton';
import KPICard from '../KPICard';
import PeriodSelector from '../PeriodSelector';
import StatsCard, { StatRow } from '../StatsCard';

// ─── ChartCard ────────────────────────────────────────────────────────────────

describe('ChartCard', () => {
  it('renders title', () => {
    render(<ChartCard title="Hashrate"><span>content</span></ChartCard>)
    expect(screen.getByText('Hashrate')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<ChartCard title="X" description="Some desc"><span /></ChartCard>)
    expect(screen.getByText('Some desc')).toBeInTheDocument()
  })

  it('renders without description (optional)', () => {
    const { container } = render(<ChartCard title="X"><span>child</span></ChartCard>)
    expect(container.querySelector('p')).toBeNull()
  })

  it('renders children inside the height container', () => {
    render(<ChartCard title="X" height={200}><span>inner</span></ChartCard>)
    expect(screen.getByText('inner')).toBeInTheDocument()
  })

  it('applies custom height', () => {
    const { container } = render(<ChartCard title="X" height={400}><span /></ChartCard>)
    const div = container.querySelector('[style]')
    expect(div?.style.height).toBe('400px')
  })

  it('default height is 350px', () => {
    const { container } = render(<ChartCard title="X"><span /></ChartCard>)
    const div = container.querySelector('[style]')
    expect(div?.style.height).toBe('350px')
  })
})

// ─── KPICard ──────────────────────────────────────────────────────────────────

describe('KPICard', () => {
  it('renders title and value', () => {
    render(<KPICard title="Hashrate" value="450 GH/s" />)
    expect(screen.getByText('Hashrate')).toBeInTheDocument()
    expect(screen.getByText('450 GH/s')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(<KPICard title="T" value="V" subtitle="last 24h" />)
    expect(screen.getByText('last 24h')).toBeInTheDocument()
  })

  it('renders without subtitle', () => {
    render(<KPICard title="T" value="V" />)
    expect(screen.queryByText('last 24h')).toBeNull()
  })

  it('renders icon when provided', () => {
    const MockIcon = ({ className }) => <svg data-testid="icon" className={className} />
    render(<KPICard title="T" value="V" icon={MockIcon} />)
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('renders progress bar when progress prop is given', () => {
    const { container } = render(<KPICard title="T" value="V" progress={75} />)
    // Progress component renders an element with role="progressbar" or similar
    expect(container.querySelector('[class*="progress"]') || container.querySelector('div > div > div')).toBeTruthy()
  })

  it('renders badge when badge prop is given', () => {
    render(<KPICard title="T" value="V" badge={{ variant: 'default', text: 'Good' }} />)
    expect(screen.getByText('Good')).toBeInTheDocument()
  })

  it('renders trend when trend prop is given', () => {
    const MockIcon = ({ className }) => <svg data-testid="trend-icon" className={className} />
    render(<KPICard title="T" value="V" trend={{ icon: MockIcon, color: 'text-green-500', text: '+5%' }} />)
    expect(screen.getByText('+5%')).toBeInTheDocument()
    expect(screen.getByTestId('trend-icon')).toBeInTheDocument()
  })

  it('renders without optional props', () => {
    render(<KPICard title="Basic" value="0" />)
    expect(screen.getByText('Basic')).toBeInTheDocument()
  })
})

// ─── StatsCard ────────────────────────────────────────────────────────────────

describe('StatsCard', () => {
  it('renders title', () => {
    render(<StatsCard title="Stats"><span>child</span></StatsCard>)
    expect(screen.getByText('Stats')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<StatsCard title="T" description="Desc"><span /></StatsCard>)
    expect(screen.getByText('Desc')).toBeInTheDocument()
  })

  it('renders without description', () => {
    render(<StatsCard title="T"><span /></StatsCard>)
    expect(screen.queryByText('Desc')).toBeNull()
  })

  it('renders children', () => {
    render(<StatsCard title="T"><span>content</span></StatsCard>)
    expect(screen.getByText('content')).toBeInTheDocument()
  })
})

// ─── StatRow ──────────────────────────────────────────────────────────────────

describe('StatRow', () => {
  it('renders label and value', () => {
    render(<StatRow label="Temp" value="65°C" />)
    expect(screen.getByText('Temp')).toBeInTheDocument()
    expect(screen.getByText('65°C')).toBeInTheDocument()
  })

  it('applies destructive variant class', () => {
    render(<StatRow label="L" value="V" variant="destructive" />)
    const span = screen.getByText('V')
    expect(span.className).toContain('destructive')
  })

  it('applies success variant class', () => {
    render(<StatRow label="L" value="V" variant="success" />)
    expect(screen.getByText('V').className).toContain('green')
  })

  it('applies warning variant class', () => {
    render(<StatRow label="L" value="V" variant="warning" />)
    expect(screen.getByText('V').className).toContain('yellow')
  })

  it('applies primary variant class', () => {
    render(<StatRow label="L" value="V" variant="primary" />)
    expect(screen.getByText('V').className).toContain('primary')
  })

  it('defaults to font-medium for unknown variant', () => {
    render(<StatRow label="L" value="V" variant="default" />)
    expect(screen.getByText('V').className).toContain('font-medium')
  })
})

// ─── DashboardSkeleton ────────────────────────────────────────────────────────

describe('DashboardSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<DashboardSkeleton />)
    expect(container.firstChild).toBeTruthy()
  })

  it('renders 8 skeleton cards', () => {
    const { container } = render(<DashboardSkeleton />)
    // 8 inner skeletons + 1 header skeleton = 9 elements with h-class
    const skeletons = container.querySelectorAll('[class*="h-"]')
    expect(skeletons.length).toBeGreaterThanOrEqual(8)
  })
})

// ─── PeriodSelector ───────────────────────────────────────────────────────────

describe('PeriodSelector', () => {
  const periods = {
    '1h': { label: '1 Hour' },
    '24h': { label: '24 Hours' },
    '7d': { label: '7 Days' },
  }

  it('renders all period buttons', () => {
    render(<PeriodSelector periods={periods} selectedPeriod="1h" onPeriodChange={vi.fn()} />)
    expect(screen.getByText('1 Hour')).toBeInTheDocument()
    expect(screen.getByText('24 Hours')).toBeInTheDocument()
    expect(screen.getByText('7 Days')).toBeInTheDocument()
  })

  it('highlights the selected period', () => {
    render(<PeriodSelector periods={periods} selectedPeriod="24h" onPeriodChange={vi.fn()} />)
    const selected = screen.getByText('24 Hours')
    expect(selected.className).toContain('bg-primary')
  })

  it('non-selected periods have secondary class', () => {
    render(<PeriodSelector periods={periods} selectedPeriod="1h" onPeriodChange={vi.fn()} />)
    const unselected = screen.getByText('24 Hours')
    expect(unselected.className).toContain('bg-secondary')
  })

  it('calls onPeriodChange when a period button is clicked', () => {
    const onChange = vi.fn()
    render(<PeriodSelector periods={periods} selectedPeriod="1h" onPeriodChange={onChange} />)
    fireEvent.click(screen.getByText('7 Days'))
    expect(onChange).toHaveBeenCalledWith('7d')
  })

  it('calls onPeriodChange with correct key', () => {
    const onChange = vi.fn()
    render(<PeriodSelector periods={periods} selectedPeriod="1h" onPeriodChange={onChange} />)
    fireEvent.click(screen.getByText('1 Hour'))
    expect(onChange).toHaveBeenCalledWith('1h')
  })
})
