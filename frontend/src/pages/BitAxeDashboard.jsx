import { Activity, ArrowRight, Hash, TrendingUp, Trophy, Users, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'

export default function BitAxeDashboard() {
  const navigate = useNavigate()
  const [poolStats, setPoolStats] = useState([])
  const [latestStats, setLatestStats] = useState(null)
  const [statistics, setStatistics] = useState(null)
  const [devices, setDevices] = useState([])
  const [deviceMiningStats, setDeviceMiningStats] = useState([])
  const [deviceHardwareStats, setDeviceHardwareStats] = useState([])
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

      // Fetch all data in parallel
      const [poolRes, latestRes, statsRes, devicesRes, miningRes, hardwareRes] = await Promise.all([
        api.get('/api/bitaxe/pool/?limit=50'),
        api.get('/api/bitaxe/pool/latest/'),
        api.get('/api/bitaxe/pool/statistics/?days=7'),
        api.get('/api/bitaxe/devices/'),
        api.get('/api/bitaxe/mining/latest/'),
        api.get('/api/bitaxe/hardware/latest/'),
      ])

      setPoolStats(poolRes.data.results || poolRes.data || [])
      setLatestStats(latestRes.data)
      setStatistics(statsRes.data)
      setDevices(devicesRes.data.results || devicesRes.data || [])
      setDeviceMiningStats(miningRes.data || [])
      setDeviceHardwareStats(hardwareRes.data || [])
    } catch (error) {
      console.error('Error fetching BitAxe data:', error)
    } finally {
      setLoading(false)
    }
  };
  const formatHashrate = (hashrateStr) => {
    return hashrateStr || 'N/A'
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
    if (num > 1e15) return `${(num / 1e15).toFixed(2)} quadrillion`
    if (num > 1e12) return `${(num / 1e12).toFixed(2)} trillion`
    if (num > 1e9) return `${(num / 1e9).toFixed(2)} billion`
    if (num > 1e6) return `${(num / 1e6).toFixed(2)} million`
    return num.toLocaleString()
  }

  // Prepare chart data for hashrate trends
  const hashrateChartData = poolStats.slice().reverse().map(stat => ({
    time: formatDate(stat.recorded_at),
    hashrate_1m_ghs: stat.hashrate_1m_ghs || 0,
    hashrate_1d_ghs: stat.hashrate_1d_ghs || 0,
    shares: stat.shares,
  }))

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">BitAxe Dashboard</h1>
          <p className="text-muted-foreground">Mining pool statistics and performance monitoring</p>
        </div>
        {latestStats && (
          <Badge variant="outline" className="text-lg px-4 py-2">
            <Activity className="h-4 w-4 mr-2 inline" />
            {latestStats.workers} Worker{latestStats.workers !== 1 ? 's' : ''} Active
          </Badge>
        )}
      </div>

      {/* Statistics Cards */}
      {loading && !latestStats ? (
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : latestStats ? (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Current Hashrate</CardTitle>
              <Hash className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_1m)}</div>
              <p className="text-xs text-muted-foreground">1 minute average</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">24h Hashrate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_1d)}</div>
              <p className="text-xs text-muted-foreground">Daily average</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Shares</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{latestStats.shares?.toLocaleString() || '0'}</div>
              <p className="text-xs text-muted-foreground">Accepted shares</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Best Share</CardTitle>
              <Trophy className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{latestStats.bestshare?.toFixed(2) || '0'}</div>
              <p className="text-xs text-muted-foreground">Difficulty</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Device Cards */}
      {deviceMiningStats.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Active Devices</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {deviceMiningStats.map((stat) => {
              const hardware = deviceHardwareStats.find(h => h.device === stat.device) || {}
              const device = devices.find(d => d.id === stat.device)
              return (
                <Card key={stat.device} className="cursor-pointer hover:border-primary transition-colors" onClick={() => navigate(`/bitaxe/device/${device?.device_id}`)}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{stat.device_name}</CardTitle>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <CardDescription>Click for detailed view</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Hashrate:</span>
                      <span className="text-sm font-bold">{stat.hashrate_ghs?.toFixed(2)} GH/s</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Shares:</span>
                      <div className="flex gap-1">
                        <Badge variant="outline" className="text-xs">{stat.shares_accepted}</Badge>
                        <Badge variant="secondary" className="text-xs">{stat.shares_rejected}</Badge>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Temperature:</span>
                      <span className={`text-sm font-medium ${hardware.temperature_c > 60 ? 'text-red-500' : ''}`}>
                        {hardware.temperature_c?.toFixed(1)}°C
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Power:</span>
                      <span className="text-sm">{hardware.power_watts?.toFixed(1)}W</span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* Main Content with Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Pool Overview</TabsTrigger>
          <TabsTrigger value="hashrate">Hashrate</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="solo-mining">Solo Mining</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Hashrate Comparison Chart */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Hashrate Trend</CardTitle>
                <CardDescription>1-minute vs 24-hour average hashrate</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-80 w-full" />
                ) : hashrateChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={hashrateChartData}>
                      <defs>
                        <linearGradient id="colorHashrate1m" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorHashrate1d" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="hashrate_1m_ghs"
                        stroke="#10b981"
                        fillOpacity={1}
                        fill="url(#colorHashrate1m)"
                        name="1m Hashrate (GH/s)"
                      />
                      <Area
                        type="monotone"
                        dataKey="hashrate_1d_ghs"
                        stroke="#3b82f6"
                        fillOpacity={1}
                        fill="url(#colorHashrate1d)"
                        name="24h Hashrate (GH/s)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No hashrate data available</p>
                )}
              </CardContent>
            </Card>

            {/* Pool Information */}
            {latestStats && (
              <Card>
                <CardHeader>
                  <CardTitle>Pool Information</CardTitle>
                  <CardDescription>CKPool connection details</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Pool Address</div>
                    <div className="text-sm font-mono break-all">{latestStats.pool_address}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Last Share</div>
                    <div className="text-sm">{formatTimestamp(latestStats.lastshare)}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Authorized</div>
                    <div className="text-sm">{formatTimestamp(latestStats.authorised)}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Best Ever</div>
                    <div className="text-sm font-bold">{latestStats.bestever}</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Performance Metrics */}
            {statistics && (
              <Card>
                <CardHeader>
                  <CardTitle>7-Day Statistics</CardTitle>
                  <CardDescription>Performance summary</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Total Shares (Period)</div>
                    <div className="text-2xl font-bold">{statistics.total_shares?.toLocaleString() || '0'}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Max Hashrate</div>
                    <div className="text-2xl font-bold">{statistics.max_hashrate_ghs?.toFixed(2) || '0'} GH/s</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Best Share (7d)</div>
                    <div className="text-2xl font-bold">{statistics.best_share?.toFixed(2) || '0'}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground">Data Points</div>
                    <div className="text-sm">{statistics.data_points || 0} samples</div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Hashrate Tab */}
        <TabsContent value="hashrate" className="space-y-4">
          <div className="grid gap-4">
            {/* All Hashrate Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Hashrate Breakdown</CardTitle>
                <CardDescription>All time-based hashrate metrics</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-64 w-full" />
                ) : latestStats ? (
                  <div className="grid gap-4 md:grid-cols-5">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-sm font-medium text-muted-foreground mb-2">1 Minute</div>
                      <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_1m)}</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-sm font-medium text-muted-foreground mb-2">5 Minutes</div>
                      <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_5m)}</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-sm font-medium text-muted-foreground mb-2">1 Hour</div>
                      <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_1hr)}</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-sm font-medium text-muted-foreground mb-2">24 Hours</div>
                      <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_1d)}</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-sm font-medium text-muted-foreground mb-2">7 Days</div>
                      <div className="text-2xl font-bold">{formatHashrate(latestStats.hashrate_7d)}</div>
                    </div>
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No data available</p>
                )}
              </CardContent>
            </Card>

            {/* Shares Over Time */}
            <Card>
              <CardHeader>
                <CardTitle>Shares Over Time</CardTitle>
                <CardDescription>Cumulative accepted shares</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-64 w-full" />
                ) : hashrateChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={hashrateChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="shares"
                        stroke="#10b981"
                        strokeWidth={2}
                        name="Total Shares"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No share data</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Pool Statistics</CardTitle>
              <CardDescription>Historical pool performance data</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  {[...Array(10)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : poolStats.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No pool statistics found</p>
              ) : (
                <div className="overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>1m Hashrate</TableHead>
                        <TableHead>24h Hashrate</TableHead>
                        <TableHead>Workers</TableHead>
                        <TableHead>Total Shares</TableHead>
                        <TableHead>Best Share</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {poolStats.map((stat, index) => (
                        <TableRow key={stat.id || index}>
                          <TableCell className="font-medium">
                            {formatDate(stat.recorded_at)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{formatHashrate(stat.hashrate_1m)}</Badge>
                          </TableCell>
                          <TableCell>{formatHashrate(stat.hashrate_1d)}</TableCell>
                          <TableCell>
                            <div className="flex items-center">
                              <Users className="h-3 w-3 mr-1" />
                              {stat.workers}
                            </div>
                          </TableCell>
                          <TableCell>{stat.shares?.toLocaleString()}</TableCell>
                          <TableCell>
                            <Badge variant={stat.bestshare > 10000 ? 'default' : 'secondary'}>
                              {stat.bestshare?.toFixed(2)}
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

        {/* Solo Mining Tab */}
        <TabsContent value="solo-mining" className="space-y-4">
          <div className="grid gap-4">
            {/* Explanation Card */}
            <Card>
              <CardHeader>
                <CardTitle>Solo Mining Statistics</CardTitle>
                <CardDescription>
                  Understanding your chances of finding a Bitcoin block with your current hashrate
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Solo mining means you're competing to find blocks independently. When you find a block, you receive the full block reward (currently 3.125 BTC + transaction fees).
                  These statistics are calculated based on the current Bitcoin network difficulty and your average hashrate.
                </p>
              </CardContent>
            </Card>

            {/* Probability Statistics */}
            {latestStats && deviceMiningStats.length > 0 && (
              <>
                {(() => {
                  // Bitcoin network stats (as of October 2025)
                  const NETWORK_HASHRATE_EH = 650 // ~650 EH/s network hashrate
                  const BLOCK_REWARD_BTC = 3.125 // Post-2024 halving
                  const BLOCKS_PER_DAY = 144 // ~10 min per block
                  const SECONDS_PER_BLOCK = 600 // 10 minutes average

                  // Calculate total device hashrate in EH/s
                  const totalDeviceHashrateGH = deviceMiningStats.reduce((sum, stat) => sum + (stat.hashrate_ghs || 0), 0)
                  const totalDeviceHashrateEH = totalDeviceHashrateGH / 1e9 // Convert GH/s to EH/s

                  // Probability calculations
                  const probabilityPerBlock = totalDeviceHashrateEH / NETWORK_HASHRATE_EH
                  const probabilityPerDay = 1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY)
                  const probabilityPerMonth = 1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY * 30)
                  const probabilityPerYear = 1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY * 365)

                  // Expected time to find a block (in days)
                  const expectedDaysToBlock = probabilityPerBlock > 0 ? 1 / (probabilityPerBlock * BLOCKS_PER_DAY) : Infinity

                  // Convert to human-readable format
                  const formatExpectedTime = (days) => {
                    if (days === Infinity || days > 365000) return 'Never (practically impossible)'
                    if (days > 365) return `${(days / 365).toFixed(0)} years`
                    if (days > 30) return `${(days / 30).toFixed(0)} months`
                    if (days > 1) return `${days.toFixed(0)} days`
                    return `${(days * 24).toFixed(0)} hours`
                  }

                  // Shares needed for one block (approximate)
                  const currentDifficulty = 92670000000000 // October 2025 approximate difficulty
                  const sharesNeededForBlock = currentDifficulty * (2 ** 32)
                  const currentSharesPerDay = deviceMiningStats.reduce((sum, stat) => sum + (stat.shares_accepted || 0), 0)
                  const estimatedDailyShares = currentSharesPerDay * (BLOCKS_PER_DAY / Math.max(poolStats.length, 1))

                  return (
                    <>
                      {/* Key Metrics */}
                      <div className="grid gap-4 md:grid-cols-4">
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Your Hashrate</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">{totalDeviceHashrateGH.toFixed(2)} GH/s</div>
                            <p className="text-xs text-muted-foreground mt-1">
                              {(totalDeviceHashrateGH / 1000).toFixed(4)} TH/s
                            </p>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Network Hashrate</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">{NETWORK_HASHRATE_EH} EH/s</div>
                            <p className="text-xs text-muted-foreground mt-1">
                              {(NETWORK_HASHRATE_EH * 1000).toLocaleString()} PH/s
                            </p>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Your Network %</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">{formatProbability(probabilityPerBlock)}</div>
                            <p className="text-xs text-muted-foreground mt-1">
                              Per block attempt
                            </p>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Block Reward</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">{BLOCK_REWARD_BTC} BTC</div>
                            <p className="text-xs text-muted-foreground mt-1">
                              + transaction fees (~0.2 BTC)
                            </p>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Probability Breakdown */}
                      <Card>
                        <CardHeader>
                          <CardTitle>Probability of Finding a Block</CardTitle>
                          <CardDescription>Likelihood of mining a Bitcoin block over different time periods</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div className="flex justify-between items-center pb-2 border-b">
                              <div>
                                <div className="font-medium">Per Block (~10 minutes)</div>
                                <div className="text-xs text-muted-foreground">Single block attempt</div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold">{formatProbability(probabilityPerBlock)}</div>
                                <div className="text-xs text-muted-foreground">{formatLargeNumber(1 / probabilityPerBlock)} attempts</div>
                              </div>
                            </div>

                            <div className="flex justify-between items-center pb-2 border-b">
                              <div>
                                <div className="font-medium">Per Day (144 blocks)</div>
                                <div className="text-xs text-muted-foreground">Daily probability</div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold">{formatProbability(probabilityPerDay)}</div>
                                <div className="text-xs text-muted-foreground">{formatLargeNumber(1 / probabilityPerDay)} attempts</div>
                              </div>
                            </div>

                            <div className="flex justify-between items-center pb-2 border-b">
                              <div>
                                <div className="font-medium">Per Month (~4,320 blocks)</div>
                                <div className="text-xs text-muted-foreground">30-day probability</div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold">{formatProbability(probabilityPerMonth)}</div>
                                <div className="text-xs text-muted-foreground">{formatLargeNumber(1 / probabilityPerMonth)} attempts</div>
                              </div>
                            </div>

                            <div className="flex justify-between items-center">
                              <div>
                                <div className="font-medium">Per Year (~52,560 blocks)</div>
                                <div className="text-xs text-muted-foreground">365-day probability</div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold">{formatProbability(probabilityPerYear)}</div>
                                <div className="text-xs text-muted-foreground">{formatLargeNumber(1 / probabilityPerYear)} attempts</div>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Expected Time & Shares */}
                      <div className="grid gap-4 md:grid-cols-2">
                        <Card>
                          <CardHeader>
                            <CardTitle>Expected Time to Block</CardTitle>
                            <CardDescription>Average time based on current hashrate</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-4">
                              <div>
                                <div className="text-sm font-medium text-muted-foreground mb-2">Statistical Average</div>
                                <div className="text-3xl font-bold">{formatExpectedTime(expectedDaysToBlock)}</div>
                                <p className="text-xs text-muted-foreground mt-2">
                                  This is a statistical average. Actual time could be shorter or much longer due to randomness.
                                </p>
                              </div>
                              <div className="pt-4 border-t">
                                <div className="text-sm font-medium text-muted-foreground mb-2">In Numbers</div>
                                <div className="text-xl font-bold">{expectedDaysToBlock.toLocaleString(undefined, { maximumFractionDigits: 0 })} days</div>
                                <div className="text-sm text-muted-foreground">
                                  ≈ {(expectedDaysToBlock / 365).toLocaleString(undefined, { maximumFractionDigits: 1 })} years
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader>
                            <CardTitle>Shares vs Block Difficulty</CardTitle>
                            <CardDescription>Understanding share difficulty relative to blocks</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-4">
                              <div>
                                <div className="text-sm font-medium text-muted-foreground mb-2">Current Difficulty</div>
                                <div className="text-2xl font-bold">{(currentDifficulty / 1e12).toFixed(2)}T</div>
                              </div>
                              <div>
                                <div className="text-sm font-medium text-muted-foreground mb-2">Your Total Shares</div>
                                <div className="text-2xl font-bold">{deviceMiningStats.reduce((sum, stat) => sum + (stat.shares_accepted || 0), 0).toLocaleString()}</div>
                              </div>
                              <div>
                                <div className="text-sm font-medium text-muted-foreground mb-2">Shares Needed (est.)</div>
                                <div className="text-xl font-bold">{(sharesNeededForBlock / 1e15).toFixed(2)} quadrillion</div>
                                <p className="text-xs text-muted-foreground mt-1">
                                  Pool difficulty shares, not block-level
                                </p>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Reality Check Card */}
                      <Card className="border-amber-500/50">
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2">
                            <Trophy className="h-5 w-5" />
                            Solo Mining Reality Check
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            <p className="text-sm">
                              <strong>⚠️ Important Understanding:</strong> With a hashrate of {totalDeviceHashrateGH.toFixed(2)} GH/s,
                              you have approximately a <strong>{formatProbability(probabilityPerBlock)}</strong> chance per block
                              (or <strong>{formatLargeNumber(1 / probabilityPerBlock)}</strong> attempts needed on average).
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Solo mining with ASICs like BitAxe is primarily done for:
                            </p>
                            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1 ml-2">
                              <li><strong>Supporting the network:</strong> Contributing to Bitcoin's decentralization</li>
                              <li><strong>Learning:</strong> Understanding how Bitcoin mining works</li>
                              <li><strong>The lottery aspect:</strong> The tiny chance of winning the full block reward</li>
                              <li><strong>Fun:</strong> Being part of Bitcoin's security infrastructure</li>
                            </ul>
                            <p className="text-sm text-muted-foreground">
                              💡 <strong>Tip:</strong> Your best share of <strong>{latestStats.bestshare?.toFixed(2)}</strong> shows you're
                              submitting valid work. Keep mining and supporting the network! Every hash counts toward Bitcoin's security.
                            </p>
                            {latestStats.bestshare > 1000000 && (
                              <p className="text-sm font-medium text-green-600">
                                🎉 You've found a share with difficulty over 1M! That's impressive for a small miner.
                              </p>
                            )}
                          </div>
                        </CardContent>
                      </Card>

                      {/* Best Share Progress */}
                      <Card>
                        <CardHeader>
                          <CardTitle>Your Best Achievements</CardTitle>
                          <CardDescription>Tracking your highest difficulty shares</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div>
                              <div className="flex justify-between mb-2">
                                <span className="text-sm font-medium">Best Share (Current Session)</span>
                                <span className="text-sm font-bold">{latestStats.bestshare?.toFixed(2)}</span>
                              </div>
                              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                                <div
                                  className="bg-primary h-full transition-all duration-500"
                                  style={{ width: `${Math.min((latestStats.bestshare / 1000000) * 100, 100)}%` }}
                                />
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">
                                {((latestStats.bestshare / 1000000) * 100).toFixed(4)}% of 1M difficulty
                              </p>
                            </div>

                            <div>
                              <div className="flex justify-between mb-2">
                                <span className="text-sm font-medium">Best Share (All Time)</span>
                                <span className="text-sm font-bold">{latestStats.bestever?.toLocaleString()}</span>
                              </div>
                              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                                <div
                                  className="bg-green-600 h-full transition-all duration-500"
                                  style={{ width: `${Math.min((latestStats.bestever / 1000000) * 100, 100)}%` }}
                                />
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">
                                {((latestStats.bestever / 1000000) * 100).toFixed(4)}% of 1M difficulty
                              </p>
                            </div>

                            <div className="pt-4 border-t">
                              <div className="text-sm text-muted-foreground">
                                <strong>For reference:</strong> A valid Bitcoin block requires finding a hash that meets the network difficulty of approximately {(currentDifficulty / 1e12).toFixed(2)} trillion.
                                Your best share shows you're finding valid proof-of-work, just not at the block level yet.
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </>
                  )
                })()}
              </>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
