import {
    Activity,
    ArrowLeft,
    CheckCircle2,
    Cpu,
    Gauge,
    HardDrive,
    Hash,
    Monitor,
    Network,
    RefreshCw,
    Settings,
    Thermometer,
    TrendingUp,
    Wifi,
    Wind,
    Zap
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import MakeBadge, { makeIconPlateClass } from '@/components/devices/MakeBadge'
import ErrorState from '@/components/feedback/ErrorState'
import DataFreshness from '@/components/metrics/DataFreshness'
import HealthBar from '@/components/metrics/HealthBar'
import MetricCard from '@/components/metrics/MetricCard'
import StatusIndicator from '@/components/status/StatusIndicator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'
import { deviceStatusLabel, getDeviceStatus, makeLabel } from '@/lib/devices'
import {
  formatDifficulty,
  formatHashrate,
  formatNumber,
  formatPower,
  formatRelativeTime,
  formatTemp,
} from '@/lib/formatters'
import { useTimeRange } from '@/lib/TimeRangeContext'
import { formatRangeWindow, getChartTimeAxisConfig, toTimeRangeParams } from '@/lib/timeRange'

// ============================================
// HELPER COMPONENTS
// ============================================

// Info row for detail sections
function InfoRow({ label, value, mono = false, badge = null }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      {badge ? (
        <Badge variant={badge.variant || 'secondary'}>{badge.text}</Badge>
      ) : (
        <span className={`text-sm font-medium ${mono ? 'font-mono' : ''}`}>{value}</span>
      )}
    </div>
  )
}

