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
  const isOnline = device?.is_active !== false
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

  // Pool stats (shared)
  const [poolStats, setPoolStats] = useState([])
  const [latestStats, setLatestStats] = useState(null)
  const [statistics, setStatistics] = useState(null)

  // Bitaxe devices
  const [bitaxeDevices, setBitaxeDevices] = useState([])
  const [bitaxeDeviceMiningStats, setBitaxeDeviceMiningStats] = useState([])
  const [bitaxeDeviceHardwareStats, setBitaxeDeviceHardwareStats] = useState([])

  // Avalon devices
  const [avalonDevices, setAvalonDevices] = useState([])
  const [avalonDeviceMiningStats, setAvalonDeviceMiningStats] = useState([])
  const [avalonDeviceHardwareStats, setAvalonDeviceHardwareStats] = useState([])

  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    // Poll for new data every 2 minutes
    const interval = setInterval(fetchData, 120000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)

      // Fetch all data in parallel - both Bitaxe and Avalon
      const [
        poolRes, latestRes, statsRes,
        bitaxeDevicesRes, bitaxeMiningRes, bitaxeHardwareRes,
        avalonDevicesRes, avalonMiningRes, avalonHardwareRes
      ] = await Promise.all([
        // Pool data (shared)
        api.get('/api/bitaxe/pool/?limit=50').catch(() => ({ data: { results: [] } })),
        api.get('/api/bitaxe/pool/latest/').catch(() => ({ data: null })),
        api.get('/api/bitaxe/pool/statistics/?days=7').catch(() => ({ data: null })),

        // Bitaxe data
        api.get('/api/bitaxe/devices/').catch(() => ({ data: { results: [] } })),
        api.get('/api/bitaxe/mining/latest/').catch(() => ({ data: [] })),
        api.get('/api/bitaxe/hardware/latest/').catch(() => ({ data: [] })),

        // Avalon data
        api.get('/api/avalon/devices/').catch(() => ({ data: [] })),
        api.get('/api/avalon/mining-stats/').catch(() => ({ data: [] })),
        api.get('/api/avalon/hardware-logs/').catch(() => ({ data: [] })),
      ])

      // Pool stats (shared)
      setPoolStats(poolRes.data.results || poolRes.data || [])
      setLatestStats(latestRes.data)
      setStatistics(statsRes.data)

      // Bitaxe data
      setBitaxeDevices(bitaxeDevicesRes.data.results || bitaxeDevicesRes.data || [])
      setBitaxeDeviceMiningStats(bitaxeMiningRes.data || [])
      setBitaxeDeviceHardwareStats(bitaxeHardwareRes.data || [])

      // Avalon data
      setAvalonDevices(avalonDevicesRes.data.results || avalonDevicesRes.data || [])
      setAvalonDeviceMiningStats(avalonMiningRes.data || [])
      setAvalonDeviceHardwareStats(avalonHardwareRes.data || [])

    } catch (error) {
      console.error('Error fetching mining data:', error)
    } finally {
      setLoading(false)
    }
  };

  // Utility functions to combine both device types
  const getAllDevices = () => {
    const bitaxeDevicesWithType = bitaxeDevices.map(device => ({ ...device, deviceType: 'bitaxe' }))
    const avalonDevicesWithType = avalonDevices.map(device => ({ ...device, deviceType: 'avalon' }))
    return [...bitaxeDevicesWithType, ...avalonDevicesWithType]
  }

  const getAllMiningStats = () => {
    // Get latest mining stats per device to avoid duplicates
    const bitaxeLatestStats = bitaxeDeviceMiningStats.map(stat => ({ ...stat, deviceType: 'bitaxe' }))

    // For Avalon, get only the latest stat per device
    const avalonStatsGrouped = avalonDeviceMiningStats.reduce((acc, stat) => {
      if (!acc[stat.device] || new Date(stat.recorded_at) > new Date(acc[stat.device].recorded_at)) {
        acc[stat.device] = stat
      }
      return acc
    }, {})

    const avalonLatestStats = Object.values(avalonStatsGrouped).map(stat => ({ ...stat, deviceType: 'avalon' }))

    return [...bitaxeLatestStats, ...avalonLatestStats]
  }

  const getAllHardwareStats = () => {
    // Get latest hardware stats per device to avoid duplicates
    const bitaxeLatestStats = bitaxeDeviceHardwareStats.map(stat => ({ ...stat, deviceType: 'bitaxe' }))

    // For Avalon, get only the latest stat per device
    const avalonStatsGrouped = avalonDeviceHardwareStats.reduce((acc, stat) => {
      if (!acc[stat.device] || new Date(stat.recorded_at) > new Date(acc[stat.device].recorded_at)) {
        acc[stat.device] = stat
      }
      return acc
    }, {})

    const avalonLatestStats = Object.values(avalonStatsGrouped).map(stat => ({ ...stat, deviceType: 'avalon' }))

    return [...bitaxeLatestStats, ...avalonLatestStats]
  }

  const formatHashrate = (hashrateValue, deviceType = null) => {
    if (!hashrateValue) return 'N/A'

    // Bitaxe reports in TH/s, Avalon reports in GH/s
    if (deviceType === 'avalon') {
      // Avalon hashrate is in GH/s, convert to TH/s for display
      const ths = parseFloat(hashrateValue) / 1000
      return `${ths.toFixed(2)} TH/s`
    } else {
      // Bitaxe or unknown - assume TH/s format
      return typeof hashrateValue === 'string' ? hashrateValue : `${parseFloat(hashrateValue).toFixed(2)} TH/s`
    }
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

  // Prepare chart data for hashrate trends
  const hashrateChartData = poolStats.slice().reverse().map(stat => ({
    time: formatDate(stat.recorded_at),
    hashrate_1m_ghs: stat.hashrate_1m_ghs || 0,
    hashrate_1d_ghs: stat.hashrate_1d_ghs || 0,
    shares: stat.shares,
  }))

  // Calculate totals for summary
  const totalDevices = bitaxeDevices.length + avalonDevices.length
  const activeDevices = bitaxeDevices.filter(d => d.is_active).length + avalonDevices.filter(d => d.is_active).length
  const allMiningStats = getAllMiningStats()
  const allHardwareStats = getAllHardwareStats()

  // Calculate combined stats
  const totalHashrateGhs = allMiningStats.reduce((sum, s) => sum + (s.hashrate_ghs || 0), 0)
  const totalPowerWatts = allHardwareStats.reduce((sum, s) => sum + (s.power_watts || 0), 0)
  const avgTemp = allHardwareStats.length > 0
    ? allHardwareStats.reduce((sum, s) => sum + (s.temperature_c || 0), 0) / allHardwareStats.length
    : 0

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
              Device monitoring & pool performance
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          {latestStats && (
            <Badge variant="outline" className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm">
              <StatusIndicator status="online" size="sm" />
              <span className="ml-2">{latestStats.workers} Worker{latestStats.workers !== 1 ? 's' : ''}</span>
            </Badge>
          )}
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
            value={formatHashrate(latestStats?.hashrate_1m)}
            subtitle="1 minute average"
            icon={Hash}
            iconColor="text-blue-500"
          />
          <MetricCard
            title="24h Average"
            value={formatHashrate(latestStats?.hashrate_1d)}
            subtitle="Daily hashrate"
            icon={TrendingUp}
            iconColor="text-green-500"
          />
          <MetricCard
            title="Active Devices"
            value={`${activeDevices}/${totalDevices}`}
            subtitle={`${bitaxeDevices.length} Bitaxe, ${avalonDevices.length} Avalon`}
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
            value={latestStats?.bestshare ? formatNumber(latestStats.bestshare) : '0'}
            subtitle="All-time difficulty"
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
              const hardware = allHardwareStats.find(h => h.device === stat.device && h.deviceType === stat.deviceType) || {}
              const device = getAllDevices().find(d => d.id === stat.device && d.deviceType === stat.deviceType) || {}
              const deviceType = stat.deviceType || 'bitaxe'
              const navPath = deviceType === 'avalon'
                ? `/avalon/device/${device?.device_id}`
                : `/bitaxe/device/${device?.device_id}`
              return (
                <DeviceCard
                  key={`${stat.device}-${stat.deviceType}`}
                  device={device}
                  miningStats={stat}
                  hardwareStats={hardware}
                  deviceType={deviceType}
                  onClick={() => navigate(navPath)}
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
        <TabsList className="w-full overflow-x-auto lg:w-auto lg:inline-grid lg:grid-cols-5">
          <TabsTrigger value="pool" className="gap-1.5 sm:gap-2">
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Pool
          </TabsTrigger>
          <TabsTrigger value="bitaxe" className="gap-1.5 sm:gap-2">
            <Cpu className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Bitaxe
          </TabsTrigger>
          <TabsTrigger value="avalon" className="gap-1.5 sm:gap-2">
            <Server className="h-3.5 w-3.5 sm:h-4 sm:w-4 hidden sm:block" />
            Avalon
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
                  <CardDescription>1-minute vs 24-hour average comparison</CardDescription>
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
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => {
                        try {
                          return new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                        } catch {
                          return value
                        }
                      }}
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

            {/* 7-Day Statistics */}
            {statistics && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500" />
                    7-Day Performance
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

        {/* Bitaxe Devices Tab */}
        <TabsContent value="bitaxe" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <Cpu className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Bitaxe Devices</CardTitle>
                    <CardDescription>{bitaxeDevices.length} device{bitaxeDevices.length !== 1 ? 's' : ''} registered</CardDescription>
                  </div>
                </div>
                <Badge variant="outline">{bitaxeDevices.filter(d => d.is_active).length} Online</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-64 w-full" />
              ) : bitaxeDevices.length > 0 ? (
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Device</TableHead>
                        <TableHead className="font-semibold">Status</TableHead>
                        <TableHead className="font-semibold">Hashrate</TableHead>
                        <TableHead className="font-semibold">Temp</TableHead>
                        <TableHead className="font-semibold">Power</TableHead>
                        <TableHead className="font-semibold">Efficiency</TableHead>
                        <TableHead className="font-semibold w-[50px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {bitaxeDevices.map((device) => {
                        const miningStats = bitaxeDeviceMiningStats.find(stat => stat.device === device.id)
                        const hardwareStats = bitaxeDeviceHardwareStats.find(stat => stat.device === device.id)
                        const temp = hardwareStats?.temperature_c
                        const tempColor = temp > 70 ? 'text-red-500' : temp > 60 ? 'text-yellow-500' : ''
                        return (
                          <TableRow key={device.device_id} className="hover:bg-muted/30">
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Cpu className="h-4 w-4 text-blue-500" />
                                <span className="font-medium">{device.device_name}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <StatusIndicator status={device.is_active ? 'online' : 'offline'} />
                                <Badge variant={device.is_active ? "default" : "destructive"} className="text-xs">
                                  {device.is_active ? "Online" : "Offline"}
                                </Badge>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono">{formatDeviceHashrate(miningStats?.hashrate_ghs, 'bitaxe')}</TableCell>
                            <TableCell className={tempColor}>{temp ? `${temp.toFixed(1)}°C` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.power_watts ? `${hardwareStats.power_watts.toFixed(0)}W` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.efficiency_j_per_th ? `${hardwareStats.efficiency_j_per_th.toFixed(1)} J/TH` : 'N/A'}</TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => navigate(`/bitaxe/device/${device.device_id}`)}
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
                  <p className="text-muted-foreground">No Bitaxe devices found</p>
                  <p className="text-sm text-muted-foreground/70 mt-1">Devices will appear here once registered</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Avalon Devices Tab */}
        <TabsContent value="avalon" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/10">
                    <Server className="h-5 w-5 text-purple-500" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Avalon Devices</CardTitle>
                    <CardDescription>{avalonDevices.length} device{avalonDevices.length !== 1 ? 's' : ''} registered</CardDescription>
                  </div>
                </div>
                <Badge variant="outline">{avalonDevices.filter(d => d.is_active).length} Online</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-64 w-full" />
              ) : avalonDevices.length > 0 ? (
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Device</TableHead>
                        <TableHead className="font-semibold">Status</TableHead>
                        <TableHead className="font-semibold">Hashrate</TableHead>
                        <TableHead className="font-semibold">Temp</TableHead>
                        <TableHead className="font-semibold">Power</TableHead>
                        <TableHead className="font-semibold">Efficiency</TableHead>
                        <TableHead className="font-semibold">Shares</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {avalonDevices.map((device) => {
                        const miningStats = avalonDeviceMiningStats.find(stat => stat.device === device.id)
                        const hardwareStats = avalonDeviceHardwareStats.find(stat => stat.device === device.id)
                        const temp = hardwareStats?.temperature_c
                        const tempColor = temp > 70 ? 'text-red-500' : temp > 60 ? 'text-yellow-500' : ''
                        return (
                          <TableRow key={device.device_id} className="hover:bg-muted/30">
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Server className="h-4 w-4 text-purple-500" />
                                <span className="font-medium">{device.device_name}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <StatusIndicator status={device.is_active ? 'online' : 'offline'} />
                                <Badge variant={device.is_active ? "default" : "destructive"} className="text-xs">
                                  {device.is_active ? "Online" : "Offline"}
                                </Badge>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono">{formatDeviceHashrate(miningStats?.hashrate_ghs, 'avalon')}</TableCell>
                            <TableCell className={tempColor}>{temp ? `${temp.toFixed(1)}°C` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.power_watts ? `${hardwareStats.power_watts.toFixed(0)}W` : 'N/A'}</TableCell>
                            <TableCell>{hardwareStats?.efficiency_j_per_th ? `${hardwareStats.efficiency_j_per_th.toFixed(1)} J/TH` : 'N/A'}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Badge variant="outline" className="text-xs text-green-600 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800">
                                  {formatShares(miningStats?.shares_accepted)}
                                </Badge>
                                <span className="text-muted-foreground">/</span>
                                <Badge variant="outline" className="text-xs text-red-600 border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800">
                                  {formatShares(miningStats?.shares_rejected)}
                                </Badge>
                              </div>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Server className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">No Avalon devices found</p>
                  <p className="text-sm text-muted-foreground/70 mt-1">Devices will appear here once registered</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Hashrate Tab */}
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
                      className="text-xs"
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => {
                        try {
                          return new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                        } catch {
                          return value
                        }
                      }}
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
                    <CardDescription>Recent pool performance snapshots</CardDescription>
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
                      {poolStats.slice(0, 20).map((stat, index) => (
                        <TableRow key={stat.id || index} className="hover:bg-muted/30">
                          <TableCell className="font-medium text-sm">
                            {formatDate(stat.recorded_at)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono text-xs">
                              {formatHashrate(stat.hashrate_1m)}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{formatHashrate(stat.hashrate_1d)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <Users className="h-3.5 w-3.5 text-muted-foreground" />
                              <span>{stat.workers}</span>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{formatShares(stat.shares)}</TableCell>
                          <TableCell>
                            <Badge
                              variant={stat.bestshare > 1e9 ? 'default' : stat.bestshare > 1e6 ? 'secondary' : 'outline'}
                              className="font-mono text-xs"
                            >
                              {stat.bestshare ? formatNumber(stat.bestshare) : '0'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
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
