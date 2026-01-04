import {
    Activity,
    ArrowLeft,
    CheckCircle2,
    Clock,
    Cpu,
    Gauge,
    Hash,
    Network,
    RefreshCw,
    Server,
    Thermometer,
    TrendingUp,
    Zap
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

// Status indicator with animated pulse
const StatusIndicator = ({ isActive }) => (
  <span className="relative flex h-3 w-3">
    {isActive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
    <span className={`relative inline-flex rounded-full h-3 w-3 ${isActive ? 'bg-green-500' : 'bg-red-500'}`}></span>
  </span>
)

// Quick stat card for hero section
const QuickStat = ({ icon: Icon, label, value, subValue, color = 'blue' }) => (
  <Card className={`bg-gradient-to-br from-${color}-500/10 to-transparent border-${color}-500/20`}>
    <CardContent className="pt-3 sm:pt-4">
      <div className="flex items-center gap-2 sm:gap-3">
        <div className={`p-2 sm:p-2.5 rounded-xl bg-${color}-500/20`}>
          <Icon className={`h-4 w-4 sm:h-5 sm:w-5 text-${color}-400`} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] sm:text-xs text-muted-foreground truncate">{label}</p>
          <p className="text-base sm:text-xl font-bold truncate">{value}</p>
          {subValue && <p className="text-[10px] sm:text-xs text-muted-foreground truncate">{subValue}</p>}
        </div>
      </div>
    </CardContent>
  </Card>
)

// Info row for detail sections
const InfoRow = ({ label, value, mono = false }) => (
  <div className="flex justify-between items-center py-2 border-b border-border/50 last:border-0">
    <span className="text-sm text-muted-foreground">{label}</span>
    <span className={`text-sm font-medium ${mono ? 'font-mono' : ''}`}>{value || 'N/A'}</span>
  </div>
)

// Health bar visualization
const HealthBar = ({ label, value, max, unit = '', thresholds = { warning: 70, danger: 90 } }) => {
  const percentage = Math.min(100, (value / max) * 100)
  const status = percentage >= thresholds.danger ? 'bg-red-500' :
                 percentage >= thresholds.warning ? 'bg-yellow-500' : 'bg-green-500'

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value?.toFixed(1)}{unit}</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full ${status} transition-all duration-500`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

export default function AvalonDeviceDetails() {
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
      // Fetch device details and historical data
      const [deviceResponse, miningHistoryResponse, hardwareHistoryResponse] = await Promise.all([
        api.get(`/api/avalon/devices/${deviceId}/`),
        api.get(`/api/avalon/mining-stats/?device_id=${deviceId}&limit=20`),
        api.get(`/api/avalon/hardware-logs/?device_id=${deviceId}&limit=20`)
      ])

      setDeviceData({
        ...deviceResponse.data,
        mining_history: miningHistoryResponse.data || [],
        hardware_history: hardwareHistoryResponse.data || []
      })
    } catch (error) {
      console.error('Error fetching Avalon device details:', error)
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
    const remainingSeconds = seconds % 60
    return `${hours}h ${minutes}m ${remainingSeconds}s`
  }

  const formatHashrate = (value) => {
    if (!value) return 'N/A'
    // Avalon reports in GH/s, convert to TH/s for display
    const ths = parseFloat(value) / 1000
    return `${ths.toFixed(2)} TH/s`
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
            {label}
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
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-8 w-64" />
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!deviceData) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h1 className="text-2xl font-bold mb-4">Device Not Found</h1>
        <p className="text-muted-foreground mb-6">
          The Avalon device with ID "{deviceId}" could not be found.
        </p>
        <Button onClick={() => navigate('/mining')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Mining Dashboard
        </Button>
      </div>
    )
  }

  const device = deviceData || {}
  const latestMining = deviceData?.latest_mining_stats || {}
  const latestHardware = deviceData?.latest_hardware_logs || {}
  const latestSystemInfo = deviceData?.latest_system_info || {}
  const miningHistory = deviceData?.mining_history || []
  const hardwareHistory = deviceData?.hardware_history || []

  // Prepare chart data
  const chartData = miningHistory.slice().reverse().map(entry => ({
    time: formatDate(entry.recorded_at),
    fullTime: entry.recorded_at,
    hashrate_ghs: entry.hashrate_ghs || 0,
    shares_accepted: entry.shares_accepted || 0,
    shares_rejected: entry.shares_rejected || 0,
    temperature: hardwareHistory.find(h =>
      Math.abs(new Date(h.recorded_at) - new Date(entry.recorded_at)) < 60000
    )?.temperature_c || null,
    power: hardwareHistory.find(h =>
      Math.abs(new Date(h.recorded_at) - new Date(entry.recorded_at)) < 60000
    )?.power_watts || null,
  }))

  // Temperature status
  const tempStatus = latestHardware.temperature_c > 70 ? 'critical' :
                     latestHardware.temperature_c > 55 ? 'warning' : 'good'

  // Calculate acceptance rate
  const acceptanceRate = latestMining.shares_accepted && latestMining.shares_rejected !== undefined
    ? ((latestMining.shares_accepted / (latestMining.shares_accepted + latestMining.shares_rejected)) * 100).toFixed(1)
    : null

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start sm:items-center gap-3 sm:gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/mining')} className="h-8 w-8 sm:h-10 sm:w-10 shrink-0">
            <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
          </Button>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-2 sm:p-2.5 rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 border border-orange-500/30">
              <Server className="h-5 w-5 sm:h-6 sm:w-6 text-orange-400" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-lg sm:text-2xl font-bold truncate">{device.device_name || `Avalon ${deviceId}`}</h1>
                <Badge
                  variant={device.is_active ? "default" : "destructive"}
                  className="flex items-center gap-1 sm:gap-1.5 text-xs"
                >
                  <StatusIndicator isActive={device.is_active} />
                  {device.is_active ? "Online" : "Offline"}
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-muted-foreground">
                {device.device_id} • {device.ip_address}
              </p>
            </div>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={fetchDeviceDetails} disabled={loading} className="self-end sm:self-auto h-8 sm:h-9">
          <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${loading ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline ml-2">Refresh</span>
        </Button>
      </div>

      {/* Hero Stats */}
      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
        <QuickStat
          icon={Gauge}
          label="Current Hashrate"
          value={formatHashrate(latestMining.hashrate_ghs)}
          subValue={`${latestMining.hashrate_ghs?.toFixed(2) || 0} GH/s`}
          color="blue"
        />
        <Card className={`bg-gradient-to-br ${
          tempStatus === 'critical' ? 'from-red-500/10 border-red-500/20' :
          tempStatus === 'warning' ? 'from-yellow-500/10 border-yellow-500/20' :
          'from-green-500/10 border-green-500/20'
        } to-transparent`}>
          <CardContent className="pt-3 sm:pt-4">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className={`p-2 sm:p-2.5 rounded-xl ${
                tempStatus === 'critical' ? 'bg-red-500/20' :
                tempStatus === 'warning' ? 'bg-yellow-500/20' : 'bg-green-500/20'
              }`}>
                <Thermometer className={`h-4 w-4 sm:h-5 sm:w-5 ${
                  tempStatus === 'critical' ? 'text-red-400' :
                  tempStatus === 'warning' ? 'text-yellow-400' : 'text-green-400'
                }`} />
              </div>
              <div>
                <p className="text-[10px] sm:text-xs text-muted-foreground">Temperature</p>
                <p className="text-base sm:text-xl font-bold">
                  {latestHardware.temperature_c ? `${latestHardware.temperature_c.toFixed(1)}°C` : 'N/A'}
                </p>
                <Badge variant={tempStatus === 'good' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'} className="text-[10px] sm:text-xs mt-0.5 sm:mt-1">
                  {tempStatus === 'good' ? 'Normal' : tempStatus === 'warning' ? 'Warm' : 'Hot'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
        <QuickStat
          icon={Zap}
          label="Power"
          value={latestHardware.power_watts ? `${latestHardware.power_watts.toFixed(0)}W` : 'N/A'}
          subValue={latestHardware.efficiency_j_per_th ? `${latestHardware.efficiency_j_per_th.toFixed(1)} J/TH` : null}
          color="amber"
        />
        <QuickStat
          icon={CheckCircle2}
          label="Shares Accepted"
          value={latestMining.shares_accepted?.toLocaleString() || '0'}
          subValue={`${latestMining.shares_rejected || 0} rejected`}
          color="emerald"
        />
      </div>

      {/* Performance Summary Bar */}
      <Card className="bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border-primary/20">
        <CardContent className="py-3 sm:py-4">
          <div className="grid grid-cols-3 gap-3 sm:gap-6">
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-3">
              <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
              <div className="text-center sm:text-left">
                <p className="text-[10px] sm:text-xs text-muted-foreground">Uptime</p>
                <p className="text-xs sm:text-base font-semibold">{formatUptime(latestMining.uptime_seconds)}</p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-3 justify-center">
              <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
              <div className="text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground">Acceptance Rate</p>
                <p className="text-xs sm:text-base font-semibold">{acceptanceRate ? `${acceptanceRate}%` : 'N/A'}</p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-3 justify-end">
              <Hash className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
              <div className="text-center sm:text-right">
                <p className="text-[10px] sm:text-xs text-muted-foreground">Difficulty</p>
                <p className="text-xs sm:text-base font-semibold">{formatNumber(latestMining.difficulty)}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Information */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="w-full overflow-x-auto sm:max-w-lg">
          <TabsTrigger value="overview" className="flex items-center gap-1.5 sm:gap-2">
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="mining" className="flex items-center gap-1.5 sm:gap-2">
            <Hash className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Mining</span>
          </TabsTrigger>
          <TabsTrigger value="hardware" className="flex items-center gap-1.5 sm:gap-2">
            <Cpu className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Hardware</span>
          </TabsTrigger>
          <TabsTrigger value="charts" className="flex items-center gap-1.5 sm:gap-2">
            <TrendingUp className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Charts</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Server className="h-4 w-4 text-muted-foreground" />
                  Device Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-0">
                <InfoRow label="Device Name" value={device.device_name} />
                <InfoRow label="Device ID" value={device.device_id} mono />
                <InfoRow label="Model" value={latestSystemInfo.device_model} />
                <InfoRow label="Firmware" value={latestSystemInfo.firmware_version} mono />
                <InfoRow label="IP Address" value={device.ip_address} mono />
                <InfoRow label="Last Seen" value={formatDate(device.last_seen_at)} />
                <InfoRow label="Added" value={formatDate(device.created_at)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Network className="h-4 w-4 text-muted-foreground" />
                  Mining Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Pool URL</p>
                  <p className="text-sm font-mono break-all">{latestMining.pool_url || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Pool User</p>
                  <p className="text-sm font-mono break-all">{latestMining.pool_user || 'N/A'}</p>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Difficulty</p>
                    <p className="text-sm font-medium">{formatNumber(latestMining.difficulty)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Blocks Found</p>
                    <p className="text-sm font-medium text-yellow-500">{latestMining.blocks_found || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Mining Stats Tab */}
        <TabsContent value="mining" className="space-y-6">
          {/* Quick Stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Gauge className="h-5 w-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Current Hashrate</p>
                    <p className="text-xl font-bold">{formatHashrate(latestMining.hashrate_ghs)}</p>
                    <p className="text-xs text-muted-foreground">{latestMining.hashrate_ghs?.toFixed(2) || 'N/A'} GH/s</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-500/20">
                    <CheckCircle2 className="h-5 w-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Share Statistics</p>
                    <p className="text-xl font-bold text-green-500">{latestMining.shares_accepted?.toLocaleString() || '0'}</p>
                    <p className="text-xs text-red-400">{latestMining.shares_rejected || 0} rejected</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-yellow-500/10 to-transparent border-yellow-500/20">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-yellow-500/20">
                    <Hash className="h-5 w-5 text-yellow-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Blocks Found</p>
                    <p className="text-xl font-bold text-yellow-500">{latestMining.blocks_found || 0}</p>
                    <p className="text-xs text-muted-foreground">{formatUptime(latestMining.uptime_seconds)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Stats */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Mining Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <HealthBar
                  label="Acceptance Rate"
                  value={acceptanceRate || 0}
                  max={100}
                  unit="%"
                  thresholds={{ warning: 95, danger: 90 }}
                />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Accepted</p>
                    <p className="text-lg font-bold text-green-500">{latestMining.shares_accepted?.toLocaleString() || '0'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total Rejected</p>
                    <p className="text-lg font-bold text-red-500">{latestMining.shares_rejected?.toLocaleString() || '0'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Uptime</p>
                    <p className="text-lg font-bold">{formatUptime(latestMining.uptime_seconds)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">{formatDate(latestMining.recorded_at)}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Hardware Tab */}
        <TabsContent value="hardware" className="space-y-6">
          {/* Quick Hardware Stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className={`bg-gradient-to-br ${
              tempStatus === 'critical' ? 'from-red-500/10 border-red-500/20' :
              tempStatus === 'warning' ? 'from-yellow-500/10 border-yellow-500/20' :
              'from-green-500/10 border-green-500/20'
            } to-transparent`}>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    tempStatus === 'critical' ? 'bg-red-500/20' :
                    tempStatus === 'warning' ? 'bg-yellow-500/20' : 'bg-green-500/20'
                  }`}>
                    <Thermometer className={`h-5 w-5 ${
                      tempStatus === 'critical' ? 'text-red-400' :
                      tempStatus === 'warning' ? 'text-yellow-400' : 'text-green-400'
                    }`} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Temperature</p>
                    <p className="text-xl font-bold">
                      {latestHardware.temperature_c ? `${latestHardware.temperature_c.toFixed(1)}°C` : 'N/A'}
                    </p>
                    <Badge variant={tempStatus === 'good' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'} className="text-xs mt-1">
                      {tempStatus === 'good' ? 'Normal' : tempStatus === 'warning' ? 'Warm' : 'Hot'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-amber-500/10 to-transparent border-amber-500/20">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-amber-500/20">
                    <Zap className="h-5 w-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Power Draw</p>
                    <p className="text-xl font-bold">
                      {latestHardware.power_watts ? `${latestHardware.power_watts.toFixed(0)}W` : 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {latestHardware.efficiency_j_per_th ? `${latestHardware.efficiency_j_per_th.toFixed(1)} J/TH` : 'N/A'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Activity className="h-5 w-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">System Status</p>
                    <Badge variant={device.is_active ? "default" : "destructive"} className="mt-1">
                      {device.is_active ? "Healthy" : "Offline"}
                    </Badge>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDate(latestHardware.recorded_at)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Hardware Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Thermometer className="h-4 w-4 text-muted-foreground" />
                  Thermal Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <HealthBar
                  label="Temperature"
                  value={latestHardware.temperature_c}
                  max={85}
                  unit="°C"
                  thresholds={{ warning: 55, danger: 70 }}
                />
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Status</p>
                    <Badge variant={tempStatus === 'good' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'} className="mt-1">
                      {tempStatus === 'critical' ? 'Hot' : tempStatus === 'warning' ? 'Warm' : 'Normal'}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Fan Speed</p>
                    <p className="text-sm font-medium">
                      {latestHardware.fan_speed_rpm ? `${latestHardware.fan_speed_rpm} RPM` : 'N/A'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-muted-foreground" />
                  System Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-0">
                <InfoRow label="Memory Usage" value={latestSystemInfo.memory_usage_percent ? `${latestSystemInfo.memory_usage_percent.toFixed(1)}%` : 'N/A'} />
                <InfoRow label="Frequency" value={latestHardware.frequency_mhz ? `${latestHardware.frequency_mhz} MHz` : 'N/A'} />
                <InfoRow label="Model" value={latestSystemInfo.device_model} />
                <InfoRow label="Firmware" value={latestSystemInfo.firmware_version} mono />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Charts Tab */}
        <TabsContent value="charts" className="space-y-6">
          {/* Hashrate Trend - Full Width */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Hashrate Trend</CardTitle>
                  <CardDescription>Historical mining performance</CardDescription>
                </div>
                <Badge variant="secondary" className="font-mono">
                  {formatHashrate(latestMining.hashrate_ghs)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorHashrateAvalon" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
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
                      domain={['dataMin - 10', 'dataMax + 10']}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => formatHashrateGH(value)}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="hashrate_ghs"
                      stroke="#f97316"
                      fillOpacity={1}
                      fill="url(#colorHashrateAvalon)"
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

          {/* Temperature and Power Charts */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Temperature</CardTitle>
                  <Badge variant={tempStatus === 'good' ? 'secondary' : tempStatus === 'warning' ? 'outline' : 'destructive'}>
                    {latestHardware.temperature_c?.toFixed(0)}°C
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {chartData.some(d => d.temperature) ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                      <XAxis dataKey="time" className="text-xs" axisLine={false} tickLine={false} tick={false} />
                      <YAxis domain={['dataMin - 2', 'dataMax + 2']} className="text-xs" axisLine={false} tickLine={false} tickFormatter={(v) => `${v}°`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="temperature" stroke="#ef4444" strokeWidth={2} name="Temperature" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">No temperature data</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Power Consumption</CardTitle>
                  <Badge variant="secondary">{latestHardware.power_watts?.toFixed(0)}W</Badge>
                </div>
              </CardHeader>
              <CardContent>
                {chartData.some(d => d.power) ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                      <XAxis dataKey="time" className="text-xs" axisLine={false} tickLine={false} tick={false} />
                      <YAxis domain={['dataMin - 10', 'dataMax + 10']} className="text-xs" axisLine={false} tickLine={false} tickFormatter={(v) => `${v}W`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="power" stroke="#f59e0b" strokeWidth={2} name="Power" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">No power data</div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Share Statistics Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Share Statistics</CardTitle>
                  <CardDescription>Accepted vs rejected shares over time</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Badge variant="secondary" className="bg-green-500/20 text-green-400">
                    {latestMining.shares_accepted?.toLocaleString() || 0} accepted
                  </Badge>
                  <Badge variant="secondary" className="bg-red-500/20 text-red-400">
                    {latestMining.shares_rejected || 0} rejected
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorAcceptedAvalon" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorRejectedAvalon" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
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
                      domain={['dataMin', 'dataMax']}
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => formatNumber(value)}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="shares_accepted"
                      stackId="1"
                      stroke="#10b981"
                      fill="url(#colorAcceptedAvalon)"
                      name="Accepted"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="shares_rejected"
                      stackId="1"
                      stroke="#ef4444"
                      fill="url(#colorRejectedAvalon)"
                      name="Rejected"
                      dot={false}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-48 text-muted-foreground">
                  No share data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}