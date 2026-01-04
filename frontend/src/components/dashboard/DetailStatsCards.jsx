import { Badge } from '@/components/ui/badge'
import StatsCard, { StatRow } from './StatsCard'

export function PoolStatsCard({ pool, formatHashrate, formatNumber }) {
  return (
    <StatsCard
      title="Pool Statistics"
      description="Current mining pool performance"
    >
      <StatRow
        label="Pool Hashrate"
        value={formatHashrate(pool.current.pool_hashrate_ghs)}
      />
      <StatRow
        label="Workers Active"
        value={pool.current.workers_active || 0}
      />
      <div className="flex justify-between items-center">
        <span className="text-sm text-muted-foreground">Stale Share Rate</span>
        <span className={`font-medium ${(pool.performance.stale_rate || 0) > 2 ? 'text-destructive' : 'text-green-500'}`}>
          {formatNumber(pool.performance.stale_rate || 0, 1)}%
        </span>
      </div>
      <StatRow
        label="Network Difficulty"
        value={pool.current.network_difficulty ? formatNumber(pool.current.network_difficulty / 1000000000000, 2) + 'T' : 'N/A'}
      />
    </StatsCard>
  )
}

export function HardwareStatsCard({ hardware, analytics, formatNumber }) {
  return (
    <StatsCard
      title="Hardware Status"
      description="Device health and performance"
    >
      <div className="flex justify-between items-center">
        <span className="text-sm text-muted-foreground">Average Temperature</span>
        <div className="flex items-center gap-2">
          <span className="font-medium">{formatNumber(hardware.current.avg_temperature_c, 1)}°C</span>
          <Badge variant={hardware.current.avg_temperature_c > 70 ? 'destructive' : 'secondary'}>
            {hardware.current.avg_temperature_c > 70 ? 'Hot' : 'OK'}
          </Badge>
        </div>
      </div>
      <StatRow
        label="Fan Speed"
        value={`${formatNumber(hardware.current.avg_fan_speed_rpm || 0)} RPM`}
      />
      <StatRow
        label="Uptime"
        value={`${formatNumber(hardware.health.uptime_percentage || 100, 1)}%`}
      />
      <StatRow
        label="Active Devices"
        value={analytics.overview.active_devices}
      />
    </StatsCard>
  )
}

export function PeriodStatsCard({ mining, periods, selectedPeriod, formatHashrate, formatShares, getBestShare, formatNumber }) {
  return (
    <StatsCard
      title="Period Summary"
      description={`Performance over ${periods[selectedPeriod].label.toLowerCase()}`}
    >
      <StatRow
        label="Avg Hashrate"
        value={formatHashrate(mining.period.avg_hashrate_ghs)}
      />
      <StatRow
        label="Total Shares"
        value={formatShares(mining.period.total_shares)}
      />
      <StatRow
        label="Best Share"
        value={getBestShare()}
      />
      <StatRow
        label="Efficiency"
        value={`${formatNumber(mining.efficiency.shares_per_hour || 0, 1)}/hr`}
      />
    </StatsCard>
  )
}