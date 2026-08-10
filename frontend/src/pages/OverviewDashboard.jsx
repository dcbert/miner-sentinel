/**
 * Overview — balanced layout:
 * KPIs → equal charts → equal Devices/Health/Pool strip → period stats
 */
import {
  DashboardSkeleton,
  HardwareHealthChart,
  MiningPerformanceChart,
  formatAxisHashrate,
  formatAxisPower,
  formatAxisShares,
  formatHashrate,
  formatNumber,
  formatShares,
  getBestShare,
} from '@/components/dashboard'
import MakeBadge from '@/components/devices/MakeBadge'
import EmptyState from '@/components/feedback/EmptyState'
import ErrorState from '@/components/feedback/ErrorState'
import DataFreshness from '@/components/metrics/DataFreshness'
import HealthBar from '@/components/metrics/HealthBar'
import MetricCard from '@/components/metrics/MetricCard'
import StatusIndicator from '@/components/status/StatusIndicator'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import api from '@/lib/api'
import { makeLabel } from '@/lib/devices'
import { useTimeRange } from '@/lib/TimeRangeContext'
import { formatRangeWindow, toAnalyticsParams } from '@/lib/timeRange'
import {
  Activity,
  Award,
  Battery,
  CheckCircle2,
  Cpu,
  Flame,
  Hash,
  Server,
  Zap,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function OverviewDashboard() {
  const { range } = useTimeRange()
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)

  const fetchAnalytics = useCallback(async () => {
    try {
      setError(null)
      const response = await api.get('/api/overview/analytics/', {
        params: toAnalyticsParams(range),
      })
      setAnalytics(response.data)
      setUpdatedAt(new Date())
    } catch (err) {
      console.error('Error fetching analytics:', err)
      setError(err)
      if (!analytics) setAnalytics(null)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keep last good data on refresh fail
  }, [range.key, range.from?.getTime?.(), range.to?.getTime?.(), range.hours, range.days])

  useEffect(() => {
    setLoading(true)
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 120000)
    return () => clearInterval(interval)
  }, [fetchAnalytics])

  if (loading && !analytics) {
    return <DashboardSkeleton />
  }

  if (error && !analytics) {
    return (
      <ErrorState
        title="Unable to load overview"
        description="Could not load analytics data. Check that the API is running and try again."
        onRetry={() => {
          setLoading(true)
          fetchAnalytics()
        }}
        className="h-96"
      />
    )
  }

  if (!analytics) {
    return (
      <ErrorState
        title="Unable to load overview"
        description="No analytics data returned."
        onRetry={() => {
          setLoading(true)
          fetchAnalytics()
        }}
        className="h-96"
      />
    )
  }

  const mining = analytics.mining || {}
  const hardware = analytics.hardware || {}
  const pool = analytics.pool || {}
  const trends = analytics.trends || {}
  const overview = analytics.overview || {}

  mining.current = mining.current || {}
  mining.period = mining.period || {}
  mining.efficiency = mining.efficiency || {}
  hardware.current = hardware.current || {}
  hardware.period = hardware.period || {}
  hardware.health = hardware.health || {}
  pool.current = pool.current || {}
  pool.performance = pool.performance || {}
  trends.hourly_hashrate = trends.hourly_hashrate || []
  trends.hourly_hardware = trends.hourly_hardware || []

  const totalHashrate = mining.current.total_hashrate_ghs || 0
  const acceptanceRate = mining.current.acceptance_rate || 0
  const totalPower = hardware.current.total_power_watts || 0
  const avgTemp = hardware.current.avg_temperature_c || 0
  const efficiency = hardware.health.power_efficiency_gh_per_watt || 0
  const stabilityScore = mining.period.hashrate_stability || 0
  const dailyEnergy = (totalPower / 1000) * 24
  const tempStatus = avgTemp > 70 ? 'danger' : avgTemp > 60 ? 'warning' : 'normal'

  const onlineDevices = overview.online_devices ?? overview.active_devices ?? 0
  const totalDevices =
    overview.total_devices ??
    overview.enabled_devices ??
    (overview.bitaxe_devices || 0) +
      (overview.avalon_devices || 0) +
      (overview.nmaxe_devices || 0) +
      (overview.nerdnos_devices || 0)
  const offlineCount =
    overview.offline_devices ?? Math.max(0, (overview.enabled_devices ?? totalDevices) - onlineDevices)
  const inactiveCount = overview.inactive_devices ?? 0

  // Prefer devices_by_make (all registered); fall back to per-make enabled counts
  let makeCounts = []
  if (overview.devices_by_make && typeof overview.devices_by_make === 'object') {
    makeCounts = Object.entries(overview.devices_by_make)
      .filter(([, val]) => Number(val) > 0)
      .map(([make, count]) => ({ make, count: Number(count) }))
      .sort((a, b) => b.count - a.count)
  } else {
    makeCounts = Object.entries(overview)
      .filter(
        ([key, val]) =>
          key.endsWith('_devices') &&
          !['active_devices', 'total_devices', 'online_devices', 'enabled_devices', 'offline_devices', 'inactive_devices'].includes(key) &&
          Number(val) > 0,
      )
      .map(([key, val]) => ({
        make: key.replace(/_devices$/, ''),
        count: Number(val),
      }))
  }

  const fleetStatus =
    totalDevices === 0
      ? 'unknown'
      : onlineDevices === 0
        ? 'offline'
        : offlineCount > 0 || inactiveCount > 0
          ? 'warning'
          : 'online'

  const acceptanceTrend =
    acceptanceRate > 99
      ? { direction: 'up', label: 'Excellent' }
      : acceptanceRate > 95
        ? { direction: 'flat', label: 'Good' }
        : { direction: 'down', label: 'Needs attention' }

  if (totalDevices === 0) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground sm:text-sm">
            Live metrics · charts for{' '}
            <span className="font-medium text-foreground/80">{range.label.toLowerCase()}</span>
          </p>
          <DataFreshness updatedAt={updatedAt} live />
        </div>
        <EmptyState
          icon={Server}
          title="No devices yet"
          description="Add a Bitaxe, Avalon, or other supported miner to start monitoring your fleet."
          action={{ label: 'Add device', to: '/settings' }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Toolbar — chrome already shows page title */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Live metrics now · charts & period stats for{' '}
            <span className="font-medium text-foreground/80">{range.label.toLowerCase()}</span>
          </p>
          <p className="mt-0.5 hidden text-[10px] text-muted-foreground/80 sm:block">
            {formatRangeWindow(range)}
          </p>
        </div>
        <DataFreshness updatedAt={updatedAt} live />
      </div>

      {/* Hero KPIs — equal weight row */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <MetricCard
          variant="hero"
          layout="icon-left"
          icon={Hash}
          label="Total Hashrate"
          value={formatHashrate(totalHashrate)}
          subtitle={`${formatNumber(totalHashrate, 2)} GH/s · fleet sum`}
          tone="default"
        />
        <MetricCard
          variant="hero"
          layout="icon-left"
          icon={CheckCircle2}
          label="Acceptance Rate"
          value={`${formatNumber(acceptanceRate, 1)}%`}
          subtitle={`${formatShares(mining.current.total_shares_accepted || 0)} accepted`}
          trend={acceptanceTrend}
          tone={acceptanceRate > 95 ? 'success' : 'warning'}
        />
        <MetricCard
          variant="hero"
          layout="icon-left"
          icon={Award}
          label="Best Share"
          value={getBestShare(mining, pool)}
          subtitle="All-time best difficulty"
          tone="default"
        />
        <MetricCard
          variant="hero"
          layout="icon-left"
          icon={Zap}
          label="Power Usage"
          value={`${formatNumber(totalPower, 0)}W`}
          subtitle={`${formatNumber(dailyEnergy, 1)} kWh/day · ${formatNumber(efficiency, 2)} GH/W`}
          tone="default"
        />
      </div>

      {/* Charts — equal 50/50 so the page isn’t left-light / right-heavy */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-6">
        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <CardTitle className="text-base font-semibold">Hashrate Performance</CardTitle>
                <CardDescription>
                  Fleet hashrate & shares · {range.label.toLowerCase()}
                </CardDescription>
              </div>
              <Badge variant="secondary" className="shrink-0 font-mono tabular-metrics">
                {formatHashrate(totalHashrate)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex-1 pt-0">
            <div className="h-[220px] sm:h-[260px]">
              <MiningPerformanceChart
                data={trends.hourly_hashrate}
                rangeHours={range.hours}
                formatAxisHashrate={formatAxisHashrate}
                formatAxisShares={formatAxisShares}
                formatHashrate={formatHashrate}
                formatShares={formatShares}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <CardTitle className="text-base font-semibold">Temperature & Power</CardTitle>
                <CardDescription>Hardware monitoring · {range.label.toLowerCase()}</CardDescription>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge
                  variant={
                    tempStatus === 'normal'
                      ? 'secondary'
                      : tempStatus === 'warning'
                        ? 'outline'
                        : 'destructive'
                  }
                  className="tabular-metrics"
                >
                  {formatNumber(avgTemp, 0)}°C
                </Badge>
                <Badge variant="secondary" className="tabular-metrics">
                  {formatNumber(totalPower, 0)}W
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 pt-0">
            <div className="h-[220px] sm:h-[260px]">
              <HardwareHealthChart
                data={trends.hourly_hardware}
                rangeHours={range.hours}
                formatAxisPower={formatAxisPower}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secondary strip — three equal cards for fleet / health / pool */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
        <Card
          className="cursor-pointer transition-shadow hover:shadow-md"
          onClick={() => navigate('/mining')}
          role="link"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              navigate('/mining')
            }
          }}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <Server className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
                Devices
              </CardTitle>
              <StatusIndicator status={fleetStatus} size="md" showLabel={false} />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tabular-metrics sm:text-4xl">{onlineDevices}</span>
              <span className="text-sm text-muted-foreground">/ {totalDevices} online</span>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
              {offlineCount > 0 && (
                <span className="font-medium text-status-warning-fg">{offlineCount} offline</span>
              )}
              {inactiveCount > 0 && (
                <span className="text-muted-foreground">{inactiveCount} inactive</span>
              )}
              {offlineCount === 0 && inactiveCount === 0 && (
                <span className="text-status-online-fg">All enabled devices online</span>
              )}
            </div>
            <div className="space-y-1.5 border-t border-border/60 pt-3">
              {makeCounts.map(({ make, count }) => (
                <div key={make} className="flex items-center justify-between text-sm">
                  <MakeBadge make={make} />
                  <span className="font-medium tabular-metrics">{count}</span>
                </div>
              ))}
              {makeCounts.length === 0 && (
                <p className="text-sm text-muted-foreground">{makeLabel('other')} fleet</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Cpu className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
              Hardware Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3.5">
            <HealthBar
              label="Temperature"
              value={avgTemp}
              max={80}
              unit="°C"
              thresholds={{ warning: 60, danger: 70 }}
              icon={Flame}
            />
            <HealthBar
              label="Power"
              value={totalPower}
              max={Math.max(totalPower * 1.2, 500)}
              unit="W"
              thresholds={{ warning: 1e9, danger: 1e9 }}
              icon={Battery}
              decimals={0}
            />
            <HealthBar
              label="Period consistency"
              value={stabilityScore}
              max={100}
              unit="%"
              thresholds={{ warning: 70, danger: 40 }}
              invert
              icon={Activity}
              decimals={0}
            />
            <p className="text-[11px] leading-snug text-muted-foreground">
              Consistency scores how steady fleet hashrate was over {range.label.toLowerCase()} (not live health).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Hash className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
              Pool
            </CardTitle>
            <CardDescription className="text-xs">Pool-reported hashrate windows</CardDescription>
          </CardHeader>
          <CardContent>
            {pool.current ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-muted/50 p-3 text-center sm:p-4">
                  <p className="mb-1 text-xs text-muted-foreground">1 Hour</p>
                  <p className="text-base font-bold tabular-metrics sm:text-lg">
                    {pool.current.hashrate_1hr || '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3 text-center sm:p-4">
                  <p className="mb-1 text-xs text-muted-foreground">24 Hours</p>
                  <p className="text-base font-bold tabular-metrics sm:text-lg">
                    {pool.current.hashrate_1d || '—'}
                  </p>
                </div>
                {(pool.current.hashrate_5m || pool.current.hashrate_7d) && (
                  <>
                    <div className="rounded-lg bg-muted/40 p-3 text-center">
                      <p className="mb-1 text-xs text-muted-foreground">5 Min</p>
                      <p className="text-sm font-semibold tabular-metrics">
                        {pool.current.hashrate_5m || '—'}
                      </p>
                    </div>
                    <div className="rounded-lg bg-muted/40 p-3 text-center">
                      <p className="mb-1 text-xs text-muted-foreground">7 Days</p>
                      <p className="text-sm font-semibold tabular-metrics">
                        {pool.current.hashrate_7d || '—'}
                      </p>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">No pool sample yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Period micro-stats — full width footer row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        <Card className="p-3 sm:p-4">
          <p className="mb-1 text-[10px] text-muted-foreground sm:text-xs">Shares/Hour</p>
          <p className="text-lg font-bold tabular-metrics sm:text-xl">
            {formatShares(mining.efficiency?.shares_per_hour || 0)}
          </p>
        </Card>
        <Card className="p-3 sm:p-4">
          <p className="mb-1 text-[10px] text-muted-foreground sm:text-xs">Peak Hashrate</p>
          <p className="text-lg font-bold tabular-metrics sm:text-xl">
            {formatHashrate(mining.period?.max_hashrate_ghs || 0)}
          </p>
        </Card>
        <Card className="p-3 sm:p-4">
          <p className="mb-1 text-[10px] text-muted-foreground sm:text-xs">Avg Temp</p>
          <p className="text-lg font-bold tabular-metrics sm:text-xl">
            {formatNumber(hardware.period?.avg_temperature_c || 0, 1)}°C
          </p>
        </Card>
        <Card className="p-3 sm:p-4">
          <p className="mb-1 text-[10px] text-muted-foreground sm:text-xs">Efficiency</p>
          <p className="text-lg font-bold tabular-metrics sm:text-xl">
            {formatNumber(efficiency, 2)} GH/W
          </p>
        </Card>
      </div>
    </div>
  )
}
