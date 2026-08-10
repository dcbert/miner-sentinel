import {
  Activity,
  ChevronRight,
  CircleDot,
  Cpu,
  Hash,
  Layers,
  Monitor,
  RefreshCw,
  Server,
  TrendingUp,
  Trophy,
  Users,
  Zap
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { deviceDetailPath, isDeviceOnline, makeLabel, unwrapList } from '@/lib/devices';
import { useTimeRange } from '@/lib/TimeRangeContext';
import { getChartTimeAxisConfig, formatRangeWindow, toTimeRangeParams } from '@/lib/timeRange';

// ============================================
// HELPER COMPONENTS
// ============================================

// Status indicator with animated pulse
function StatusIndicator({ status = 'online', size = 'sm' }) {
  const colors = {
    online: 'bg-green-500',
    warning: 'bg-yellow-500',
    offline: 'bg-red-500',
  }
  const sizes = {
    sm: 'h-2 w-2',
    md: 'h-2.5 w-2.5',
    lg: 'h-3 w-3',
  }
  return (
    <span className="relative flex">
      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${colors[status]} ${sizes[size]}`}></span>
      <span className={`relative inline-flex rounded-full ${colors[status]} ${sizes[size]}`}></span>
    </span>
  )
}

// Metric card with trend indicator
function MetricCard({ title, value, subtitle, icon: Icon, trend, trendValue, iconColor = 'text-primary' }) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2">
        <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`p-1.5 sm:p-2 rounded-lg bg-muted/50 ${iconColor}`}>
          <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-lg sm:text-2xl font-bold">{value}</div>
        <div className="flex flex-wrap items-center justify-between gap-1 mt-0.5 sm:mt-1">
          <p className="text-[10px] sm:text-xs text-muted-foreground truncate max-w-[80%]">{subtitle}</p>
          {trend && (
            <span className={`text-[10px] sm:text-xs font-medium flex items-center ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>
              <TrendingUp className={`h-2.5 w-2.5 sm:h-3 sm:w-3 mr-0.5 ${trend === 'down' ? 'rotate-180' : ''}`} />
              {trendValue}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// Device card with quick stats
function DeviceCard({ device, miningStats, hardwareStats, deviceType, onClick }) {
  const isOnline = isDeviceOnline(device)
  const temp = hardwareStats?.temperature_c
  const tempStatus = temp > 70 ? 'danger' : temp > 60 ? 'warning' : 'normal'
  const tempColor = tempStatus === 'danger' ? 'text-red-500' : tempStatus === 'warning' ? 'text-yellow-500' : 'text-green-500'

  return (
    <Card
      className="group cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all duration-200"
      onClick={onClick}
    >
      <CardHeader className="pb-2 sm:pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className={`p-1.5 sm:p-2 rounded-lg ${deviceType === 'avalon' ? 'bg-purple-500/10' : 'bg-blue-500/10'}`}>
              {deviceType === 'avalon' ? (
                <Server className={`h-4 w-4 sm:h-5 sm:w-5 ${deviceType === 'avalon' ? 'text-purple-500' : 'text-blue-500'}`} />
              ) : (
                <Cpu className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500" />
              )}
            </div>
            <div className="min-w-0">
              <CardTitle className="text-sm sm:text-base font-semibold truncate">{miningStats?.device_name || device?.device_name}</CardTitle>
              <div className="flex items-center gap-1.5 sm:gap-2 mt-0.5">
                <StatusIndicator status={isOnline ? 'online' : 'offline'} />
                <span className="text-[10px] sm:text-xs text-muted-foreground">{isOnline ? 'Online' : 'Offline'}</span>
              </div>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-2 gap-2 sm:gap-4">
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Hashrate</p>
            <p className="text-sm sm:text-lg font-bold">
              {miningStats?.hashrate_ghs ? (
                miningStats.hashrate_ghs >= 1000
                  ? `${(miningStats.hashrate_ghs / 1000).toFixed(2)} TH/s`
                  : `${miningStats.hashrate_ghs.toFixed(2)} GH/s`
              ) : 'N/A'}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Temperature</p>
            <p className={`text-sm sm:text-lg font-bold ${tempColor}`}>
              {temp ? `${temp.toFixed(0)}°C` : 'N/A'}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Power</p>
            <p className="text-xs sm:text-sm font-medium">
              {hardwareStats?.power_watts ? `${hardwareStats.power_watts.toFixed(0)}W` : 'N/A'}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Shares</p>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-[10px] sm:text-xs text-green-600 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800 px-1.5 sm:px-2">
                {miningStats?.shares_accepted?.toLocaleString() || 0}
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Section header component
function SectionHeader({ icon: Icon, title, description, action }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

export default function MiningDashboard() {
  const navigate = useNavigate()
  const { range } = useTimeRange()

  // Pool stats
  const [poolStats, setPoolStats] = useState([])
  const [latestStats, setLatestStats] = useState(null)
  const [statistics, setStatistics] = useState(null)

  // Unified fleet
  const [devices, setDevices] = useState([])
  const [deviceMiningStats, setDeviceMiningStats] = useState([])
  const [deviceHardwareStats, setDeviceHardwareStats] = useState([])

  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 120000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.key, range.from?.getTime?.(), range.to?.getTime?.(), range.hours, range.days])

  const fetchData = async () => {
    try {
      setLoading(true)
      const rangeParams = toTimeRangeParams(range)

      const [poolRes, latestRes, statsRes, devicesRes, miningRes, hardwareRes] = await Promise.all([
        // Prefer trend endpoint scoped to range; fall back to paginated list
        api.get('/api/pool/hashrate_trend/', { params: rangeParams }).catch(() =>
          api.get('/api/pool/', { params: { ...rangeParams, limit: 20000 } }).catch(() => ({ data: [] })),
        ),
        api.get('/api/pool/latest/').catch(() => ({ data: null })),
        api.get('/api/pool/statistics/', { params: rangeParams }).catch(() => ({ data: null })),
        api.get('/api/devices/').catch(() => ({ data: { results: [] } })),
        api.get('/api/mining/latest/').catch(() => ({ data: [] })),
        api.get('/api/hardware/latest/').catch(() => ({ data: [] })),
      ])

      const poolData = Array.isArray(poolRes.data)
        ? poolRes.data
        : unwrapList(poolRes.data)
      setPoolStats(poolData)
      setLatestStats(latestRes.data?.detail ? null : latestRes.data)
      setStatistics(statsRes.data)
      setDevices(unwrapList(devicesRes.data))
      setDeviceMiningStats(Array.isArray(miningRes.data) ? miningRes.data : [])
      setDeviceHardwareStats(Array.isArray(hardwareRes.data) ? hardwareRes.data : [])
    } catch (error) {
      console.error('Error fetching mining data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Group devices by make for fleet summary (Bitaxe, Avalon, NMAxe, NerdNOS, …)
  const devicesByMake = devices.reduce((acc, d) => {
    const m = d.make || 'other'
    if (!acc[m]) acc[m] = []
    acc[m].push(d)
    return acc
  }, {})

  const getAllDevices = () =>
    devices.map((device) => ({ ...device, deviceType: device.make }))

  const getAllMiningStats = () =>
    deviceMiningStats.map((stat) => ({
      ...stat,
      deviceType: stat.device_type || 'bitaxe',
    }))

  const getAllHardwareStats = () =>
    deviceHardwareStats.map((stat) => ({
      ...stat,
      deviceType: stat.device_type || 'bitaxe',
    }))

  const formatHashrate = (hashrateValue) => {
    if (!hashrateValue && hashrateValue !== 0) return 'N/A'
    // Pool display strings like "466G" or numeric GH/s
    if (typeof hashrateValue === 'string' && /[A-Za-z]/.test(hashrateValue)) {
      return hashrateValue
    }
    const ghs = parseFloat(hashrateValue)
    if (Number.isNaN(ghs)) return 'N/A'
    if (ghs >= 1000) return `${(ghs / 1000).toFixed(2)} TH/s`
    return `${ghs.toFixed(2)} GH/s`
  }

  const formatDeviceHashrate = (hashrateValue, deviceType = null) => {
    if (!hashrateValue) return 'N/A'

    const value = parseFloat(hashrateValue)

    // Both Bitaxe and Avalon report in GH/s for device tables
    if (value >= 1000) {
      // Convert to TH/s if >= 1000 GH/s
      return `${(value / 1000).toFixed(2)} TH/s`
    } else {
      // Show in GH/s
      return `${value.toFixed(2)} GH/s`
    }
  }

  const formatNumber = (num) => {
    if (!num || num === 0) return '0'

    if (num >= 1e15) return `${(num / 1e15).toFixed(2)}P` // Peta
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T` // Tera
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)}G` // Giga
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M` // Mega
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K` // Kilo

    return num.toLocaleString()
  }

  const formatHashrateGH = (ghsValue) => {
    if (!ghsValue) return 'N/A'

    const ghs = parseFloat(ghsValue)
    if (ghs >= 1000) {
      return `${(ghs / 1000).toFixed(2)} TH/s`
    }
    return `${ghs.toFixed(2)} GH/s`
  }

  const formatDifficulty = (difficulty) => {
    if (!difficulty) return 'N/A'

    if (difficulty >= 1e12) return `${(difficulty / 1e12).toFixed(2)}T`
    if (difficulty >= 1e9) return `${(difficulty / 1e9).toFixed(2)}G`
    if (difficulty >= 1e6) return `${(difficulty / 1e6).toFixed(2)}M`
    if (difficulty >= 1e3) return `${(difficulty / 1e3).toFixed(1)}K`

    return Math.round(difficulty).toLocaleString()
  }

  const formatShares = (shares) => {
    if (!shares) return '0'
    return formatNumber(shares)
  }

  // Custom formatters for charts
  const formatYAxisHashrate = (value) => {
    return formatHashrateGH(value)
  }

  const formatYAxisShares = (value) => {
    return formatNumber(value)
  }

  // Adaptive X-axis labels based on selected global time range
  const timeAxis = getChartTimeAxisConfig(range.hours)

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
          <div className="text-xs text-muted-foreground mb-2">
            {timeAxis.tooltip(label)}
          </div>
          <div className="space-y-1">
            {payload.map((entry, index) => (
              <div key={index} className="flex justify-between items-center gap-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: entry.color }}
                  ></div>
                  <span className="text-[0.70rem] uppercase text-muted-foreground">
                    {entry.name}
                  </span>
                </div>
                <span className="font-bold" style={{ color: entry.color }}>
                  {entry.dataKey.includes('hashrate') ? formatHashrateGH(entry.value) : formatNumber(entry.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    }
    return null
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp * 1000).toLocaleString()
  }

  const formatProbability = (probability) => {
    // For very small probabilities, format as "1 in X" instead of percentage
    if (probability < 0.000001) {
      const odds = Math.round(1 / probability)
      if (odds > 1e15) return `1 in ${(odds / 1e15).toFixed(2)} quadrillion`
      if (odds > 1e12) return `1 in ${(odds / 1e12).toFixed(2)} trillion`
      if (odds > 1e9) return `1 in ${(odds / 1e9).toFixed(2)} billion`
      if (odds > 1e6) return `1 in ${(odds / 1e6).toFixed(2)} million`
      return `1 in ${odds.toLocaleString()}`
    }
    // For slightly larger probabilities, show as percentage
    return `${(probability * 100).toFixed(6)}%`
  }

  const formatLargeNumber = (num) => {
    if (!num || num === 0) return '0'

    if (num >= 1e15) return `${(num / 1e15).toFixed(2)} quadrillion`
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)} trillion`
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)} billion`
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)} million`
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)} thousand`

    return Math.round(num).toLocaleString()
  }

  // Prepare chart data for hashrate trends (trend endpoint is ascending; list may be reverse)
  // Keep raw timestamps so tickFormatter can adapt to the window length.
  const sortedPool = [...poolStats].sort(
    (a, b) => new Date(a.recorded_at) - new Date(b.recorded_at),
  )
  const hashrateChartData = sortedPool.map((stat) => ({
    time: stat.recorded_at,
    hashrate_1m_ghs: stat.hashrate_1m_ghs || 0,
    hashrate_1d_ghs: stat.hashrate_1d_ghs || 0,
    shares: stat.shares,
  }))

  // Calculate totals for summary
  const totalDevices = devices.length
  const activeDevices = devices.filter((d) => isDeviceOnline(d)).length
  const allMiningStats = getAllMiningStats()
  const allHardwareStats = getAllHardwareStats()

  // Calculate combined stats
  const totalHashrateGhs = allMiningStats.reduce((sum, s) => sum + (s.hashrate_ghs || 0), 0)
  const totalPowerWatts = allHardwareStats.reduce((sum, s) => sum + (s.power_watts || 0), 0)
  const avgTemp = allHardwareStats.length > 0
    ? allHardwareStats.reduce((sum, s) => sum + (s.temperature_c || 0), 0) / allHardwareStats.length
    : 0
  const maxBestDifficulty = allMiningStats.reduce(
    (max, s) => Math.max(max, s.best_difficulty || s.difficulty || 0),
    0,
  )

  // Live workers: prefer fresh pool sample; fall back to online devices
  const poolSampleAgeMs = latestStats?.recorded_at
    ? Date.now() - new Date(latestStats.recorded_at).getTime()
    : Infinity
  const poolSampleFresh = Number.isFinite(poolSampleAgeMs) && poolSampleAgeMs < 30 * 60 * 1000
  const poolWorkers = Number(latestStats?.workers)
  const hasPoolWorkers = poolSampleFresh && Number.isFinite(poolWorkers)
  const liveWorkerCount = hasPoolWorkers ? poolWorkers : activeDevices
  const liveWorkerLabel = hasPoolWorkers
    ? `Worker${liveWorkerCount !== 1 ? 's' : ''}`
    : `Online device${liveWorkerCount !== 1 ? 's' : ''}`
  const liveWorkersOnline = liveWorkerCount > 0

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* ============================================ */}
      {/* HEADER - Clean with status badge */}
      {/* ============================================ */}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 sm:p-2.5 rounded-xl bg-primary/10">
            <Layers className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Mining</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Live device status · pool history for{' '}
              <span className="text-foreground/80 font-medium">{range.label.toLowerCase()}</span>
            </p>
            <p className="text-[10px] text-muted-foreground/80 mt-0.5 hidden sm:block">
              {formatRangeWindow(range)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Badge variant="outline" className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm" title={
            hasPoolWorkers
              ? 'Live workers reported by the mining pool'
              : 'Online mining devices (pool sample missing or stale)'
          }>
            <StatusIndicator status={liveWorkersOnline ? 'online' : 'offline'} size="sm" />
            <span className="ml-2">
              {liveWorkerCount} {liveWorkerLabel}
            </span>
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} className="h-8 sm:h-9">
            <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {/* ============================================ */}
      {/* TOP METRICS ROW - Key KPIs */}
      {/* ============================================ */}
      {loading && !latestStats ? (
        <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2"><Skeleton className="h-3 sm:h-4 w-16 sm:w-20" /></CardHeader>
              <CardContent><Skeleton className="h-6 sm:h-8 w-20 sm:w-24" /></CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          <MetricCard
            title="Pool Hashrate"
            value={
              poolSampleFresh
                ? formatHashrate(latestStats?.hashrate_1m)
                : formatHashrateGH(totalHashrateGhs)
            }
            subtitle={poolSampleFresh ? 'Pool 1 minute average' : 'Fleet live (pool stale)'}
            icon={Hash}
            iconColor="text-blue-500"
          />
          <MetricCard
            title="24h Average"
            value={formatHashrate(latestStats?.hashrate_1d)}
            subtitle={poolSampleFresh ? 'Pool daily hashrate' : 'Last pool sample'}
            icon={TrendingUp}
            iconColor="text-green-500"
          />
          <MetricCard
            title="Active Devices"
            value={`${activeDevices}/${totalDevices}`}
            subtitle={
              Object.entries(devicesByMake)
                .map(([make, list]) => `${list.length} ${makeLabel(make)}`)
                .join(', ') || 'No devices'
            }
            icon={Monitor}
            iconColor="text-purple-500"
          />
          <MetricCard
            title="Total Power"
            value={`${formatNumber(totalPowerWatts)}W`}
            subtitle={`${((totalPowerWatts / 1000) * 24).toFixed(1)} kWh/day`}
            icon={Zap}
            iconColor="text-yellow-500"
          />
          <MetricCard
            title="Best Share"
            value={maxBestDifficulty ? formatNumber(maxBestDifficulty) : '0'}
            subtitle="Device best difficulty"
            icon={Trophy}
            iconColor="text-orange-500"
          />
        </div>
      )}

      {/* ============================================ */}
      {/* DEVICES GRID - Quick overview of all devices */}
      {/* ============================================ */}
      {allMiningStats.length > 0 && (
        <div className="space-y-4">
          <SectionHeader
            icon={Server}
            title="Active Devices"
            description={`${activeDevices} device${activeDevices !== 1 ? 's' : ''} currently mining`}
          />
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {allMiningStats.map((stat) => {
              const hardware = allHardwareStats.find(
                (h) => h.device === stat.device && h.deviceType === stat.deviceType,
              ) || {}
              const device = getAllDevices().find(
                (d) => d.id === stat.device && d.deviceType === stat.deviceType,
              ) || {}
              const deviceType = stat.deviceType || device.make || 'bitaxe'
              const deviceId = device.device_id || stat.device_id_str
              return (
                <DeviceCard
                  key={`${stat.device}-${deviceType}`}
                  device={device}
                  miningStats={stat}
                  hardwareStats={hardware}
                  deviceType={deviceType}
                  onClick={() => deviceId && navigate(deviceDetailPath(deviceType, deviceId))}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* ============================================ */}
      {/* DETAILED TABS - Advanced data */}
      {/* ============================================ */}
      <Tabs defaultValue="pool" className="space-y-4">
        <TabsList className="w-full overflow-x-auto lg:w-auto lg:inline-grid lg:grid-cols-4">
          <TabsTrigger value="pool" className="gap-1.5 sm:gap-2">
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Pool
          </TabsTrigger>
          <TabsTrigger value="devices" className="gap-1.5 sm:gap-2">
            <Cpu className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Devices
          </TabsTrigger>
          <TabsTrigger value="hashrate" className="gap-1.5 sm:gap-2">
            <Hash className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Hashrate
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5 sm:gap-2">
            <Layers className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            History
          </TabsTrigger>
        </TabsList>

        {/* Pool Overview Tab */}
        <TabsContent value="pool" className="space-y-6">
          {/* Main Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Hashrate Trend</CardTitle>
                  <CardDescription>
                    1-minute vs 24-hour average · {hashrateChartData.length} point
                    {hashrateChartData.length !== 1 ? 's' : ''} in selected range
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-xs text-muted-foreground">1m</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span className="text-xs text-muted-foreground">24h</span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-80 w-full" />
              ) : hashrateChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <AreaChart data={hashrateChartData}>
                    <defs>
                      <linearGradient id="colorHashrate1m" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorHashrate1d" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                    <XAxis
                      dataKey="time"
                      tickFormatter={timeAxis.tick}
                      minTickGap={timeAxis.minTickGap}
                      interval={timeAxis.interval}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={formatYAxisHashrate}
                      domain={['dataMin', 'dataMax']}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="hashrate_1m_ghs"
                      stroke="#10b981"
                      fillOpacity={1}
                      fill="url(#colorHashrate1m)"
                      name="1m Hashrate"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="hashrate_1d_ghs"
                      stroke="#3b82f6"
                      fillOpacity={1}
                      fill="url(#colorHashrate1d)"
                      name="24h Hashrate"
                      dot={false}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-80 text-muted-foreground">
                  No hashrate data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pool Info Grid */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Pool Connection */}
            {latestStats && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <CircleDot className="h-4 w-4 text-green-500" />
                    Pool Connection
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm text-muted-foreground">Pool Address</span>
                    <span className="text-sm font-mono truncate max-w-[200px]">{latestStats.pool_address}</span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm text-muted-foreground">Last Share</span>
                    <span className="text-sm">{formatTimestamp(latestStats.lastshare)}</span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-sm text-muted-foreground">Authorized</span>
                    <span className="text-sm">{formatTimestamp(latestStats.authorised)}</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-muted-foreground">Best Ever</span>
                    <Badge variant="secondary" className="font-mono">{latestStats.bestever}</Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Period statistics for selected time range */}
            {statistics && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500" />
                    Performance · {range.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1 p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground">Total Shares</p>
                      <p className="text-xl font-bold">{formatShares(statistics.total_shares)}</p>
                    </div>
                    <div className="space-y-1 p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground">Max Hashrate</p>
                      <p className="text-xl font-bold">{formatHashrateGH(statistics.max_hashrate_ghs)}</p>
                    </div>
                    <div className="space-y-1 p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground">Best Share</p>
                      <p className="text-xl font-bold text-orange-500">{statistics.best_share ? formatNumber(statistics.best_share) : '0'}</p>
                    </div>
                    <div className="space-y-1 p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground">Data Points</p>
                      <p className="text-xl font-bold">{statistics.data_points || 0}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* All devices (multi-make) */}
        <TabsContent value="devices" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <Cpu className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Fleet Devices</CardTitle>
                    <CardDescription>
                      {devices.length} device{devices.length !== 1 ? 's' : ''} registered
                      {Object.keys(devicesByMake).length
                        ? ` · ${Object.entries(devicesByMake).map(([m, list]) => `${list.length} ${makeLabel(m)}`).join(', ')}`
                        : ''}
                    </CardDescription>
                  </div>
                </div>
                <Badge variant="outline">{devices.filter((d) => isDeviceOnline(d)).length} Online</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-64 w-full" />
              ) : devices.length > 0 ? (
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Device</TableHead>
                        <TableHead className="font-semibold">Make</TableHead>
                        <TableHead className="font-semibold">Status</TableHead>
                        <TableHead className="font-semibold">Hashrate</TableHead>
                        <TableHead className="font-semibold">Temp</TableHead>
                        <TableHead className="font-semibold">Power</TableHead>
                        <TableHead className="font-semibold">Efficiency</TableHead>
                        <TableHead className="font-semibold w-[50px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {devices.map((device) => {
                        const miningStats = deviceMiningStats.find(
                          (stat) => stat.device === device.id || stat.device_id_str === device.device_id,
                        )
                        const hardwareStats = deviceHardwareStats.find(
                          (stat) => stat.device === device.id || stat.device_id_str === device.device_id,
                        )
                        const temp = hardwareStats?.temperature_c
                        const tempColor = temp > 70 ? 'text-red-500' : temp > 60 ? 'text-yellow-500' : ''
                        return (
                          <TableRow key={`${device.make}-${device.device_id}`} className="hover:bg-muted/30">
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Cpu className="h-4 w-4 text-blue-500" />
                                <span className="font-medium">{device.device_name}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{makeLabel(device.make)}</Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <StatusIndicator status={isDeviceOnline(device) ? 'online' : 'offline'} />
                                <Badge variant={isDeviceOnline(device) ? "default" : "destructive"} className="text-xs">
                                  {isDeviceOnline(device) ? "Online" : "Offline"}
                                </Badge>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono">{formatDeviceHashrate(miningStats?.hashrate_ghs, device.make)}</TableCell>
                            <TableCell className={tempColor}>{temp ? `${temp.toFixed(1)}°C` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.power_watts ? `${hardwareStats.power_watts.toFixed(0)}W` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.efficiency_j_per_th ? `${hardwareStats.efficiency_j_per_th.toFixed(1)} J/TH` : 'N/A'}</TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => navigate(deviceDetailPath(device.make, device.device_id))}
                              >
                                <ChevronRight className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Cpu className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">No devices found</p>
                  <p className="text-sm text-muted-foreground/70 mt-1">Add Bitaxe, Avalon, NMAxe, or NerdNOS devices in Settings</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="hashrate" className="space-y-6">
          {/* Hashrate Breakdown Cards */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Hash className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Hashrate Breakdown</CardTitle>
                  <CardDescription>Pool hashrate across different time windows</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-32 w-full" />
              ) : latestStats ? (
                <div className="grid gap-3 grid-cols-2 md:grid-cols-5">
                  {[
                    { label: '1 Minute', value: latestStats.hashrate_1m, color: 'border-l-green-500' },
                    { label: '5 Minutes', value: latestStats.hashrate_5m, color: 'border-l-blue-500' },
                    { label: '1 Hour', value: latestStats.hashrate_1hr, color: 'border-l-purple-500' },
                    { label: '24 Hours', value: latestStats.hashrate_1d, color: 'border-l-yellow-500' },
                    { label: '7 Days', value: latestStats.hashrate_7d, color: 'border-l-orange-500' },
                  ].map((item, idx) => (
                    <div key={idx} className={`p-4 rounded-lg bg-muted/30 border-l-4 ${item.color}`}>
                      <p className="text-xs text-muted-foreground mb-1">{item.label}</p>
                      <p className="text-xl font-bold">{formatHashrate(item.value)}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">No data available</div>
              )}
            </CardContent>
          </Card>

          {/* Shares Over Time Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Shares Over Time</CardTitle>
                  <CardDescription>Cumulative accepted shares trend</CardDescription>
                </div>
                <Badge variant="secondary" className="font-mono">
                  {formatShares(latestStats?.shares)} total
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-64 w-full" />
              ) : hashrateChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={hashrateChartData}>
                    <defs>
                      <linearGradient id="sharesGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                    <XAxis
                      dataKey="time"
                      tickFormatter={timeAxis.tick}
                      minTickGap={timeAxis.minTickGap}
                      interval={timeAxis.interval}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={formatYAxisShares}
                      domain={['dataMin', 'dataMax']}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="shares"
                      stroke="#10b981"
                      strokeWidth={2}
                      name="Total Shares"
                      dot={false}
                      fill="url(#sharesGradient)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-64 text-muted-foreground">
                  No share data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Layers className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Pool History</CardTitle>
                    <CardDescription>
                      Pool snapshots · {range.label.toLowerCase()}
                    </CardDescription>
                  </div>
                </div>
                <Badge variant="outline">{poolStats.length} records</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  {[...Array(8)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : poolStats.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Layers className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">No pool statistics found</p>
                </div>
              ) : (
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Time</TableHead>
                        <TableHead className="font-semibold">1m Hashrate</TableHead>
                        <TableHead className="font-semibold">24h Hashrate</TableHead>
                        <TableHead className="font-semibold">Workers</TableHead>
                        <TableHead className="font-semibold">Shares</TableHead>
                        <TableHead className="font-semibold">Best Share</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...poolStats]
                        .sort((a, b) => new Date(b.recorded_at) - new Date(a.recorded_at))
                        .slice(0, 50)
                        .map((stat, index) => {
                          const best = stat.bestshare ?? stat.best_share ?? 0
                          return (
                        <TableRow key={stat.id || index} className="hover:bg-muted/30">
                          <TableCell className="font-medium text-sm">
                            {formatDate(stat.recorded_at)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono text-xs">
                              {formatHashrate(stat.hashrate_1m ?? stat.hashrate_1m_ghs)}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {formatHashrate(stat.hashrate_1d ?? stat.hashrate_1d_ghs)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <Users className="h-3.5 w-3.5 text-muted-foreground" />
                              <span>{stat.workers}</span>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{formatShares(stat.shares)}</TableCell>
                          <TableCell>
                            <Badge
                              variant={best > 1e9 ? 'default' : best > 1e6 ? 'secondary' : 'outline'}
                              className="font-mono text-xs"
                            >
                              {best ? formatNumber(best) : '0'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                          )
                        })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
