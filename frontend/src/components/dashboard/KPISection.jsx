import {
    Award,
    Cpu,
    Network,
    Power,
    Shield,
    TrendingUp,
    Zap
} from 'lucide-react'
import KPICard from './KPICard'
import { formatHashrate, formatNumber, formatShares } from './formatters'
import { getBestShare, getBestShareTimestamp, getBestShareValue } from './shareUtils'

export default function KPISection({ analytics, mining, hardware, pool }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KPICard
        title="Total Hashrate"
        value={formatHashrate(mining.current.total_hashrate_ghs)}
        subtitle={`${formatNumber(mining.current.total_hashrate_ghs)} GH/s raw`}
        icon={Cpu}
        trend={{
          icon: TrendingUp,
          color: "text-green-500",
          text: `${formatNumber(mining.period.hashrate_stability, 1)}% stable`
        }}
      />

      <KPICard
        title="Share Performance"
        value={`${formatNumber(mining.current.acceptance_rate, 1)}%`}
        subtitle={`${formatShares(mining.current.total_shares_accepted)} accepted`}
        icon={Network}
        progress={mining.current.acceptance_rate}
      />

      <KPICard
        title="Best Share"
        value={getBestShare(mining, pool)}
        subtitle={getBestShareValue(mining, pool) ? 'Difficulty target' : 'Searching for shares...'}
        icon={Award}
        trend={{
          icon: Shield,
          color: "text-blue-500",
          text: `Last found: ${getBestShareTimestamp(mining, pool)}`
        }}
        className={getBestShareValue(mining, pool) ? '' : 'text-muted-foreground'}
      />

      <KPICard
        title="Mining Efficiency"
        value={`${formatNumber(hardware.health.power_efficiency_gh_per_watt, 2)} GH/W`}
        subtitle={`${formatNumber(hardware.current.total_power_watts, 0)}W total power`}
        icon={Zap}
        trend={{
          icon: Power,
          color: "text-yellow-500",
          text: `${formatNumber((hardware.current.total_power_watts / 1000) * 24, 1)} kWh/day`
        }}
      />
    </div>
  )
}