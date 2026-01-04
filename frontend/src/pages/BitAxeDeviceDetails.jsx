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

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

// ============================================
// HELPER COMPONENTS
// ============================================

// Status indicator with animated pulse
function StatusIndicator({ status = 'online', size = 'md' }) {
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

// Quick stat card for the hero section
function QuickStat({ icon: Icon, label, value, subValue, status, iconColor = 'text-primary' }) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-xl bg-muted/30 border">
      <div className={`p-2 sm:p-2.5 rounded-lg bg-background ${iconColor}`}>
        <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] sm:text-xs text-muted-foreground">{label}</p>
        <p className="text-base sm:text-xl font-bold truncate">{value}</p>
        {subValue && <p className="text-[10px] sm:text-xs text-muted-foreground truncate">{subValue}</p>}
      </div>
      {status && (
        <Badge variant={status === 'good' ? 'default' : status === 'warning' ? 'secondary' : 'destructive'} className="ml-auto text-[10px] sm:text-xs">
          {status === 'good' ? 'OK' : status === 'warning' ? 'Warm' : 'Hot'}
        </Badge>
      )}
    </div>
  )
}

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

// Health indicator bar
function HealthBar({ label, value, max, unit = '', thresholds = { warning: 60, danger: 70 } }) {
  const percentage = Math.min((value / max) * 100, 100)
  const status = value > thresholds.danger ? 'danger' : value > thresholds.warning ? 'warning' : 'normal'
  const colors = {
    normal: 'bg-green-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value?.toFixed(1)}{unit}</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colors[status]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export default function BitAxeDeviceDetails() {
  const { deviceId } = useParams()
  const navigate = useNavigate()
  const [deviceData, setDeviceData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDeviceDetails()
    // Poll for new data every 2 minutes
    const interval = setInterval(fetchDeviceDetails, 120000)
    return () => clearInterval(interval)
  }, [deviceId])

  const fetchDeviceDetails = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/api/bitaxe/system/device/${deviceId}/`)
      setDeviceData(response.data)
    } catch (error) {
      console.error('Error fetching device details:', error)
    } finally {
      setLoading(false)
    }
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

  const formatUptime = (seconds) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const formatNumber = (num) => {
    if (!num) return '0'
    if (num >= 1e15) return (num / 1e15).toFixed(1) + 'P'
    if (num >= 1e12) return (num / 1e12).toFixed(1) + 'T'
    if (num >= 1e9) return (num / 1e9).toFixed(1) + 'G'
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
    return num.toString()
  }

  const formatHashrateGH = (value) => {
    if (!value) return '0 GH/s'
    return `${parseFloat(value).toFixed(2)} GH/s`
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
          <div className="text-xs text-muted-foreground mb-2">
            {new Date(label).toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
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
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => navigate('/bitaxe')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Device Not Found</h1>
            <p className="text-muted-foreground">The requested device could not be found</p>
          </div>
        </div>
      </div>
    )
  }

  const { device, latest_mining, latest_hardware, latest_system, hashrate_trend_24h, temperature_trend_24h } = deviceData

  // Prepare chart data
  const hashrateChartData = hashrate_trend_24h?.map(stat => ({
    time: formatDate(stat.recorded_at),
    hashrate: stat.hashrate_ghs || 0,
    shares_accepted: stat.shares_accepted,
  })) || []

  const temperatureChartData = temperature_trend_24h?.map(log => ({
    time: formatDate(log.recorded_at),
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
      {/* ============================================ */}
      {/* HEADER - Device info with back button */}
      {/* ============================================ */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/mining')} className="w-8 h-8 sm:w-10 sm:h-10 shrink-0 self-start">
          <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-blue-500/10">
              <Cpu className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold tracking-tight truncate">{device.device_name}</h1>
              <p className="text-xs sm:text-sm text-muted-foreground">
                <span className="font-mono">{device.device_id}</span>
                <span className="mx-1 sm:mx-2">•</span>
                <span className="font-mono">{device.ip_address}</span>
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 self-end sm:self-auto">
          <Badge
            variant={device.is_active ? 'default' : 'destructive'}
            className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm"
          >
            <StatusIndicator status={device.is_active ? 'online' : 'offline'} size="sm" />
            <span className="ml-1.5 sm:ml-2">{device.is_active ? 'Online' : 'Offline'}</span>
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchDeviceDetails} disabled={loading} className="h-8 sm:h-9">
            <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline ml-2">Refresh</span>
          </Button>
        </div>
      </div>

      {/* ============================================ */}
      {/* HERO STATS - Key metrics at a glance */}
      {/* ============================================ */}
      {latest_mining && latest_hardware && (
        <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
          <QuickStat
            icon={Hash}
            label="Hashrate"
            value={`${latest_mining.hashrate_ghs?.toFixed(2)} GH/s`}
            subValue={latest_system?.expected_hashrate ? `Target: ${latest_system.expected_hashrate.toFixed(2)} GH/s` : null}
            iconColor="text-blue-500"
          />
          <QuickStat
            icon={Thermometer}
            label="Temperature"
            value={`${latest_hardware.temperature_c?.toFixed(1)}°C`}
            subValue={`Fan: ${latest_hardware.fan_speed_rpm} RPM`}
            status={tempStatus}
            iconColor="text-red-500"
          />
          <QuickStat
            icon={Zap}
            label="Power"
            value={`${latest_hardware.power_watts?.toFixed(1)}W`}
            subValue={`Efficiency: ${latest_hardware.efficiency_j_per_th?.toFixed(1)} J/TH`}
            iconColor="text-yellow-500"
          />
          <QuickStat
            icon={CheckCircle2}
            label="Shares"
            value={latest_mining.shares_accepted?.toLocaleString()}
            subValue={`${latest_mining.shares_rejected} rejected • ${formatUptime(latest_mining.uptime_seconds)}`}
            iconColor="text-green-500"
          />
        </div>
      )}

      {/* ============================================ */}
      {/* PERFORMANCE SUMMARY BAR */}
      {/* ============================================ */}
      {latest_system && latest_mining && (
        <Card className="bg-gradient-to-r from-muted/50 to-muted/30">
          <CardContent className="py-3 sm:py-4">
            <div className="grid gap-4 sm:gap-6 grid-cols-3">
              <div className="text-center sm:text-left">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Performance</p>
                <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 justify-center sm:justify-start">
                  <span className="text-lg sm:text-2xl font-bold">{efficiencyPercent}%</span>
                  {parseFloat(efficiencyPercent) >= 95 && <Badge variant="default" className="text-[10px] sm:text-xs">Optimal</Badge>}
                </div>
              </div>
              <div className="text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Acceptance Rate</p>
                <span className="text-lg sm:text-2xl font-bold text-green-500">{acceptanceRate}%</span>
              </div>
              <div className="text-center sm:text-right">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 sm:mb-1">Best Difficulty</p>
                <span className="text-lg sm:text-2xl font-bold text-orange-500">{formatNumber(latest_mining.best_difficulty)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================ */}
      {/* MAIN CONTENT TABS */}
      {/* ============================================ */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="w-full overflow-x-auto lg:w-auto lg:inline-grid lg:grid-cols-4">
          <TabsTrigger value="overview" className="gap-1.5 sm:gap-2">
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Overview
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
        <TabsContent value="overview" className="space-y-6">
          {/* Charts Row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Hashrate Trend */}
            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Hashrate Trend</CardTitle>
                    <CardDescription>24-hour mining performance</CardDescription>
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
                        className="text-xs"
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => {
                          try {
                            return new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                          } catch { return value }
                        }}
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
                    No hashrate data available
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
                      <XAxis dataKey="time" className="text-xs" axisLine={false} tickLine={false} tick={false} />
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
                      <XAxis dataKey="time" className="text-xs" axisLine={false} tickLine={false} tick={false} />
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
                  <InfoRow label="Best Difficulty" value={formatNumber(latest_mining.best_difficulty)} />
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
                        <Network className={`h-5 w-5 ${latest_system.is_using_fallback ? 'text-red-400' : 'text-emerald-400'}`} />
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
