import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import api from '@/lib/api'
import {
    Activity,
    AlertTriangle,
    Award,
    Battery,
    CheckCircle2,
    Cpu,
    Flame,
    Hash,
    Server,
    TrendingDown,
    TrendingUp,
    Zap
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'

// Import dashboard components
import {
    DashboardSkeleton,
    HardwareHealthChart,
    MiningPerformanceChart,
    PeriodSelector,
    formatAxisHashrate,
    formatAxisPower,
    formatAxisShares,
    formatHashrate,
    formatNumber,
    formatShares,
    getBestShare
} from '@/components/dashboard'

// ============================================
// HELPER COMPONENTS
// ============================================

// Status indicator dot with animation
function StatusDot({ status = 'online' }) {
  const colors = {
    online: 'bg-green-500',
    warning: 'bg-yellow-500',
    offline: 'bg-red-500',
  }
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${colors[status]}`}></span>
      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${colors[status]}`}></span>
    </span>
  )
}

// Hero metric card for the main KPIs
function HeroMetric({
  icon: Icon,
  label,
  value,
  subValue,
  trend,
  trendValue,
  iconColor = 'text-primary',
  tooltip
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : null
  const trendColor = trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-muted-foreground'

  return (
    <div className="flex items-start gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl bg-card border hover:shadow-lg transition-shadow">
      <div className={`p-2 sm:p-3 rounded-lg bg-muted ${iconColor}`}>
        <Icon className="h-5 w-5 sm:h-6 sm:w-6" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs sm:text-sm text-muted-foreground font-medium">{label}</p>
        <p className="text-lg sm:text-2xl font-bold tracking-tight truncate">{value}</p>
        <div className="flex flex-wrap items-center gap-1 sm:gap-2 mt-0.5">
          {subValue && <span className="text-[10px] sm:text-xs text-muted-foreground">{subValue}</span>}
          {TrendIcon && trendValue && (
            <span className={`flex items-center text-[10px] sm:text-xs font-medium ${trendColor}`}>
              <TrendIcon className="h-3 w-3 mr-0.5" />
              {trendValue}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// Compact stat row for detailed sections
function CompactStat({ label, value, icon: Icon, variant = 'default' }) {
  const variantStyles = {
    default: 'text-foreground',
    success: 'text-green-500',
    warning: 'text-yellow-500',
    danger: 'text-red-500',
    muted: 'text-muted-foreground',
  }
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className={`text-sm font-medium ${variantStyles[variant]}`}>{value}</span>
    </div>
  )
}

// Mini sparkline chart for trends
function MiniSparkline({ data, dataKey, color = 'hsl(var(--chart-1))', height = 40 }) {
  if (!data || data.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`sparkline-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          fill={`url(#sparkline-${dataKey})`}
          strokeWidth={1.5}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// Device status card
function DeviceStatusCard({ bitaxeCount, avalonCount, totalActive }) {
  return (
    <Card className="col-span-full lg:col-span-1">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">Devices Online</CardTitle>
          <StatusDot status={totalActive > 0 ? 'online' : 'offline'} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold">{totalActive}</div>
          <div className="flex-1 space-y-1">
            {bitaxeCount > 0 && (
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">BitAxe</Badge>
                <span className="text-sm font-medium">{bitaxeCount}</span>
              </div>
            )}
            {avalonCount > 0 && (
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">Avalon</Badge>
                <span className="text-sm font-medium">{avalonCount}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Quick health indicator
function HealthIndicator({ label, value, max, unit = '', status = 'normal', icon: Icon }) {
  const percentage = Math.min((value / max) * 100, 100)
  const statusColors = {
    normal: 'bg-green-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
  }
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5">
          {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
          <span className="text-muted-foreground">{label}</span>
        </div>
        <span className="font-medium">{formatNumber(value, 1)}{unit}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${statusColors[status]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export default function OverviewDashboard() {
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState('24h')

  const periods = {
    '24h': { hours: 24, days: 1, label: '24 Hours' },
    '7d': { hours: 168, days: 7, label: '7 Days' },
    '30d': { hours: 720, days: 30, label: '30 Days' },
  }

  useEffect(() => {
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 120000)
    return () => clearInterval(interval)
  }, [selectedPeriod])

  const fetchAnalytics = async () => {
    try {
      const period = periods[selectedPeriod]
      const response = await api.get('/api/overview/analytics/', {
        params: {
          hours: period.hours,
          days: period.days,
        },
      })
      setAnalytics(response.data)
    } catch (error) {
      console.error('Error fetching analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <DashboardSkeleton />
  }

  if (!analytics) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-4">
          <AlertTriangle className="h-12 w-12 mx-auto text-destructive" />
          <p className="text-muted-foreground">Unable to load analytics data</p>
        </div>
      </div>
    )
  }

  const mining = analytics.mining || {}
  const hardware = analytics.hardware || {}
  const pool = analytics.pool || {}
  const trends = analytics.trends || {}

  // Add defaults for nested objects
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

  // Calculate derived values
  const totalHashrate = mining.current.total_hashrate_ghs || 0
  const acceptanceRate = mining.current.acceptance_rate || 0
  const totalPower = hardware.current.total_power_watts || 0
  const avgTemp = hardware.current.avg_temperature_c || 0
  const efficiency = hardware.health.power_efficiency_gh_per_watt || 0
  const stabilityScore = mining.period.hashrate_stability || 0
  const dailyEnergy = (totalPower / 1000) * 24
  const tempStatus = avgTemp > 70 ? 'danger' : avgTemp > 60 ? 'warning' : 'normal'

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* ============================================ */}
      {/* HEADER - Clean and minimal */}
      {/* ============================================ */}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Activity className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Overview</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Real-time mining operations at a glance
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <PeriodSelector
            periods={periods}
            selectedPeriod={selectedPeriod}
            onPeriodChange={setSelectedPeriod}
          />
        </div>
      </div>

      {/* ============================================ */}
      {/* HERO KPIs - 4 most important metrics */}
      {/* ============================================ */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <HeroMetric
          icon={Hash}
          label="Total Hashrate"
          value={formatHashrate(totalHashrate)}
          subValue={`${formatNumber(totalHashrate, 2)} GH/s`}
          trend={stabilityScore > 90 ? 'up' : stabilityScore > 70 ? null : 'down'}
          trendValue={`${formatNumber(stabilityScore, 0)}% stable`}
          iconColor="text-blue-500"
          tooltip="Combined hashrate from all active mining devices"
        />

        <HeroMetric
          icon={CheckCircle2}
          label="Acceptance Rate"
          value={`${formatNumber(acceptanceRate, 1)}%`}
          subValue={`${formatShares(mining.current.total_shares_accepted || 0)} accepted`}
          trend={acceptanceRate > 99 ? 'up' : acceptanceRate > 95 ? null : 'down'}
          trendValue={acceptanceRate > 99 ? 'Excellent' : acceptanceRate > 95 ? 'Good' : 'Needs attention'}
          iconColor="text-green-500"
          tooltip="Percentage of submitted shares accepted by the pool"
        />

        <HeroMetric
          icon={Award}
          label="Best Share"
          value={getBestShare(mining, pool)}
          subValue="All-time best difficulty"
          iconColor="text-orange-500"
          tooltip="Highest difficulty share ever found by your devices"
        />

        <HeroMetric
          icon={Zap}
          label="Power Usage"
          value={`${formatNumber(totalPower, 0)}W`}
          subValue={`${formatNumber(dailyEnergy, 1)} kWh/day`}
          trend={efficiency > 0.5 ? 'up' : null}
          trendValue={`${formatNumber(efficiency, 2)} GH/W`}
          iconColor="text-yellow-500"
          tooltip="Total power consumption across all devices"
        />
      </div>

      {/* ============================================ */}
      {/* MAIN CONTENT GRID - 3 column layout */}
      {/* ============================================ */}
      <div className="grid gap-4 sm:gap-6 grid-cols-1 lg:grid-cols-3">

        {/* LEFT COLUMN - Device Status & Hardware Health */}
        <div className="space-y-3 sm:space-y-4">
          {/* Device Status Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Server className="h-4 w-4 text-muted-foreground" />
                  Devices
                </CardTitle>
                <StatusDot status={analytics.overview?.active_devices > 0 ? 'online' : 'offline'} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2 mb-4">
                <span className="text-4xl font-bold">{analytics.overview?.active_devices || 0}</span>
                <span className="text-sm text-muted-foreground">online</span>
              </div>
              <div className="space-y-2">
                {(analytics.overview?.bitaxe_devices || 0) > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span>BitAxe</span>
                    </div>
                    <span className="font-medium">{analytics.overview?.bitaxe_devices}</span>
                  </div>
                )}
                {(analytics.overview?.avalon_devices || 0) > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-purple-500" />
                      <span>Avalon</span>
                    </div>
                    <span className="font-medium">{analytics.overview?.avalon_devices}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Hardware Health Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                Hardware Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <HealthIndicator
                label="Temperature"
                value={avgTemp}
                max={80}
                unit="°C"
                status={tempStatus}
                icon={Flame}
              />
              <HealthIndicator
                label="Power"
                value={totalPower}
                max={Math.max(totalPower * 1.2, 500)}
                unit="W"
                status="normal"
                icon={Battery}
              />
              <HealthIndicator
                label="Stability"
                value={stabilityScore}
                max={100}
                unit="%"
                status={stabilityScore > 85 ? 'normal' : stabilityScore > 70 ? 'warning' : 'danger'}
                icon={Activity}
              />
            </CardContent>
          </Card>

          {/* Pool Quick Stats */}
          {pool.current && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Pool Stats</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground mb-1">1 Hour</p>
                    <p className="text-sm font-bold">{pool.current.hashrate_1hr || '—'}</p>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground mb-1">24 Hours</p>
                    <p className="text-sm font-bold">{pool.current.hashrate_1d || '—'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* CENTER COLUMN - Main Charts (spans 2 columns on lg) */}
        <div className="lg:col-span-2 space-y-3 sm:space-y-4">
          {/* Hashrate Trend Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">Hashrate Performance</CardTitle>
                  <CardDescription>Mining output over {periods[selectedPeriod].label.toLowerCase()}</CardDescription>
                </div>
                <Badge variant="secondary" className="font-mono">
                  {formatHashrate(totalHashrate)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[200px]">
                <MiningPerformanceChart
                  data={trends.hourly_hashrate}
                  formatAxisHashrate={formatAxisHashrate}
                  formatAxisShares={formatAxisShares}
                  formatHashrate={formatHashrate}
                  formatShares={formatShares}
                />
              </div>
            </CardContent>
          </Card>

          {/* Temperature & Power Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">Temperature & Power</CardTitle>
                  <CardDescription>Hardware monitoring</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={tempStatus === 'normal' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'}>
                    {formatNumber(avgTemp, 0)}°C
                  </Badge>
                  <Badge variant="secondary">
                    {formatNumber(totalPower, 0)}W
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[200px]">
                <HardwareHealthChart
                  data={trends.hourly_hardware}
                  formatAxisPower={formatAxisPower}
                />
              </div>
            </CardContent>
          </Card>

          {/* Quick Stats Grid */}
          <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-4">
            <Card className="p-3 sm:p-4">
              <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Shares/Hour</p>
              <p className="text-lg sm:text-xl font-bold">{formatShares(mining.efficiency?.shares_per_hour || 0)}</p>
            </Card>
            <Card className="p-3 sm:p-4">
              <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Peak Hashrate</p>
              <p className="text-lg sm:text-xl font-bold">{formatHashrate(mining.period?.max_hashrate_ghs || 0)}</p>
            </Card>
            <Card className="p-3 sm:p-4">
              <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Avg Temp</p>
              <p className="text-lg sm:text-xl font-bold">{formatNumber(hardware.period?.avg_temperature_c || 0, 1)}°C</p>
            </Card>
            <Card className="p-3 sm:p-4">
              <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Efficiency</p>
              <p className="text-lg sm:text-xl font-bold">{formatNumber(efficiency, 2)} GH/W</p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
