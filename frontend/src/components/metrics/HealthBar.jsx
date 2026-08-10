import { formatNumber } from '@/lib/formatters'
import { cn } from '@/lib/utils'

/**
 * Horizontal health / utilization bar with semantic thresholds.
 * @param {boolean} invert - when true, lower values are worse (e.g. stability %)
 */
export default function HealthBar({
  label,
  value = 0,
  max = 100,
  unit = '',
  thresholds = { warning: 60, danger: 70 },
  invert = false,
  icon: Icon,
  className,
  decimals = 1,
}) {
  const n = Number(value)
  const safe = Number.isFinite(n) ? n : 0
  const percentage = Math.min((safe / (max || 1)) * 100, 100)
  let status = 'normal'
  if (invert) {
    // higher is better: below danger → critical, below warning → warning
    if (safe < thresholds.danger) status = 'danger'
    else if (safe < thresholds.warning) status = 'warning'
  } else if (safe > thresholds.danger) {
    status = 'danger'
  } else if (safe > thresholds.warning) {
    status = 'warning'
  }

  const barColor = {
    normal: 'bg-status-online',
    warning: 'bg-status-warning',
    danger: 'bg-status-critical',
  }[status]

  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5">
          {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />}
          <span className="text-muted-foreground">{label}</span>
        </div>
        <span className="font-medium tabular-metrics">
          {formatNumber(safe, decimals)}
          {unit}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all', barColor)}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={safe}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={`${label}: ${formatNumber(safe, decimals)}${unit}`}
        />
      </div>
    </div>
  )
}
