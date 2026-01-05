import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function BestSharesChart({ data, formatAxisDifficulty, formatAxisHashrate, formatHashrate, formatNumber }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <defs>
          <linearGradient id="bitaxeBestShareGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(var(--chart-4))" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="hsl(var(--chart-4))" stopOpacity={0.1}/>
          </linearGradient>
          <linearGradient id="avalonBestShareGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0.1}/>
          </linearGradient>
          <linearGradient id="hashrateBgGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.2}/>
            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.02}/>
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
        yAxisId="shares"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={formatAxisDifficulty}
        domain={['dataMin', 'dataMax']}
      />
      <YAxis
        yAxisId="hashrate"
        orientation="right"
        className="text-xs"
        axisLine={false}
        tickLine={false}
        tickFormatter={formatAxisHashrate}
        domain={['dataMin', 'dataMax']}
      />
      <Tooltip
        content={({ active, payload, label }) => {
          if (active && payload && payload.length) {
            const hashrate = payload.find(p => p.dataKey === 'hashrate_ghs')?.value;
            const bitaxeBestShare = payload.find(p => p.dataKey === 'bitaxe_best_share')?.value;
            const avalonBestShare = payload.find(p => p.dataKey === 'avalon_best_share')?.value;
            const bitaxeDeviceName = payload.find(p => p.payload?.bitaxe_device_name)?.payload?.bitaxe_device_name;
            const avalonDeviceName = payload.find(p => p.payload?.avalon_device_name)?.payload?.avalon_device_name;

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
                <div className="space-y-2">
                  {bitaxeBestShare && bitaxeBestShare > 0 && (
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">Bitaxe Best Share</span>
                      <span className="font-bold text-chart-4 text-lg">
                        {bitaxeBestShare >= 1000000 ?
                          `${(bitaxeBestShare / 1000000).toFixed(1)}M` :
                          formatNumber(bitaxeBestShare, 0)
                        }
                      </span>
                      {bitaxeDeviceName && (
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[0.65rem] text-muted-foreground">
                            Bitaxe • {bitaxeDeviceName}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  {avalonBestShare && avalonBestShare > 0 && (
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">Avalon Best Share</span>
                      <span className="font-bold text-chart-2 text-lg">
                        {avalonBestShare >= 1000000 ?
                          `${(avalonBestShare / 1000000).toFixed(1)}M` :
                          formatNumber(avalonBestShare, 0)
                        }
                      </span>
                      {avalonDeviceName && (
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[0.65rem] text-muted-foreground">
                            Avalon • {avalonDeviceName}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  {hashrate && hashrate > 0 && (
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">Mining Hashrate</span>
                      <span className="font-bold text-primary">{formatHashrate(hashrate)}</span>
                    </div>
                  )}
                  {(!bitaxeBestShare || bitaxeBestShare === 0) && (!avalonBestShare || avalonBestShare === 0) && (
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">Status</span>
                      <span className="font-medium text-muted-foreground">No best shares found</span>
                    </div>
                  )}
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
              <div className="w-3 h-3 rounded-full bg-chart-4"></div>
              <span className="text-xs text-muted-foreground">Bitaxe Best Shares</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-2"></div>
              <span className="text-xs text-muted-foreground">Avalon Best Shares</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary/50"></div>
              <span className="text-xs text-muted-foreground">Mining Hashrate</span>
            </div>
          </div>
        )}
      />
      <Area
        yAxisId="hashrate"
        type="monotone"
        dataKey="hashrate_ghs"
        stroke="hsl(var(--primary))"
        fill="url(#hashrateBgGradient)"
        strokeWidth={1}
        dot={false}
      />
      <Area
        yAxisId="shares"
        type="stepAfter"
        dataKey="bitaxe_best_share"
        stroke="hsl(var(--chart-4))"
        fill="url(#bitaxeBestShareGradient)"
        strokeWidth={3}
        connectNulls={false}
        dot={false}
        activeDot={{ r: 6, fill: "hsl(var(--chart-4))", strokeWidth: 2, stroke: "hsl(var(--background))" }}
      />
      <Area
        yAxisId="shares"
        type="stepAfter"
        dataKey="avalon_best_share"
        stroke="hsl(var(--chart-2))"
        fill="url(#avalonBestShareGradient)"
        strokeWidth={2}
        connectNulls={false}
        dot={false}
        activeDot={{ r: 5, fill: "hsl(var(--chart-2))", strokeWidth: 2, stroke: "hsl(var(--background))" }}
      />
    </AreaChart>
  </ResponsiveContainer>
  )
}