export default function BitAxeDeviceDetails() {
  const { deviceId, make: makeParam } = useParams()
  const make = makeParam || 'bitaxe'
  const navigate = useNavigate()
  const { range } = useTimeRange()
  const [deviceData, setDeviceData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updatedAt, setUpdatedAt] = useState(null)

  useEffect(() => {
    fetchDeviceDetails()
    // Poll for new data every 2 minutes
    const interval = setInterval(fetchDeviceDetails, 120000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceId, make, range.key, range.from?.getTime?.(), range.to?.getTime?.(), range.hours])

  const fetchDeviceDetails = async () => {
    try {
      setLoading(true)
      const params = toTimeRangeParams(range)
      const response = await api.get(`/api/devices/${make}/${deviceId}/details/`, { params })
      setDeviceData(response.data)
      setUpdatedAt(new Date())
    } catch (error) {
      console.error('Error fetching device details:', error)
      setDeviceData(null)
    } finally {
      setLoading(false)
    }
  }

  const timeAxis = getChartTimeAxisConfig(range.hours)

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return timeAxis.tooltip(dateString) || 'N/A'
  }

  const formatUptime = (seconds) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const formatHashrateGH = (value) => formatHashrate(value)

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
                  {entry.dataKey.includes('hashrate') ? formatHashrateGH(entry.value) :
                   entry.dataKey.includes('temperature') ? `${entry.value}°C` :
                   entry.dataKey.includes('power') ? `${entry.value}W` :
                   formatNumber(entry.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    }
    return null
  }

  if (loading && !deviceData) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    )
  }

  if (!deviceData) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/mining')} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Mining
        </Button>
        <ErrorState
          title="Device not found"
          description="The requested device could not be loaded. It may have been removed or the API is unavailable."
          onRetry={fetchDeviceDetails}
        />
      </div>
    )
  }

  const { device, latest_mining, latest_hardware, latest_system, hashrate_trend_24h, temperature_trend_24h } = deviceData

  const deviceStatus = getDeviceStatus(device)
  const isOnline = deviceStatus === 'online'
  const isOfflineLike = deviceStatus === 'offline' || deviceStatus === 'inactive' || deviceStatus === 'stale'

  // Prepare chart data — keep raw timestamps for adaptive X-axis ticks
  const hashrateChartData = hashrate_trend_24h?.map(stat => ({
    time: stat.recorded_at,
    hashrate: stat.hashrate_ghs || 0,
    shares_accepted: stat.shares_accepted,
  })) || []

  const temperatureChartData = temperature_trend_24h?.map(log => ({
    time: log.recorded_at,
    temperature: log.temperature_c || 0,
    power: log.power_watts || 0,
    fan_speed: log.fan_speed_rpm || 0,
  })) || []

  // Calculate derived values
  const tempStatus = latest_hardware?.temperature_c > 70 ? 'hot' : latest_hardware?.temperature_c > 60 ? 'warning' : 'good'
  const efficiencyPercent = latest_system?.expected_hashrate
    ? ((latest_mining?.hashrate_ghs / latest_system.expected_hashrate) * 100).toFixed(1)
    : null
  const acceptanceRate = latest_mining?.shares_accepted && latest_mining?.shares_rejected !== undefined
    ? ((latest_mining.shares_accepted / (latest_mining.shares_accepted + latest_mining.shares_rejected)) * 100).toFixed(2)
    : null

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Contextual identity header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/mining')}
          className="h-8 w-8 shrink-0 self-start sm:h-10 sm:w-10"
          aria-label="Back to Mining"
        >
          <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
        </Button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 sm:gap-3">
            {(() => {
              const plate = makeIconPlateClass(make)
              const Icon = plate.Icon
              return (
                <div className="rounded-lg bg-muted p-1.5 sm:p-2">
                  <Icon className="h-4 w-4 sm:h-5 sm:w-5" style={plate.iconStyle} strokeWidth={1.75} />
                </div>
              )
            })()}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-lg font-bold tracking-tight sm:text-2xl">{device.device_name}</h1>
                <MakeBadge make={make} />
              </div>
              <p className="text-xs text-muted-foreground sm:text-sm">
                <span className="font-mono">{device.device_id}</span>
                <span className="mx-1 sm:mx-2">·</span>
                <span className="font-mono">{device.ip_address}</span>
                {latest_system?.firmware_version && (
                  <>
                    <span className="mx-1 sm:mx-2">·</span>
                    <span>fw {latest_system.firmware_version}</span>
                  </>
                )}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <p className="text-[10px] text-muted-foreground/80">
                  Charts: {range.label.toLowerCase()}
                  <span className="hidden sm:inline"> · {formatRangeWindow(range)}</span>
                </p>
                <DataFreshness updatedAt={updatedAt} live />
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 self-end sm:gap-3 sm:self-auto">
          <Badge
            variant={isOnline ? 'default' : deviceStatus === 'stale' ? 'secondary' : 'destructive'}
            className="px-2 py-1 text-xs sm:px-3 sm:py-1.5 sm:text-sm"
          >
            <StatusIndicator status={deviceStatus === 'online' ? 'online' : deviceStatus === 'stale' ? 'stale' : deviceStatus === 'inactive' ? 'unknown' : 'offline'} size="sm" />
            <span className="ml-1.5 sm:ml-2">{deviceStatusLabel(deviceStatus)}</span>
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchDeviceDetails} disabled={loading} className="h-8 sm:h-9">
            <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="ml-2 hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {isOfflineLike && (
        <div
          className={
            deviceStatus === 'stale'
              ? 'rounded-lg border border-status-warning/30 bg-status-warning/10 px-3 py-2 text-sm text-status-warning-fg'
              : deviceStatus === 'inactive'
                ? 'rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground'
                : 'rounded-lg border border-status-critical/30 bg-status-critical/10 px-3 py-2 text-sm text-status-critical-fg'
          }
          role="status"
        >
          {deviceStatus === 'inactive' && 'Device inactive — collection is disabled. Showing last known stats.'}
          {deviceStatus === 'stale' && 'Data may be stale — last poll is older than expected. Showing last known stats.'}
          {deviceStatus === 'offline' && 'Device offline — showing last known stats.'}
          {device.last_seen_at && (
            <span className="text-muted-foreground">
              {' '}
              · last seen {formatRelativeTime(device.last_seen_at)}
            </span>
          )}
        </div>
      )}

      {/* ============================================ */}
      {/* HERO STATS - Key metrics at a glance */}
      {/* ============================================ */}
      {latest_mining && latest_hardware && (
        <div className={`grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 ${isOfflineLike ? 'opacity-80' : ''}`}>
          <MetricCard
            variant="inline"
            icon={Hash}
            label={isOfflineLike ? 'Hashrate (last known)' : 'Hashrate'}
            value={formatHashrate(latest_mining.hashrate_ghs)}
            subtitle={
              latest_system?.expected_hashrate
                ? `Target: ${formatHashrate(latest_system.expected_hashrate)}`
                : undefined
            }
          />
          <MetricCard
            variant="inline"
            icon={Thermometer}
            label={isOfflineLike ? 'Temperature (last known)' : 'Temperature'}
            value={formatTemp(latest_hardware.temperature_c, 1)}
            subtitle={
              latest_hardware.fan_speed_rpm != null
                ? `Fan: ${latest_hardware.fan_speed_rpm} RPM`
                : undefined
            }
            tone={tempStatus === 'hot' ? 'danger' : tempStatus === 'warning' ? 'warning' : 'success'}
          />
          <MetricCard
            variant="inline"
            icon={Zap}
            label={isOfflineLike ? 'Power (last known)' : 'Power'}
            value={formatPower(latest_hardware.power_watts, 1)}
            subtitle={
              latest_hardware.efficiency_j_per_th != null
                ? `Efficiency: ${latest_hardware.efficiency_j_per_th?.toFixed(1)} J/TH`
                : undefined
            }
          />
          <MetricCard
            variant="inline"
            icon={CheckCircle2}
            label="Best difficulty"
            value={formatDifficulty(latest_mining.best_difficulty)}
            subtitle={`${latest_mining.shares_accepted?.toLocaleString() || 0} accepted · ${formatUptime(latest_mining.uptime_seconds)}`}
            tone={isOfflineLike ? 'muted' : 'success'}
          />
        </div>
      )}

      {/* ============================================ */}
      {/* PERFORMANCE SUMMARY BAR */}
      {/* ============================================ */}
      {latest_system && latest_mining && (
        <Card className={`bg-gradient-to-r from-muted/50 to-muted/30 ${isOfflineLike ? 'opacity-80' : ''}`}>
          <CardContent className="py-3 sm:py-4">
            <div className="grid gap-4 sm:gap-6 grid-cols-3">
              <div className="text-center sm:text-left">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Performance</p>
                <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 justify-center sm:justify-start">
                  <span className="text-lg sm:text-2xl font-bold">{efficiencyPercent}%</span>
                  {!isOfflineLike && parseFloat(efficiencyPercent) >= 95 && <Badge variant="default" className="text-[10px] sm:text-xs">Optimal</Badge>}
                </div>
              </div>
              <div className="text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Acceptance Rate</p>
                <span className="text-lg sm:text-2xl font-bold text-status-online-fg">{acceptanceRate}%</span>
              </div>
              <div className="text-center sm:text-right">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Best Ever</p>
                <span className="text-lg sm:text-2xl font-bold text-primary">{formatNumber(latest_mining.best_difficulty)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================ */}
      {/* MAIN CONTENT TABS */}
      {/* ============================================ */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="w-full overflow-x-auto lg:w-auto lg:inline-grid lg:grid-cols-4">
          <TabsTrigger value="performance" className="gap-1.5 sm:gap-2">
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Performance
          </TabsTrigger>
          <TabsTrigger value="hardware" className="gap-1.5 sm:gap-2">
            <Cpu className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Hardware
          </TabsTrigger>
          <TabsTrigger value="network" className="gap-1.5 sm:gap-2">
            <Wifi className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Network
          </TabsTrigger>
          <TabsTrigger value="system" className="gap-1.5 sm:gap-2">
            <Settings className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            System
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="performance" className="space-y-6">
          {/* Charts Row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Hashrate Trend */}
            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Hashrate Trend</CardTitle>
                    <CardDescription>Mining performance · {range.label.toLowerCase()}</CardDescription>
                  </div>
                  <Badge variant="secondary" className="font-mono">
                    {latest_mining?.hashrate_ghs?.toFixed(2)} GH/s
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {hashrateChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={hashrateChartData}>
                      <defs>
                        <linearGradient id="colorHashrateBitaxe" x1="0" y1="0" x2="0" y2="1">
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
                        domain={['dataMin - 0.1', 'dataMax + 0.1']}
                        className="text-xs"
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => `${value.toFixed(1)}`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="hashrate"
                        stroke="#3b82f6"
                        fillOpacity={1}
                        fill="url(#colorHashrateBitaxe)"
                        name="Hashrate (GH/s)"
                        dot={false}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-64 text-muted-foreground">
                    isOfflineLike ? 'No samples in this range (device offline)' : 'No hashrate data available'
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Temperature Chart */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Temperature</CardTitle>
                  <Badge variant={tempStatus === 'good' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'}>
                    {latest_hardware?.temperature_c?.toFixed(0)}°C
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {temperatureChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={temperatureChartData}>
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
                      <YAxis domain={['dataMin - 2', 'dataMax + 2']} className="text-xs" axisLine={false} tickLine={false} tickFormatter={(v) => `${v}°`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="temperature" stroke="#ef4444" strokeWidth={2} name="Temperature" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">No data</div>
                )}
              </CardContent>
            </Card>

            {/* Power Chart */}
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Power Consumption</CardTitle>
                  <Badge variant="secondary">{latest_hardware?.power_watts?.toFixed(0)}W</Badge>
                </div>
              </CardHeader>
              <CardContent>
                {temperatureChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={temperatureChartData}>
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
                      <YAxis domain={['dataMin - 1', 'dataMax + 1']} className="text-xs" axisLine={false} tickLine={false} tickFormatter={(v) => `${v}W`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="power" stroke="#f59e0b" strokeWidth={2} name="Power" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">No data</div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Info Cards */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Mining Stats */}
            {latest_mining && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    Mining Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-0">
                  <InfoRow label="Pool URL" value={latest_mining.pool_url} mono />
                  <InfoRow label="Pool User" value={latest_mining.pool_user?.substring(0, 25) + '...'} mono />
                  <InfoRow label="Best Ever" value={formatDifficulty(latest_mining.best_difficulty)} />
                  <InfoRow label="Best Session" value={formatDifficulty(latest_mining.best_session_difficulty)} />
                  <InfoRow label="Blocks Found" value={latest_mining.blocks_found?.toString()} />
                  <InfoRow label="Uptime" value={formatUptime(latest_mining.uptime_seconds)} />
                  <InfoRow label="Last Updated" value={formatDate(latest_mining.recorded_at)} />
                </CardContent>
              </Card>
            )}

            {/* Hardware Metrics */}
            {latest_hardware && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Gauge className="h-4 w-4 text-muted-foreground" />
                    Hardware Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <HealthBar
                    label="Temperature"
                    value={latest_hardware.temperature_c}
                    max={80}
                    unit="°C"
                    thresholds={{ warning: 55, danger: 65 }}
                  />
                  <HealthBar
                    label="Power"
                    value={latest_hardware.power_watts}
                    max={latest_system?.max_power || 20}
                    unit="W"
                    thresholds={{ warning: latest_system?.max_power * 0.8, danger: latest_system?.max_power * 0.95 }}
                  />
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div>
                      <p className="text-xs text-muted-foreground">Voltage</p>
                      <p className="text-sm font-medium">{latest_hardware.voltage?.toFixed(3)}V</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Frequency</p>
                      <p className="text-sm font-medium">{latest_hardware.frequency_mhz} MHz</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Fan Speed</p>
                      <p className="text-sm font-medium">{latest_hardware.fan_speed_rpm} RPM</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Efficiency</p>
                      <p className="text-sm font-medium">{latest_hardware.efficiency_j_per_th?.toFixed(2)} J/TH</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Hardware Tab */}
        <TabsContent value="hardware" className="space-y-6">
          {latest_system && (
            <>
              {/* Top Row - Key Hardware Info */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-blue-500/20">
                        <Cpu className="h-5 w-5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">ASIC Model</p>
                        <p className="font-semibold">{latest_system.asic_model}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-purple-500/20">
                        <Gauge className="h-5 w-5 text-purple-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Frequency</p>
                        <p className="font-semibold">{latest_hardware?.frequency_mhz} MHz</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-orange-500/10 to-transparent border-orange-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-orange-500/20">
                        <Thermometer className="h-5 w-5 text-orange-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">VR Temp</p>
                        <p className="font-semibold">{latest_system.vr_temp}°C</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-green-500/20">
                        <Zap className="h-5 w-5 text-green-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Max Power</p>
                        <p className="font-semibold">{latest_system.max_power}W</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Detail Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-muted-foreground" />
                      ASIC Configuration
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-0">
                    <InfoRow label="Model" value={latest_system.asic_model} mono />
                    <InfoRow label="Board Version" value={latest_system.board_version} />
                    <InfoRow label="Small Core Count" value={latest_system.small_core_count?.toString()} />
                    <InfoRow label="Core Voltage" value={`${latest_system.core_voltage}mV (actual: ${latest_system.core_voltage_actual}mV)`} />
                    <InfoRow label="Frequency" value={`${latest_hardware?.frequency_mhz} MHz`} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Thermometer className="h-4 w-4 text-muted-foreground" />
                      Thermal Management
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <HealthBar
                      label="Current Temp"
                      value={latest_hardware?.temperature_c}
                      max={80}
                      unit="°C"
                      thresholds={{ warning: latest_system.temp_target - 5, danger: latest_system.temp_target }}
                    />
                    <div className="grid grid-cols-2 gap-4 pt-2">
                      <div>
                        <p className="text-xs text-muted-foreground">VR Temp</p>
                        <p className="text-sm font-medium">{latest_system.vr_temp}°C</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Target Temp</p>
                        <p className="text-sm font-medium">{latest_system.temp_target}°C</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t">
                      <span className="text-sm text-muted-foreground">Overheat Mode</span>
                      <Badge variant={latest_system.overheat_mode ? 'destructive' : 'secondary'}>
                        {latest_system.overheat_mode ? 'Active' : 'Normal'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Wind className="h-4 w-4 text-muted-foreground" />
                      Fan Control
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <HealthBar
                      label="Fan Speed"
                      value={latest_system.fan_speed_percent}
                      max={100}
                      unit="%"
                      thresholds={{ warning: 80, danger: 95 }}
                    />
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">RPM</p>
                        <p className="text-sm font-medium">{latest_hardware?.fan_speed_rpm}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Min Speed</p>
                        <p className="text-sm font-medium">{latest_system.min_fan_speed}%</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t">
                      <span className="text-sm text-muted-foreground">Auto Fan</span>
                      <Badge variant={latest_system.auto_fan_speed ? 'default' : 'secondary'}>
                        {latest_system.auto_fan_speed ? 'Enabled' : 'Manual'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Zap className="h-4 w-4 text-muted-foreground" />
                      Power Configuration
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <HealthBar
                      label="Power Usage"
                      value={latest_hardware?.power_watts}
                      max={latest_system.max_power || 20}
                      unit="W"
                      thresholds={{ warning: latest_system.max_power * 0.8, danger: latest_system.max_power * 0.95 }}
                    />
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Voltage</p>
                        <p className="text-sm font-medium">{latest_hardware?.voltage?.toFixed(3)}V</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Nominal</p>
                        <p className="text-sm font-medium">{latest_system.nominal_voltage}V</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t">
                      <span className="text-sm text-muted-foreground">Overclock</span>
                      <Badge variant={latest_system.overclock_enabled ? 'default' : 'secondary'}>
                        {latest_system.overclock_enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card className="md:col-span-2">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Monitor className="h-4 w-4 text-muted-foreground" />
                      Display Settings
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Display Type</p>
                        <p className="text-sm font-medium font-mono">{latest_system.display_type}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Rotation</p>
                        <p className="text-sm font-medium">{latest_system.display_rotation}°</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Invert Screen</p>
                        <Badge variant={latest_system.invert_screen ? 'default' : 'secondary'} className="mt-1">
                          {latest_system.invert_screen ? 'Yes' : 'No'}
                        </Badge>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Timeout</p>
                        <p className="text-sm font-medium">{latest_system.display_timeout === -1 ? 'Never' : `${latest_system.display_timeout}s`}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* Network Tab */}
        <TabsContent value="network" className="space-y-6">
          {latest_system && (
            <>
              {/* Quick Network Stats */}
              <div className="grid gap-4 md:grid-cols-3">
                <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-green-500/20">
                        <Wifi className="h-5 w-5 text-green-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">WiFi Status</p>
                        <p className="font-semibold">{latest_system.wifi_status}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-blue-500/20">
                        <TrendingUp className="h-5 w-5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Signal Strength</p>
                        <p className="font-semibold">{latest_system.wifi_rssi} dBm</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className={`bg-gradient-to-br ${latest_system.is_using_fallback ? 'from-red-500/10 border-red-500/20' : 'from-emerald-500/10 border-emerald-500/20'} to-transparent`}>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${latest_system.is_using_fallback ? 'bg-red-500/20' : 'bg-emerald-500/20'}`}>
                        <Network className={`h-5 w-5 ${latest_system.is_using_fallback ? 'text-status-critical-fg' : 'text-status-online-fg'}`} />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Pool Status</p>
                        <p className="font-semibold">{latest_system.is_using_fallback ? 'Fallback' : 'Primary'}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Detail Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Wifi className="h-4 w-4 text-muted-foreground" />
                      WiFi Connection
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-0">
                    <InfoRow label="SSID" value={latest_system.ssid} mono />
                    <InfoRow label="Hostname" value={latest_system.hostname} mono />
                    <InfoRow label="IP Address" value={device.ip_address} mono />
                    <InfoRow label="MAC Address" value={latest_system.mac_address} mono />
                    <InfoRow label="Signal" value={`${latest_system.wifi_rssi} dBm`} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Network className="h-4 w-4 text-muted-foreground" />
                      Stratum Configuration
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Primary Pool</p>
                      <p className="text-sm font-mono">{latest_system.stratum_url}:{latest_system.stratum_port}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Pool User</p>
                      <p className="text-sm font-mono break-all">{latest_system.stratum_user}</p>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-muted-foreground">Pool Difficulty</span>
                      <span className="text-sm font-medium">{formatNumber(latest_system.pool_difficulty)}</span>
                    </div>
                    <div className="pt-2 border-t">
                      <p className="text-xs text-muted-foreground mb-1">Fallback Pool</p>
                      <p className="text-sm font-mono">{latest_system.fallback_stratum_url}:{latest_system.fallback_stratum_port}</p>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Using Fallback</span>
                      <Badge variant={latest_system.is_using_fallback ? 'destructive' : 'secondary'}>
                        {latest_system.is_using_fallback ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* System Tab */}
        <TabsContent value="system" className="space-y-6">
          {latest_system && (
            <>
              {/* Performance Summary */}
              <Card className="bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border-primary/20">
                <CardContent className="py-6">
                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Current Hashrate</p>
                      <p className="text-2xl font-bold">{latest_mining?.hashrate_ghs?.toFixed(2)} <span className="text-sm font-normal text-muted-foreground">GH/s</span></p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Expected</p>
                      <p className="text-2xl font-bold">{latest_system.expected_hashrate?.toFixed(2)} <span className="text-sm font-normal text-muted-foreground">GH/s</span></p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Efficiency</p>
                      <p className="text-2xl font-bold">
                        {latest_system.expected_hashrate > 0
                          ? ((latest_mining?.hashrate_ghs / latest_system.expected_hashrate) * 100).toFixed(1)
                          : '0'}
                        <span className="text-sm font-normal text-muted-foreground">%</span>
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Detail Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Settings className="h-4 w-4 text-muted-foreground" />
                      Software Versions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-0">
                    <InfoRow label="Firmware" value={latest_system.version} mono />
                    <InfoRow label="AxeOS Version" value={latest_system.axe_os_version} mono />
                    <InfoRow label="IDF Version" value={latest_system.idf_version} mono />
                    <InfoRow label="Running Partition" value={latest_system.running_partition} mono />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <HardDrive className="h-4 w-4 text-muted-foreground" />
                      Memory & Storage
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-muted-foreground">Free Heap Memory</span>
                        <span className="text-sm font-medium">{(latest_system.free_heap / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                      <Progress
                        value={Math.min(100, (latest_system.free_heap / (4 * 1024 * 1024)) * 100)}
                        className="h-2"
                      />
                    </div>
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-sm text-muted-foreground">PSRAM Available</span>
                      <Badge variant={latest_system.is_psram_available ? 'default' : 'secondary'}>
                        {latest_system.is_psram_available ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
