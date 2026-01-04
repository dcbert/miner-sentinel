import { CartesianGrid, Legend, Line, LineChart as RechartsLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function HardwareHealthChart({ data, formatAxisPower }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <RechartsLineChart data={data}>
      <defs>
        <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3}/>
          <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0.05}/>
        </linearGradient>
        <linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="hsl(var(--chart-3))" stopOpacity={0.3}/>
          <stop offset="95%" stopColor="hsl(var(--chart-3))" stopOpacity={0.05}/>
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
      <XAxis
        dataKey="hour"
        tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { hour: '2-digit' })}
        className="text-xs"
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        yAxisId="left"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={(value) => `${value}°C`}
      />
      <YAxis
        yAxisId="right"
        orientation="right"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={formatAxisPower}
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
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Temperature</span>
                    <span className="font-bold text-destructive">{payload[0]?.value?.toFixed(1) || 0}°C</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[0.70rem] uppercase text-muted-foreground">Power</span>
                    <span className="font-bold text-chart-3">{payload[1]?.value?.toFixed(1) || 0}W</span>
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
              <div className="w-3 h-3 rounded-full bg-destructive"></div>
              <span className="text-xs text-muted-foreground">Temperature (°C)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-3"></div>
              <span className="text-xs text-muted-foreground">Power (W)</span>
            </div>
          </div>
        )}
      />
      <Line
        yAxisId="left"
        type="monotone"
        dataKey="temperature_c"
        stroke="hsl(var(--destructive))"
        strokeWidth={3}
        dot={{ fill: "hsl(var(--destructive))", r: 2 }}
        activeDot={{ r: 4, fill: "hsl(var(--destructive))" }}
      />
      <Line
        yAxisId="right"
        type="monotone"
        dataKey="power_watts"
        stroke="hsl(var(--chart-3))"
        strokeWidth={2}
        dot={{ fill: "hsl(var(--chart-3))", r: 2 }}
        activeDot={{ r: 4, fill: "hsl(var(--chart-3))" }}
        strokeDasharray="5 5"
      />
    </RechartsLineChart>
  </ResponsiveContainer>
  )
}