import {
  Activity,
  ChevronRight,
  CircleDot,
  Cpu,
  Hash,
  Layers,
  LayoutGrid,
  List,
  Monitor,
  RefreshCw,
  Search,
  Server,
  TrendingUp,
  Trophy,
  Users,
  Zap,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import ChartFrame from '@/components/charts/ChartFrame'
import MakeBadge, { makeIconPlateClass } from '@/components/devices/MakeBadge';
import EmptyState from '@/components/feedback/EmptyState'
import SectionHeader from '@/components/layout/SectionHeader'
import DataFreshness from '@/components/metrics/DataFreshness';
import MetricCard from '@/components/metrics/MetricCard';
import StatusIndicator from '@/components/status/StatusIndicator';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import {
  deviceDetailPath,
  deviceStatusLabel,
  getDeviceStatus,
  isDeviceOnline,
  makeLabel,
  tempStatusClass,
  unwrapList,
} from '@/lib/devices';
import {
  formatDifficulty,
  formatHashrate,
  formatNumber,
  formatPower,
  formatTemp,
} from '@/lib/formatters';
import { useTimeRange } from '@/lib/TimeRangeContext';
import { getChartTimeAxisConfig, formatRangeWindow, toTimeRangeParams } from '@/lib/timeRange'
import { cn } from '@/lib/utils'

// Device card with quick stats
function DeviceCard({ device, miningStats, hardwareStats, deviceType, onClick }) {
  const status = getDeviceStatus(device)
  const temp = hardwareStats?.temperature_c
  const tempColor = tempStatusClass(temp)
  const { Icon, iconStyle } = makeIconPlateClass(deviceType)
  const statusForDot =
    status === 'online' ? 'online' : status === 'stale' ? 'stale' : status === 'inactive' ? 'unknown' : 'offline'

  return (
    <Card
      className="group cursor-pointer transition-all duration-200 hover:border-primary/50 hover:shadow-lg"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick?.()
        }
      }}
      role="link"
      tabIndex={0}
    >
      <CardHeader className="pb-2 sm:pb-3">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <div className="rounded-lg bg-muted p-1.5 sm:p-2">
              <Icon className="h-4 w-4 sm:h-5 sm:w-5" style={iconStyle} strokeWidth={1.75} />
            </div>
            <div className="min-w-0">
              <CardTitle className="truncate text-sm font-semibold sm:text-base">
                {miningStats?.device_name || device?.device_name}
              </CardTitle>
              <div className="mt-0.5 flex items-center gap-1.5 sm:gap-2">
                <StatusIndicator
                  status={statusForDot}
                  label={deviceStatusLabel(status)}
                  showLabel
                />
                <MakeBadge make={deviceType} className="hidden sm:inline-flex" />
              </div>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary sm:h-5 sm:w-5" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-2 gap-2 sm:gap-4">
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] text-muted-foreground sm:text-xs">Hashrate</p>
            <p className="text-sm font-bold tabular-metrics sm:text-lg">
              {formatHashrate(miningStats?.hashrate_ghs)}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] text-muted-foreground sm:text-xs">Temperature</p>
            <p className={`text-sm font-bold tabular-metrics sm:text-lg ${tempColor}`}>
              {formatTemp(temp, 0)}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] text-muted-foreground sm:text-xs">Power</p>
            <p className="text-xs font-medium tabular-metrics sm:text-sm">
              {formatPower(hardwareStats?.power_watts, 0)}
            </p>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-[10px] text-muted-foreground sm:text-xs">Shares</p>
            <Badge
              variant="outline"
              className="border-status-online/30 bg-status-online/10 px-1.5 text-[10px] text-status-online-fg sm:px-2 sm:text-xs"
            >
              {miningStats?.shares_accepted?.toLocaleString() || 0}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
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
  const [updatedAt, setUpdatedAt] = useState(null)
  const [mainTab, setMainTab] = useState('fleet')
  const [fleetSearch, setFleetSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all') // all | online | offline
  const [makeFilter, setMakeFilter] = useState('all')
  const [fleetView, setFleetView] = useState('cards') // cards | table
  const [poolHistoryPage, setPoolHistoryPage] = useState(0)
  const POOL_HISTORY_PAGE_SIZE = 25

  useEffect(() => {
    setPoolHistoryPage(0)
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
      setUpdatedAt(new Date())
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

  const formatHashrateGH = (ghsValue) => formatHashrate(ghsValue)
  const formatDeviceHashrate = (hashrateValue) => formatHashrate(hashrateValue)
  const formatShares = (shares) => formatNumber(shares)
  const formatYAxisHashrate = (value) => formatHashrate(value)
  const formatYAxisShares = (value) => formatNumber(value)

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

  const makeOptions = useMemo(
    () => Object.keys(devicesByMake).sort(),
    [devicesByMake],
  )

  const filteredFleet = useMemo(() => {
    const q = fleetSearch.trim().toLowerCase()
    return devices
      .map((device) => {
        const miningStats = deviceMiningStats.find(
          (stat) => stat.device === device.id || stat.device_id_str === device.device_id,
        )
        const hardwareStats = deviceHardwareStats.find(
          (stat) => stat.device === device.id || stat.device_id_str === device.device_id,
        )
        return { device, miningStats, hardwareStats, online: isDeviceOnline(device) }
      })
      .filter(({ device, online }) => {
        if (statusFilter === 'online' && !online) return false
        if (statusFilter === 'offline' && online) return false
        if (makeFilter !== 'all' && (device.make || 'other') !== makeFilter) return false
        if (!q) return true
        const hay = `${device.device_name || ''} ${device.device_id || ''} ${device.ip_address || ''}`.toLowerCase()
        return hay.includes(q)
      })
      .sort((a, b) => {
        const rank = (s) => ({ offline: 0, stale: 1, inactive: 2, unknown: 3, online: 4 }[s] ?? 3)
        const ra = rank(getDeviceStatus(a.device))
        const rb = rank(getDeviceStatus(b.device))
        if (ra !== rb) return ra - rb
        return (a.device.device_name || '').localeCompare(b.device.device_name || '')
      })
  }, [devices, deviceMiningStats, deviceHardwareStats, fleetSearch, statusFilter, makeFilter])

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Toolbar — page title lives in Layout chrome */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Live device status · pool history for{' '}
            <span className="font-medium text-foreground/80">{range.label.toLowerCase()}</span>
          </p>
          <p className="mt-0.5 hidden text-[10px] text-muted-foreground/80 sm:block">
            {formatRangeWindow(range)}
          </p>
          <DataFreshness updatedAt={updatedAt} live className="mt-1.5" />
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Badge
            variant="outline"
            className="px-2 py-1 text-xs sm:px-3 sm:py-1.5 sm:text-sm"
            title={
              hasPoolWorkers
                ? 'Live workers reported by the mining pool'
                : 'Online mining devices (pool sample missing or stale)'
            }
          >
            <StatusIndicator status={liveWorkersOnline ? 'online' : 'offline'} size="sm" />
            <span className="ml-2">
              {liveWorkerCount} {liveWorkerLabel}
            </span>
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="h-8 sm:h-9"
          >
            <RefreshCw
              className={`mr-1.5 h-3.5 w-3.5 sm:mr-2 sm:h-4 sm:w-4 ${loading ? 'animate-spin' : ''}`}
            />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {/* KPI strip */}
      {loading && !latestStats && devices.length === 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <MetricCard key={i} skeleton />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
          <MetricCard
            label="Pool Hashrate"
            value={
              poolSampleFresh
                ? formatHashrate(latestStats?.hashrate_1m)
                : formatHashrateGH(totalHashrateGhs)
            }
            subtitle={poolSampleFresh ? 'Pool reported · 1m' : 'Fleet sum (pool sample stale)'}
            icon={Hash}
          />
          <MetricCard
            label="24h Average"
            value={formatHashrate(latestStats?.hashrate_1d)}
            subtitle={poolSampleFresh ? 'Pool reported · 24h' : 'Last pool sample'}
            icon={TrendingUp}
            tone="success"
          />
          <MetricCard
            label="Active Devices"
            value={`${activeDevices}/${totalDevices}`}
            subtitle={
              Object.entries(devicesByMake)
                .map(([make, list]) => `${list.length} ${makeLabel(make)}`)
                .join(', ') || 'No devices'
            }
            icon={Monitor}
          />
          <MetricCard
            label="Total Power"
            value={formatPower(totalPowerWatts, 0)}
            subtitle={`${((totalPowerWatts / 1000) * 24).toFixed(1)} kWh/day`}
            icon={Zap}
          />
          <MetricCard
            label="Best Share"
            value={maxBestDifficulty ? formatDifficulty(maxBestDifficulty) : '0'}
            subtitle="Device best difficulty"
            icon={Trophy}
          />
        </div>
      )}


      {/* Fleet / Pool workbench */}
      <Tabs value={mainTab} onValueChange={setMainTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 sm:inline-flex sm:w-auto">
          <TabsTrigger value="fleet" className="gap-1.5">
            <Server className="hidden h-3.5 w-3.5 sm:block" strokeWidth={1.75} />
            Fleet
          </TabsTrigger>
          <TabsTrigger value="pool" className="gap-1.5">
            <Activity className="hidden h-3.5 w-3.5 sm:block" strokeWidth={1.75} />
            Pool
          </TabsTrigger>
        </TabsList>

        <TabsContent value="fleet" className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <SectionHeader
              title="Devices"
              description={`${activeDevices} online · ${filteredFleet.length} shown`}
            />
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-[12rem] flex-1 sm:max-w-xs">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" strokeWidth={1.75} />
                <Input
                  value={fleetSearch}
                  onChange={(e) => setFleetSearch(e.target.value)}
                  placeholder="Search name, id, IP…"
                  className="h-9 pl-8"
                  aria-label="Search devices"
                />
              </div>
              <div className="flex rounded-md border border-border p-0.5">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'online', label: 'Online' },
                  { key: 'offline', label: 'Offline' },
                ].map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setStatusFilter(opt.key)}
                    className={cn(
                      'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                      statusFilter === opt.key
                        ? 'bg-accent text-accent-foreground'
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {makeOptions.length > 1 && (
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    onClick={() => setMakeFilter('all')}
                    className={cn(
                      'rounded-full border px-2.5 py-0.5 text-[11px]',
                      makeFilter === 'all' ? 'border-foreground/30 bg-muted' : 'border-border text-muted-foreground',
                    )}
                  >
                    All makes
                  </button>
                  {makeOptions.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMakeFilter(m)}
                      className={cn(
                        'rounded-full border px-2.5 py-0.5 text-[11px]',
                        makeFilter === m ? 'border-foreground/30 bg-muted' : 'border-border text-muted-foreground',
                      )}
                    >
                      {makeLabel(m)}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex rounded-md border border-border p-0.5">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn('h-8 w-8', fleetView === 'cards' && 'bg-accent')}
                  onClick={() => setFleetView('cards')}
                  aria-label="Card view"
                >
                  <LayoutGrid className="h-3.5 w-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn('h-8 w-8', fleetView === 'table' && 'bg-accent')}
                  onClick={() => setFleetView('table')}
                  aria-label="Table view"
                >
                  <List className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>

          {loading && devices.length === 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-36 w-full" />
              ))}
            </div>
          ) : filteredFleet.length === 0 ? (
            <EmptyState
              icon={Server}
              title={devices.length === 0 ? 'No devices yet' : 'No devices match filters'}
              description={
                devices.length === 0
                  ? 'Add Bitaxe, Avalon, NMAxe, or NerdNOS devices in Settings.'
                  : 'Try clearing search or status filters.'
              }
              action={
                devices.length === 0
                  ? { label: 'Open Settings', to: '/settings' }
                  : { label: 'Clear filters', onClick: () => { setFleetSearch(''); setStatusFilter('all'); setMakeFilter('all') } }
              }
            />
          ) : fleetView === 'cards' ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3 xl:grid-cols-4">
              {filteredFleet.map(({ device, miningStats, hardwareStats }) => (
                <DeviceCard
                  key={`${device.make}-${device.device_id}`}
                  device={device}
                  miningStats={miningStats || { device_name: device.device_name }}
                  hardwareStats={hardwareStats || {}}
                  deviceType={device.make || 'bitaxe'}
                  onClick={() => navigate(deviceDetailPath(device.make, device.device_id))}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Device</TableHead>
                        <TableHead className="font-semibold">Make</TableHead>
                        <TableHead className="font-semibold">Status</TableHead>
                        <TableHead className="font-semibold">Hashrate</TableHead>
                        <TableHead className="font-semibold">Temp</TableHead>
                        <TableHead className="font-semibold">Power</TableHead>
                        <TableHead className="w-[50px] font-semibold" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredFleet.map(({ device, miningStats, hardwareStats }) => {
                        const temp = hardwareStats?.temperature_c
                        const tempColor = tempStatusClass(temp)
                        const st = getDeviceStatus(device)
                        const statusDot =
                          st === 'online' ? 'online' : st === 'stale' ? 'stale' : st === 'inactive' ? 'unknown' : 'offline'
                        return (
                          <TableRow
                            key={`${device.make}-${device.device_id}`}
                            className="cursor-pointer hover:bg-muted/30"
                            tabIndex={0}
                            onClick={() => navigate(deviceDetailPath(device.make, device.device_id))}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault()
                                navigate(deviceDetailPath(device.make, device.device_id))
                              }
                            }}
                          >
                            <TableCell className="font-medium">{device.device_name}</TableCell>
                            <TableCell>
                              <MakeBadge make={device.make} />
                            </TableCell>
                            <TableCell>
                              <StatusIndicator
                                status={statusDot}
                                showLabel
                                label={deviceStatusLabel(st)}
                              />
                            </TableCell>
                            <TableCell className="font-mono tabular-metrics text-sm">
                              {formatDeviceHashrate(miningStats?.hashrate_ghs)}
                            </TableCell>
                            <TableCell className={cn('tabular-metrics', tempColor)}>
                              {formatTemp(temp, 1)}
                            </TableCell>
                            <TableCell className="tabular-metrics">
                              {formatPower(hardwareStats?.power_watts, 0)}
                            </TableCell>
                            <TableCell>
                              <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="pool" className="space-y-6">
          <ChartFrame
            title="Hashrate Trend"
            description={`1-minute vs 24-hour average · ${hashrateChartData.length} point${hashrateChartData.length !== 1 ? 's' : ''} in selected range`}
            loading={loading && hashrateChartData.length === 0}
            empty={!loading && hashrateChartData.length === 0}
            heightClass="h-[280px] sm:h-[320px]"
            legend={
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[var(--chart-2)]" />
                  1m
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[var(--chart-1)]" />
                  24h
                </span>
              </div>
            }
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hashrateChartData}>
                <defs>
                  <linearGradient id="colorHashrate1m" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorHashrate1d" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
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
                  stroke="var(--chart-2)"
                  fillOpacity={1}
                  fill="url(#colorHashrate1m)"
                  name="1m Hashrate"
                  dot={false}
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="hashrate_1d_ghs"
                  stroke="var(--chart-1)"
                  fillOpacity={1}
                  fill="url(#colorHashrate1d)"
                  name="24h Hashrate"
                  dot={false}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartFrame>

          <div className="grid gap-4 md:grid-cols-2">
            {latestStats && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CircleDot className="h-4 w-4 text-status-online" />
                    Pool Connection
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between border-b py-2">
                    <span className="text-sm text-muted-foreground">Pool Address</span>
                    <span className="max-w-[200px] truncate font-mono text-sm">{latestStats.pool_address}</span>
                  </div>
                  <div className="flex items-center justify-between border-b py-2">
                    <span className="text-sm text-muted-foreground">Last Share</span>
                    <span className="text-sm">{formatTimestamp(latestStats.lastshare)}</span>
                  </div>
                  <div className="flex items-center justify-between border-b py-2">
                    <span className="text-sm text-muted-foreground">Authorized</span>
                    <span className="text-sm">{formatTimestamp(latestStats.authorised)}</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-muted-foreground">Best Ever</span>
                    <Badge variant="secondary" className="font-mono tabular-metrics">
                      {typeof latestStats.bestever === 'string' && /[A-Za-z]/.test(latestStats.bestever)
                        ? latestStats.bestever
                        : formatDifficulty(latestStats.bestever)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {statistics && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    Performance · {range.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1 rounded-lg bg-muted/50 p-3">
                      <p className="text-xs text-muted-foreground">Total Shares</p>
                      <p className="text-xl font-bold tabular-metrics">{formatShares(statistics.total_shares)}</p>
                    </div>
                    <div className="space-y-1 rounded-lg bg-muted/50 p-3">
                      <p className="text-xs text-muted-foreground">Max Hashrate</p>
                      <p className="text-xl font-bold tabular-metrics">{formatHashrateGH(statistics.max_hashrate_ghs)}</p>
                    </div>
                    <div className="space-y-1 rounded-lg bg-muted/50 p-3">
                      <p className="text-xs text-muted-foreground">Best Share</p>
                      <p className="text-xl font-bold tabular-metrics text-primary">
                        {statistics.best_share ? formatDifficulty(statistics.best_share) : '0'}
                      </p>
                    </div>
                    <div className="space-y-1 rounded-lg bg-muted/50 p-3">
                      <p className="text-xs text-muted-foreground">Data Points</p>
                      <p className="text-xl font-bold tabular-metrics">{statistics.data_points || 0}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-muted p-2">
                  <Hash className="h-5 w-5 text-primary" strokeWidth={1.75} />
                </div>
                <div>
                  <CardTitle className="text-lg">Hashrate Breakdown</CardTitle>
                  <CardDescription>Pool hashrate across different time windows</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {latestStats ? (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                  {[
                    { label: '1 Minute', value: latestStats.hashrate_1m },
                    { label: '5 Minutes', value: latestStats.hashrate_5m },
                    { label: '1 Hour', value: latestStats.hashrate_1hr },
                    { label: '24 Hours', value: latestStats.hashrate_1d },
                    { label: '7 Days', value: latestStats.hashrate_7d },
                  ].map((item) => (
                    <div key={item.label} className="rounded-lg border-l-4 border-l-primary/60 bg-muted/30 p-4">
                      <p className="mb-1 text-xs text-muted-foreground">{item.label}</p>
                      <p className="text-xl font-bold tabular-metrics">{formatHashrate(item.value)}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-muted-foreground">No data available</div>
              )}
            </CardContent>
          </Card>

          <ChartFrame
            title="Shares Over Time"
            description="Cumulative accepted shares (running total, not rate)"
            badge={
              <Badge variant="secondary" className="font-mono tabular-metrics">
                {formatShares(latestStats?.shares)} total
              </Badge>
            }
            loading={loading && hashrateChartData.length === 0}
            empty={!loading && hashrateChartData.length === 0}
            heightClass="h-[240px] sm:h-[280px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hashrateChartData}>
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
                  stroke="var(--chart-2)"
                  strokeWidth={2}
                  name="Total Shares"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Pool History</CardTitle>
                  <CardDescription>Pool snapshots · {range.label.toLowerCase()}</CardDescription>
                </div>
                <Badge variant="outline">{poolStats.length} records</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading && poolStats.length === 0 ? (
                <div className="space-y-2">
                  {[...Array(6)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : poolStats.length === 0 ? (
                <EmptyState icon={Layers} title="No pool statistics found" className="border-0 bg-transparent py-8" />
              ) : (
                <div className="overflow-hidden rounded-lg border">
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
                      {(() => {
                        const sorted = [...poolStats].sort(
                          (a, b) => new Date(b.recorded_at) - new Date(a.recorded_at),
                        )
                        const totalPages = Math.max(1, Math.ceil(sorted.length / POOL_HISTORY_PAGE_SIZE))
                        const page = Math.min(poolHistoryPage, totalPages - 1)
                        const slice = sorted.slice(
                          page * POOL_HISTORY_PAGE_SIZE,
                          page * POOL_HISTORY_PAGE_SIZE + POOL_HISTORY_PAGE_SIZE,
                        )
                        return (
                          <>
                            {slice.map((stat, index) => {
                              const best = stat.bestshare ?? stat.best_share ?? 0
                              return (
                                <TableRow key={stat.id || index} className="hover:bg-muted/30">
                                  <TableCell className="text-sm font-medium">{formatDate(stat.recorded_at)}</TableCell>
                                  <TableCell>
                                    <Badge variant="outline" className="font-mono text-xs tabular-metrics">
                                      {formatHashrate(stat.hashrate_1m ?? stat.hashrate_1m_ghs)}
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="font-mono text-sm tabular-metrics">
                                    {formatHashrate(stat.hashrate_1d ?? stat.hashrate_1d_ghs)}
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex items-center gap-1.5">
                                      <Users className="h-3.5 w-3.5 text-muted-foreground" />
                                      <span>{stat.workers}</span>
                                    </div>
                                  </TableCell>
                                  <TableCell className="font-mono text-sm tabular-metrics">
                                    {formatShares(stat.shares)}
                                  </TableCell>
                                  <TableCell>
                                    <Badge
                                      variant={best > 1e9 ? 'default' : best > 1e6 ? 'secondary' : 'outline'}
                                      className="font-mono text-xs tabular-metrics"
                                    >
                                      {best ? formatDifficulty(best) : '0'}
                                    </Badge>
                                  </TableCell>
                                </TableRow>
                              )
                            })}
                          </>
                        )
                      })()}
                    </TableBody>
                  </Table>
                </div>
              )}
              {poolStats.length > POOL_HISTORY_PAGE_SIZE && (
                <div className="mt-4 flex items-center justify-between gap-2 border-t pt-3">
                  <p className="text-xs text-muted-foreground">
                    Showing{' '}
                    {Math.min(poolStats.length, poolHistoryPage * POOL_HISTORY_PAGE_SIZE + 1)}–
                    {Math.min(poolStats.length, (poolHistoryPage + 1) * POOL_HISTORY_PAGE_SIZE)} of{' '}
                    {poolStats.length}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={poolHistoryPage <= 0}
                      onClick={() => setPoolHistoryPage((p) => Math.max(0, p - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={(poolHistoryPage + 1) * POOL_HISTORY_PAGE_SIZE >= poolStats.length}
                      onClick={() => setPoolHistoryPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

    </div>
  )
}
