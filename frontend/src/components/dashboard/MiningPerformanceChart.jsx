import { Area, AreaChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getChartTimeAxisConfig } from '@/lib/timeRange'

export default function MiningPerformanceChart({
  data,
  rangeHours = 24,
  formatAxisHashrate,
  formatAxisShares,
  formatHashrate,
  formatShares,
  incidents = [],
}) {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">No data available</div>
  }

  const timeAxis = getChartTimeAxisConfig(rangeHours)

  // Map incident timestamps onto nearest chart x-key ("hour")
  const markerXs = []
  if (incidents?.length && data.length) {
    const points = data.map((d) => ({
      key: d.hour,
      t: new Date(d.hour).getTime(),
    })).filter((p) => !Number.isNaN(p.t))
    for (const ev of incidents) {
      const et = new Date(ev.created_at).getTime()
      if (Number.isNaN(et) || !points.length) continue
      let best = points[0]
      let bestDist = Math.abs(points[0].t - et)
      for (const p of points) {
        const dist = Math.abs(p.t - et)
        if (dist < bestDist) {
          best = p
          bestDist = dist
        }
      }
      if (!markerXs.find((m) => m.x === best.key && m.id === ev.id)) {
        markerXs.push({
          x: best.key,
          id: ev.id,
          label: ev.event_type,
          severity: ev.severity,
        })
      }
    }
  }

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
            const near = markerXs.filter((m) => m.x === label)
            return (
              <div className="rounded-lg border bg-background/95 backdrop-blur p-3 shadow-lg">
                <div className="text-xs text-muted-foreground mb-2">
                  {timeAxis.tooltip(label)}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col">
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Hashrate (left)</span>
                    <span className="font-bold text-primary">{formatHashrate(payload[0]?.value || 0)}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Shares (right)</span>
                    <span className="font-bold text-chart-2">{formatShares(payload[1]?.value || 0)}</span>
                  </div>
                </div>
                {near.length > 0 && (
                  <div className="mt-2 border-t border-border/60 pt-2 text-[10px] text-amber-600">
                    {near.map((m) => m.label).join(', ')}
                  </div>
                )}
              </div>
            )
          }
          return null
        }}
      />
      <Legend
        content={() => (
          <div className="mt-2 flex justify-center gap-5">
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-primary" />
              <span className="text-[11px] text-muted-foreground">Hashrate (left)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-chart-2" />
              <span className="text-[11px] text-muted-foreground">Shares (right)</span>
            </div>
            {markerXs.length > 0 && (
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-0.5 bg-amber-500" />
                <span className="text-[11px] text-muted-foreground">Incidents</span>
              </div>
            )}
          </div>
        )}
      />
      {markerXs.map((m) => (
        <ReferenceLine
          key={m.id}
          x={m.x}
          yAxisId="hashrate"
          stroke="var(--chart-5, #f59e0b)"
          strokeDasharray="3 3"
          strokeOpacity={0.7}
        />
      ))}
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
