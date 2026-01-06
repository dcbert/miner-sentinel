import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  Battery,
  Cpu,
  DollarSign,
  Flame,
  Hash,
  Target,
  Timer,
  TrendingUp,
  Trophy,
  Zap
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

// Format difficulty to human-readable
const formatDifficulty = (diff) => {
  if (diff === null || diff === undefined || diff === 0) return '0'
  if (diff >= 1e15) return `${(diff / 1e15).toFixed(2)}P`
  if (diff >= 1e12) return `${(diff / 1e12).toFixed(2)}T`
  if (diff >= 1e9) return `${(diff / 1e9).toFixed(2)}G`
  if (diff >= 1e6) return `${(diff / 1e6).toFixed(2)}M`
  if (diff >= 1e3) return `${(diff / 1e3).toFixed(2)}K`
  return diff.toString()
}

const formatCurrency = (value, decimals = 2) => {
  return `$${Number(value).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return '0'
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// Loading skeleton
function AnalyticsSkeleton() {
  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <Skeleton className="h-7 sm:h-8 w-48 sm:w-64" />
        <Skeleton className="h-4 w-72 sm:w-96 mt-2" />
      </div>
      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-24 sm:h-32" />
        ))}
      </div>
      <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-2">
        <Skeleton className="h-72 sm:h-96" />
        <Skeleton className="h-72 sm:h-96" />
      </div>
    </div>
  )
}

// Format probability percentage (clamp to 0-100)
const formatProbability = (prob) => {
  if (prob === null || prob === undefined) return '0.0000'
  const clamped = Math.min(Math.max(Number(prob), 0), 100)
  return clamped.toFixed(4)
}

// Best Difficulty Prediction Card
function PredictionCard({ prediction }) {
  const prob1h = Math.min(prediction?.probability_to_beat_current_best?.['1_hour'] || 0, 100)
  const prob24h = Math.min(prediction?.probability_to_beat_current_best?.['24_hours'] || 0, 100)
  const prob7d = Math.min(prediction?.probability_to_beat_current_best?.['7_days'] || 0, 100)

  // Format expected time for display
  const expectedHours = prediction?.expected_time_to_beat?.hours || 0
  const expectedDays = prediction?.expected_time_to_beat?.days || 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Target className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
          Best Difficulty Prediction
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">
          Statistical analysis: when will you beat your current best?
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 sm:space-y-6">
        {/* Current Best */}
        <div className="flex items-center justify-between p-3 sm:p-4 rounded-lg bg-muted/50">
          <div>
            <p className="text-xs sm:text-sm text-muted-foreground">Current All-Time Best</p>
            <p className="text-xl sm:text-3xl font-bold text-primary">
              {prediction?.all_time_best_formatted || '0'}
            </p>
            {prediction?.all_time_best_timestamp && (
              <p className="text-[10px] sm:text-xs text-muted-foreground">
                Achieved {new Date(prediction.all_time_best_timestamp).toLocaleDateString()}
              </p>
            )}
          </div>
          <Award className="h-8 w-8 sm:h-12 sm:w-12 text-primary/30" />
        </div>

        {/* Key Stats Grid */}
        <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
          <div className="p-3 sm:p-4 rounded-lg border bg-primary/5">
            <div className="flex items-center gap-2 mb-1 sm:mb-2">
              <Timer className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-primary" />
              <span className="text-xs sm:text-sm font-medium">Expected Time to New Best</span>
            </div>
            <p className="text-lg sm:text-2xl font-bold text-primary">
              {prediction?.expected_time_to_beat?.formatted || 'N/A'}
            </p>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              Based on your current hashrate
            </p>
          </div>

          <div className="p-3 sm:p-4 rounded-lg border">
            <div className="flex items-center gap-2 mb-1 sm:mb-2">
              <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground" />
              <span className="text-xs sm:text-sm text-muted-foreground">Combined Hashrate</span>
            </div>
            <p className="text-lg sm:text-2xl font-semibold">
              {formatNumber(prediction?.current_hashrate_ghs, 2)} GH/s
            </p>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {formatNumber((prediction?.current_hashrate_ghs || 0) / 1000, 4)} TH/s
            </p>
          </div>
        </div>

        {/* Probability Bars */}
        <div className="space-y-3 sm:space-y-4">
          <h4 className="text-xs sm:text-sm font-medium">Probability of Beating Current Best</h4>

          <div className="space-y-2 sm:space-y-3">
            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-1">
                <span>Within 1 Hour</span>
                <span className="font-medium">
                  {formatProbability(prob1h)}%
                </span>
              </div>
              <Progress
                value={prob1h}
                className="h-2"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-1">
                <span>Within 24 Hours</span>
                <span className="font-medium">{formatProbability(prob24h)}%</span>
              </div>
              <Progress value={prob24h} className="h-2" />
            </div>

            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-1">
                <span>Within 7 Days</span>
                <span className="font-medium">{formatProbability(prob7d)}%</span>
              </div>
              <Progress value={prob7d} className="h-2" />
            </div>
          </div>
        </div>

        {/* Explanation */}
        <div className="p-2 sm:p-3 rounded-lg bg-muted/30 text-xs sm:text-sm text-muted-foreground">
          <p>
            <strong>How it works:</strong> Each hash has a 1/{prediction?.all_time_best_formatted || 'D'} chance
            of beating your current best. At {formatNumber(prediction?.current_hashrate_ghs, 0)} GH/s,
            you make ~{formatNumber((prediction?.current_hashrate_ghs || 0) * 1e9 * 3600, 0)} attempts per hour.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

// Energy Analysis Card
function EnergyAnalysisCard({ energy }) {
  const devices = energy?.devices || []

  // Prepare pie chart data
  const pieData = devices.map((d, i) => ({
    name: d.device_name || 'Unknown',
    value: d.power_watts || 0,
    fill: i === 0 ? 'hsl(var(--primary))' : i === 1 ? 'hsl(var(--chart-2))' : `hsl(${220 + i * 40}, 70%, 50%)`
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
          Energy Consumption
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">Power usage breakdown by device</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 sm:space-y-4">
        <div className="flex items-center justify-between p-3 sm:p-4 rounded-lg bg-muted/50">
          <div>
            <p className="text-xs sm:text-sm text-muted-foreground">Total Power Draw</p>
            <p className="text-xl sm:text-3xl font-bold">{formatNumber(energy?.current_power_watts, 1)}W</p>
          </div>
          <Battery className="h-8 w-8 sm:h-10 sm:w-10 text-yellow-500/30" />
        </div>

        {devices.length > 0 && (
          <div className="h-40 sm:h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
                          <div className="text-xs text-muted-foreground mb-1">{payload[0]?.name}</div>
                          <div className="font-bold text-primary">{(payload[0]?.value || 0).toFixed(1)}W</div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="space-y-2">
          {devices.map((device, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: pieData[i]?.fill || 'gray' }}
                />
                <span>{device.device_name || 'Unknown'}</span>
                <Badge variant="outline" className="text-xs">{device.device_type || 'N/A'}</Badge>
              </div>
              <span className="font-medium">{formatNumber(device.power_watts, 1)}W</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Cost Analysis Card
function CostAnalysisCard({ cost }) {
  const profitability = cost?.profitability || {}
  const energyCosts = cost?.energy_costs || {}
  const revenue = cost?.mining_revenue || {}

  const isProfit = profitability.is_profitable

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <DollarSign className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
          Cost Analysis
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">Energy costs vs mining revenue</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 sm:space-y-4">
        {/* Daily Summary */}
        <div className={`p-3 sm:p-4 rounded-lg ${isProfit ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">Daily Net</p>
              <p className={`text-lg sm:text-2xl font-bold ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrency(profitability.daily_profit_usd, 4)}
              </p>
            </div>
            <Badge variant={isProfit ? 'default' : 'destructive'} className="text-xs">
              {isProfit ? 'Profitable' : 'Loss'}
            </Badge>
          </div>
        </div>

        {/* Breakdown */}
        <div className="grid gap-3 sm:gap-4 grid-cols-2">
          <div className="p-2 sm:p-3 rounded-lg border">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Daily Energy Cost</p>
            <p className="text-base sm:text-lg font-semibold text-red-400">
              -{formatCurrency(energyCosts.daily_cost_usd)}
            </p>
          </div>
          <div className="p-2 sm:p-3 rounded-lg border">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Daily Revenue</p>
            <p className="text-base sm:text-lg font-semibold text-green-400">
              +{formatCurrency(revenue.daily_revenue_usd, 4)}
            </p>
          </div>
        </div>

        {/* Monthly Projections */}
        <div className="space-y-1.5 sm:space-y-2 pt-2 border-t">
          <div className="flex justify-between text-xs sm:text-sm">
            <span className="text-muted-foreground">Monthly Energy Cost</span>
            <span>{formatCurrency(energyCosts.monthly_cost_usd)}</span>
          </div>
          <div className="flex justify-between text-xs sm:text-sm">
            <span className="text-muted-foreground">Monthly Revenue</span>
            <span>{formatCurrency(revenue.monthly_revenue_usd, 4)}</span>
          </div>
          <div className="flex justify-between text-xs sm:text-sm font-medium pt-2 border-t">
            <span>Monthly Profit</span>
            <span className={(profitability.monthly_profit_usd || 0) >= 0 ? 'text-green-500' : 'text-red-500'}>
              {formatCurrency(profitability.monthly_profit_usd || 0, 4)}
            </span>
          </div>
        </div>

        {/* Break-even */}
        {profitability.break_even_btc_price && (
          <div className="p-2 sm:p-3 rounded-lg bg-muted/50 text-center">
            <p className="text-[10px] sm:text-xs text-muted-foreground">Break-even BTC Price</p>
            <p className="text-base sm:text-lg font-semibold">{formatCurrency(profitability.break_even_btc_price)}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Device Comparison Table
function DeviceComparisonTable({ devices }) {
  if (!devices || devices.length === 0) {
    return (
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Cpu className="h-4 w-4 sm:h-5 sm:w-5" />
            Device Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8 text-sm">No device data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Cpu className="h-4 w-4 sm:h-5 sm:w-5" />
          Device Comparison
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">Performance metrics across all mining devices</CardDescription>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        <div className="overflow-x-auto -mx-2 sm:mx-0">
          <Table className="min-w-[700px]">
            <TableHeader>
              <TableRow>
                <TableHead>Device</TableHead>
                <TableHead className="hidden sm:table-cell">Type</TableHead>
                <TableHead className="text-right">Hashrate</TableHead>
                <TableHead className="text-right">Power</TableHead>
                <TableHead className="text-right hidden sm:table-cell">Temp</TableHead>
                <TableHead className="text-right">Efficiency</TableHead>
                <TableHead className="text-right hidden md:table-cell">Best Diff</TableHead>
                <TableHead className="text-right hidden md:table-cell">Uptime</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.map((device, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">
                    <div>
                      {device.device_name || 'Unknown'}
                      <span className="block sm:hidden text-xs text-muted-foreground">
                        {device.device_type || 'N/A'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <Badge variant="outline" className="text-xs">{device.device_type || 'N/A'}</Badge>
                  </TableCell>
                  <TableCell className="text-right text-xs sm:text-sm">{formatNumber(device.hashrate_ghs, 2)} GH/s</TableCell>
                  <TableCell className="text-right text-xs sm:text-sm">{formatNumber(device.power_watts, 1)}W</TableCell>
                  <TableCell className="text-right hidden sm:table-cell">{formatNumber(device.temperature_c, 1)}°C</TableCell>
                  <TableCell className="text-right text-xs sm:text-sm">{formatNumber(device.efficiency_j_per_th, 2)} J/TH</TableCell>
                  <TableCell className="text-right font-mono text-xs hidden md:table-cell">{device.best_difficulty_formatted || '0'}</TableCell>
                  <TableCell className="text-right hidden md:table-cell">{formatNumber(device.uptime_hours, 1)}h</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}

// Historical Best Shares Chart
function BestSharesHistoryChart({ dailyBests }) {
  if (!dailyBests || dailyBests.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Best Shares History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">No historical data available</p>
        </CardContent>
      </Card>
    )
  }

  // Format data for chart
  const chartData = dailyBests.map(item => ({
    date: item.date,
    dateFormatted: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    bestEver: item.best_difficulty || 0,           // All-time best difficulty
    bestSession: item.best_session_difficulty || 0, // Session best difficulty
  }))

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5" />
          <span className="truncate">Best Shares History (Last 30 Days)</span>
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">
          Daily best shares: All-Time Best vs Session Best
        </CardDescription>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        {/* Legend */}
        <div className="flex flex-wrap gap-4 mb-4 text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-primary"></div>
            <span className="text-muted-foreground">Best Ever (All-Time)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-orange-500"></div>
            <span className="text-muted-foreground">Best Session</span>
          </div>
        </div>
        <div className="h-64 sm:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="bestEverGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bestSessionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(24, 95%, 53%)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="hsl(24, 95%, 53%)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
              <XAxis
                dataKey="dateFormatted"
                className="text-xs"
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={formatDifficulty}
                className="text-xs"
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
                        <div className="text-xs text-muted-foreground mb-2">
                          {new Date(payload[0]?.payload?.date).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Best Ever</span>
                            <span className="font-bold text-primary">{formatDifficulty(payload[0]?.payload?.bestEver)}</span>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Best Session</span>
                            <span className="font-bold text-orange-500">{formatDifficulty(payload[0]?.payload?.bestSession)}</span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              {/* Session best area */}
              <Area
                type="monotone"
                dataKey="bestSession"
                stroke="hsl(24, 95%, 53%)"
                fill="url(#bestSessionGradient)"
                strokeWidth={2}
                name="Best Session"
              />
              {/* All-time best area (on top) */}
              <Area
                type="monotone"
                dataKey="bestEver"
                stroke="hsl(var(--primary))"
                fill="url(#bestEverGradient)"
                strokeWidth={2}
                name="Best Ever"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Top 10 Best Shares Table
function TopSharesTable({ topShares }) {
  if (!topShares || topShares.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Award className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
            Top 10 Best Shares
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">All-time highest difficulty shares</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-6 sm:py-8 text-sm">No best shares recorded yet</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Award className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
          Top 10 Best Shares
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">All-time highest difficulty shares</CardDescription>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        <div className="overflow-x-auto -mx-2 sm:mx-0">
        <Table className="min-w-[400px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-10 sm:w-12">#</TableHead>
              <TableHead>Difficulty</TableHead>
              <TableHead className="hidden sm:table-cell">Device</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {topShares.map((share, i) => (
              <TableRow key={i}>
                <TableCell className="text-sm">
                  {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`}
                </TableCell>
                <TableCell className="font-mono font-bold text-xs sm:text-sm">
                  <div>
                    {share.difficulty_formatted}
                    <span className="block sm:hidden text-[10px] text-muted-foreground font-normal">
                      {share.device_name || 'Unknown'}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <div className="flex items-center gap-2">
                    {share.device_name}
                    <Badge variant="outline" className="text-xs">{share.device_type}</Badge>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground text-xs sm:text-sm">
                  {new Date(share.timestamp).toLocaleDateString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
      </CardContent>
    </Card>
  )
}

// Power Trend Chart
function PowerTrendChart({ powerTrend }) {
  if (!powerTrend || powerTrend.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Flame className="h-4 w-4 sm:h-5 sm:w-5 text-orange-500" />
            Power & Temperature Trend
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">24-hour power consumption and temperature</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-6 sm:py-8 text-sm">No power data available</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = powerTrend.map(item => ({
    time: item.hour,
    power: item.power_watts || 0,
    temp: item.temperature_c || 0,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Flame className="h-4 w-4 sm:h-5 sm:w-5 text-orange-500" />
          Power & Temperature Trend
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">24-hour power consumption and temperature</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
              <XAxis
                dataKey="time"
                tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                className="text-xs"
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="power"
                orientation="left"
                className="text-xs"
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}W`}
              />
              <YAxis
                yAxisId="temp"
                orientation="right"
                className="text-xs"
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}°`}
              />
              <Tooltip
                content={({ active, payload, label }) => {
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
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Power</span>
                            <span className="font-bold text-chart-1">{payload[0]?.value?.toFixed(1) || 0}W</span>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Temperature</span>
                            <span className="font-bold text-chart-3">{payload[1]?.value?.toFixed(1) || 0}°C</span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Line
                yAxisId="power"
                type="monotone"
                dataKey="power"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                dot={false}
                name="Power (W)"
              />
              <Line
                yAxisId="temp"
                type="monotone"
                dataKey="temp"
                stroke="hsl(var(--chart-3))"
                strokeWidth={2}
                dot={false}
                name="Temp (°C)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Efficiency Comparison Bar Chart
function EfficiencyComparisonChart({ devices }) {
  if (!devices || devices.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5" />
            Efficiency Comparison
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">Power efficiency (J/TH) - lower is better</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-6 sm:py-8 text-sm">No device data available</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = devices.map(d => ({
    name: d.device_name.length > 12 ? d.device_name.substring(0, 12) + '...' : d.device_name,
    efficiency: d.efficiency_j_per_th || 0,
    hashrate: d.hashrate_ghs || 0,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5" />
          Efficiency Comparison
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">Power efficiency (J/TH) - lower is better</CardDescription>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        <div className="h-56 sm:h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
              <XAxis
                dataKey="name"
                className="text-xs"
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                className="text-xs"
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v} J/TH`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
                        <div className="text-xs text-muted-foreground mb-2">
                          {payload[0]?.payload?.name}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Efficiency</span>
                            <span className="font-bold text-primary">{payload[0]?.value?.toFixed(2) || 0} J/TH</span>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">Hashrate</span>
                            <span className="font-bold text-chart-2">{payload[0]?.payload?.hashrate?.toFixed(2) || 0} GH/s</span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Bar dataKey="efficiency" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Solo Mining Statistics Component
function SoloMiningStats({ totalHashrateGhs, bestDifficulty, bestDifficultyFormatted }) {
  // Bitcoin network constants
  const NETWORK_HASHRATE_EH = 750 // Current approximate network hashrate
  const BLOCK_REWARD_BTC = 3.125 // Post-2024 halving
  const BLOCKS_PER_DAY = 144
  const BTC_PRICE_USD = 100000 // Approximate

  // Calculate probabilities
  const totalHashrateEH = totalHashrateGhs / 1e9
  const probabilityPerBlock = totalHashrateEH / NETWORK_HASHRATE_EH
  const probabilityPerDay = 1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY)
  const probabilityPerYear = 1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY * 365)

  // Expected time to find a block
  const expectedDaysToBlock = probabilityPerBlock > 0 ? 1 / (probabilityPerBlock * BLOCKS_PER_DAY) : Infinity
  const expectedYearsToBlock = expectedDaysToBlock / 365

  // Format large numbers
  const formatLargeTime = (years) => {
    if (years === Infinity || !isFinite(years)) return 'Extremely unlikely'
    if (years >= 1000000) return `${(years / 1000000).toFixed(1)}M years`
    if (years >= 1000) return `${(years / 1000).toFixed(1)}K years`
    if (years >= 1) return `${years.toFixed(0)} years`
    const days = years * 365
    if (days >= 1) return `${days.toFixed(0)} days`
    return `${(days * 24).toFixed(0)} hours`
  }

  const formatSmallProbability = (prob) => {
    if (prob === 0 || !isFinite(prob)) return '~0%'
    if (prob >= 0.01) return `${(prob * 100).toFixed(2)}%`
    if (prob >= 0.0001) return `${(prob * 100).toFixed(4)}%`
    // Scientific notation for very small numbers
    const exponent = Math.floor(Math.log10(prob))
    const mantissa = prob / Math.pow(10, exponent)
    return `${mantissa.toFixed(1)}×10^${exponent} %`
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Hero Stats */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-3">
        <Card className="bg-gradient-to-br from-orange-500/10 to-yellow-500/10 border-orange-500/20">
          <CardHeader className="pb-1 sm:pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium flex items-center gap-2">
              <Trophy className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-orange-500" />
              Your Chance Per Block
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold text-orange-500">
              {formatSmallProbability(probabilityPerBlock)}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              1 in {probabilityPerBlock > 0 ? formatNumber(Math.round(1 / probabilityPerBlock)) : '∞'} blocks
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardHeader className="pb-1 sm:pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium flex items-center gap-2">
              <Timer className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-blue-500" />
              Expected Wait Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold text-blue-500">
              {formatLargeTime(expectedYearsToBlock)}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              Statistical average to find a block
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20">
          <CardHeader className="pb-1 sm:pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium flex items-center gap-2">
              <Award className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-500" />
              Block Reward
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold text-green-500">
              {BLOCK_REWARD_BTC} BTC
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              ≈ ${formatNumber(BLOCK_REWARD_BTC * BTC_PRICE_USD)} if you win
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Your Mining Power vs Network */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Hash className="h-4 w-4 sm:h-5 sm:w-5" />
            Your Mining Power vs The Network
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            Visual comparison of your contribution to Bitcoin's security
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 sm:space-y-6">
          <div className="space-y-3 sm:space-y-4">
            <div>
              <div className="flex flex-col sm:flex-row sm:justify-between text-xs sm:text-sm mb-2 gap-1">
                <span>Your Hashrate</span>
                <span className="font-mono">{formatNumber(totalHashrateGhs, 2)} GH/s ({formatNumber(totalHashrateGhs / 1000, 4)} TH/s)</span>
              </div>
              <Progress value={0.001} className="h-2 sm:h-3" />
            </div>
            <div>
              <div className="flex flex-col sm:flex-row sm:justify-between text-xs sm:text-sm mb-2 gap-1">
                <span>Network Hashrate</span>
                <span className="font-mono">{NETWORK_HASHRATE_EH} EH/s ({formatNumber(NETWORK_HASHRATE_EH * 1000)} PH/s)</span>
              </div>
              <Progress value={100} className="h-2 sm:h-3" />
            </div>
          </div>

          <div className="p-3 sm:p-4 rounded-lg bg-muted/50 text-center">
            <p className="text-xs sm:text-sm text-muted-foreground">
              You represent approximately
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-primary my-1 sm:my-2">
              {formatSmallProbability(probabilityPerBlock)}
            </p>
            <p className="text-xs sm:text-sm text-muted-foreground">
              of the entire Bitcoin network
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Probability Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5" />
            Block Finding Probability Over Time
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            Your chances of finding a Bitcoin block
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 sm:space-y-4">
            <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
              <div className="p-2 sm:p-4 rounded-lg border text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Per Block (10 min)</p>
                <p className="text-sm sm:text-lg font-bold">{formatSmallProbability(probabilityPerBlock)}</p>
              </div>
              <div className="p-2 sm:p-4 rounded-lg border text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Per Day</p>
                <p className="text-sm sm:text-lg font-bold">{formatSmallProbability(probabilityPerDay)}</p>
              </div>
              <div className="p-2 sm:p-4 rounded-lg border text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Per Month</p>
                <p className="text-sm sm:text-lg font-bold">{formatSmallProbability(1 - Math.pow(1 - probabilityPerBlock, BLOCKS_PER_DAY * 30))}</p>
              </div>
              <div className="p-2 sm:p-4 rounded-lg border text-center">
                <p className="text-[10px] sm:text-xs text-muted-foreground mb-1">Per Year</p>
                <p className="text-sm sm:text-lg font-bold">{formatSmallProbability(probabilityPerYear)}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Best Share Achievement */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Trophy className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
            Your Best Achievement
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            Highest difficulty share found by your miners
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-3 sm:p-4 rounded-lg bg-gradient-to-r from-yellow-500/10 to-orange-500/10">
            <div>
              <p className="text-xs sm:text-sm text-muted-foreground">All-Time Best Difficulty</p>
              <p className="text-2xl sm:text-4xl font-bold text-yellow-500">{bestDifficultyFormatted || '0'}</p>
            </div>
            <Trophy className="h-12 w-12 sm:h-16 sm:w-16 text-yellow-500/30" />
          </div>

          <div className="mt-3 sm:mt-4 p-3 sm:p-4 rounded-lg bg-muted/30">
            <p className="text-xs sm:text-sm text-muted-foreground">
              <strong>What does this mean?</strong> Your best share shows the highest difficulty
              proof-of-work you've found. While you need network-level difficulty (~92T currently)
              to find a block, every high-difficulty share proves your hardware is working correctly.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Why Solo Mine Card */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            Why Solo Mine?
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-2">
            <div className="space-y-2 sm:space-y-3">
              <div className="flex items-start gap-2 sm:gap-3">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-green-500 text-sm sm:text-base">🎲</span>
                </div>
                <div>
                  <p className="font-medium text-sm sm:text-base">The Lottery</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Any hash could be THE hash. Win {BLOCK_REWARD_BTC} BTC if you find a block.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2 sm:gap-3">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-blue-500 text-sm sm:text-base">🌐</span>
                </div>
                <div>
                  <p className="font-medium text-sm sm:text-base">Decentralization</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Your hashpower helps secure and decentralize Bitcoin.
                  </p>
                </div>
              </div>
            </div>
            <div className="space-y-2 sm:space-y-3">
              <div className="flex items-start gap-2 sm:gap-3">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-purple-500 text-sm sm:text-base">📚</span>
                </div>
                <div>
                  <p className="font-medium text-sm sm:text-base">Learn Bitcoin</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Hands-on experience with proof-of-work mining.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2 sm:gap-3">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-orange-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-orange-500 text-sm sm:text-base">🔥</span>
                </div>
                <div>
                  <p className="font-medium text-sm sm:text-base">Space Heater</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Turn electricity into heat + lottery tickets!
                  </p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 300000) // Refresh every 5 minutes
    return () => clearInterval(interval)
  }, [])

  const fetchAnalytics = async () => {
    try {
      const response = await api.get('/api/analytics/detailed/', {
        params: { hours: 24, days: 30 }
      })
      setAnalytics(response.data)
      setError(null)
    } catch (err) {
      console.error('Error fetching analytics:', err)
      setError('Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <AnalyticsSkeleton />
  }

  if (error || !analytics) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-4">
          <AlertTriangle className="h-12 w-12 mx-auto text-destructive" />
          <p className="text-muted-foreground">{error || 'Unable to load analytics'}</p>
        </div>
      </div>
    )
  }

  const prediction = analytics.best_difficulty_prediction || {}
  const energy = analytics.energy_analysis || {}
  const cost = analytics.cost_analysis || {}
  const devices = analytics.device_comparison?.devices || []
  const topShares = analytics.historical_best_shares?.top_10 || []
  const dailyBests = prediction.daily_best_shares || []

  // Calculate total hashrate for solo mining stats
  const totalHashrateGhs = prediction.current_hashrate_ghs || 0

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">Analytics Dashboard</h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Advanced insights, predictions, and cross-data analysis
        </p>
      </div>

      <Tabs defaultValue="predictions" className="space-y-4 sm:space-y-6">
        <TabsList className="w-full overflow-x-auto lg:w-[600px]">
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
          <TabsTrigger value="solo">Solo</TabsTrigger>
          <TabsTrigger value="energy">Energy</TabsTrigger>
          <TabsTrigger value="costs">Costs</TabsTrigger>
          <TabsTrigger value="devices">Devices</TabsTrigger>
        </TabsList>

        {/* PREDICTIONS TAB */}
        <TabsContent value="predictions" className="space-y-4 sm:space-y-6">
          <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
            <PredictionCard prediction={prediction} />
            <TopSharesTable topShares={topShares} />
          </div>
          <BestSharesHistoryChart dailyBests={dailyBests} />
        </TabsContent>

        {/* SOLO MINING TAB */}
        <TabsContent value="solo" className="space-y-4 sm:space-y-6">
          <SoloMiningStats
            totalHashrateGhs={totalHashrateGhs}
            bestDifficulty={prediction.all_time_best_difficulty}
            bestDifficultyFormatted={prediction.all_time_best_formatted}
          />
        </TabsContent>

        {/* ENERGY TAB */}
        <TabsContent value="energy" className="space-y-4 sm:space-y-6">
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <EnergyAnalysisCard energy={energy} />
            <PowerTrendChart powerTrend={energy.power_trend} />
          </div>
          <EfficiencyComparisonChart devices={devices} />
        </TabsContent>

        {/* COSTS TAB */}
        <TabsContent value="costs" className="space-y-4 sm:space-y-6">
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            <CostAnalysisCard cost={cost} />

            {/* Energy Consumption Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Energy Consumption
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Daily</span>
                    <span className="font-medium">{formatNumber(cost.energy_consumption?.daily_kwh, 2)} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Monthly</span>
                    <span className="font-medium">{formatNumber(cost.energy_consumption?.monthly_kwh, 2)} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Yearly</span>
                    <span className="font-medium">{formatNumber(cost.energy_consumption?.yearly_kwh, 2)} kWh</span>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Electricity Rate</p>
                    <p className="text-lg font-semibold">${cost.energy_costs?.kwh_price || '0.00'}/kWh</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Mining Revenue */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Mining Output
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Daily BTC</span>
                    <span className="font-mono text-sm">{cost.mining_revenue?.daily_btc || '0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Monthly BTC</span>
                    <span className="font-mono text-sm">{cost.mining_revenue?.monthly_btc || '0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Yearly BTC</span>
                    <span className="font-mono text-sm">{cost.mining_revenue?.yearly_btc || '0'}</span>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Sats/kWh</span>
                    <span className="font-medium">{formatNumber(cost.efficiency_metrics?.sats_per_kwh, 4)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Assumptions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Calculation Assumptions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span>BTC Price: {formatCurrency(cost.mining_revenue?.btc_price || 0)}</span>
                <span>•</span>
                <span>Network Hashrate: {cost.assumptions?.network_hashrate_ehs || 0} EH/s</span>
                <span>•</span>
                <span>Block Reward: {cost.assumptions?.btc_per_block || 0} BTC</span>
                <span>•</span>
                <span>Blocks/Day: {cost.assumptions?.blocks_per_day || 0}</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* DEVICES TAB */}
        <TabsContent value="devices" className="space-y-4 sm:space-y-6">
          <DeviceComparisonTable devices={devices} />
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <EfficiencyComparisonChart devices={devices} />
            <EnergyAnalysisCard energy={energy} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
