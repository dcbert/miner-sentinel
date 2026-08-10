import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getChartTimeAxisConfig } from '@/lib/timeRange'

export default function MiningPerformanceChart({
  data,
  rangeHours = 24,
  formatAxisHashrate,
  formatAxisShares,
  formatHashrate,
  formatShares,
}) {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">No data available</div>
  }

  const timeAxis = getChartTimeAxisConfig(rangeHours)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
      <defs>
        <linearGradient id="hashrateGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.8}/>
          <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.1}/>
        </linearGradient>
        <linearGradient id="sharesGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.6}/>
          <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0.05}/>
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
      <XAxis
        dataKey="hour"
        tickFormatter={timeAxis.tick}
        minTickGap={timeAxis.minTickGap}
        interval={timeAxis.interval}
        className="text-xs"
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        yAxisId="hashrate"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={formatAxisHashrate}
        domain={['dataMin', 'dataMax']}
      />
      <YAxis
        yAxisId="shares"
        orientation="right"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={formatAxisShares}
        domain={['dataMin', 'dataMax']}
      />
      <Tooltip
        content={({ active, payload, label }) => {
          if (active && payload && payload.length) {
            return (
              <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
                <div className="text-xs text-muted-foreground mb-2">
                  {timeAxis.tooltip(label)}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col">
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Hashrate</span>
                    <span className="font-bold text-primary">{formatHashrate(payload[0]?.value || 0)}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Shares</span>
                    <span className="font-bold text-chart-2">{formatShares(payload[1]?.value || 0)}</span>
                  </div>
                </div>
              </div>
            )
          }
          return null
        }}
      />
      <Legend
        content={() => (
          <div className="flex justify-center gap-4 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <span className="text-xs text-muted-foreground">Hashrate</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-2"></div>
              <span className="text-xs text-muted-foreground">Shares</span>
            </div>
          </div>
        )}
      />
      <Area
        yAxisId="hashrate"
        type="monotone"
        dataKey="hashrate_ghs"
        stroke="var(--primary)"
        fill="url(#hashrateGradient)"
        strokeWidth={2}
        dot={false}
      />
      <Area
        yAxisId="shares"
        type="monotone"
        dataKey="shares"
        stroke="var(--chart-2)"
        fill="url(#sharesGradient)"
        strokeWidth={1.5}
        dot={false}
      />
    </AreaChart>
  </ResponsiveContainer>
  )
}
