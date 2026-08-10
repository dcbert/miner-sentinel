import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { TrendingDown, TrendingUp } from 'lucide-react'

const TONE_ICON = {
  default: 'text-primary',
  success: 'text-status-online-fg',
  warning: 'text-status-warning-fg',
  danger: 'text-status-critical-fg',
  muted: 'text-muted-foreground',
}

/**
 * Unified KPI / metric card for ops dashboards.
 *
 * @param {'hero'|'compact'|'inline'} variant
 * @param {'icon-left'|'icon-top'|'stat-only'} layout
 */
export default function MetricCard({
  label,
  value,
  subtitle,
  trend,
  icon: Icon,
  tone = 'default',
  variant = 'compact',
  layout = 'icon-top',
  onClick,
  className,
  skeleton = false,
}) {
  if (skeleton) {
    return (
      <Card className={cn(className)}>
        <CardHeader className="space-y-0 pb-2">
          <Skeleton className="h-3 w-20" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-7 w-24" />
          <Skeleton className="mt-2 h-3 w-16" />
        </CardContent>
      </Card>
    )
  }

  const TrendIcon =
    trend?.direction === 'up'
      ? TrendingUp
      : trend?.direction === 'down'
        ? TrendingDown
        : null
  const trendColor =
    trend?.direction === 'up'
      ? 'text-status-online-fg'
      : trend?.direction === 'down'
        ? 'text-status-critical-fg'
        : 'text-muted-foreground'

  const interactive = typeof onClick === 'function'

  if (variant === 'hero' || layout === 'icon-left') {
    return (
      <div
        className={cn(
          'flex items-start gap-3 rounded-xl border bg-card p-3 sm:gap-4 sm:p-4',
          interactive && 'cursor-pointer transition-shadow hover:shadow-md',
          className,
        )}
        onClick={onClick}
        onKeyDown={
          interactive
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onClick()
                }
              }
            : undefined
        }
        role={interactive ? 'button' : undefined}
        tabIndex={interactive ? 0 : undefined}
      >
        {Icon && (
          <div className={cn('rounded-lg bg-muted p-2 sm:p-3', TONE_ICON[tone] || TONE_ICON.default)}>
            <Icon className="h-5 w-5 sm:h-6 sm:w-6" strokeWidth={1.75} />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-muted-foreground sm:text-sm">{label}</p>
          <p className="truncate text-lg font-bold tracking-tight tabular-metrics sm:text-2xl">
            {value}
          </p>
          <div className="mt-0.5 flex flex-wrap items-center gap-1 sm:gap-2">
            {subtitle && (
              <span className="text-[10px] text-muted-foreground sm:text-xs">{subtitle}</span>
            )}
            {TrendIcon && trend?.label && (
              <span className={cn('flex items-center text-[10px] font-medium sm:text-xs', trendColor)}>
                <TrendIcon className="mr-0.5 h-3 w-3" />
                {trend.label}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (variant === 'inline') {
    return (
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl border bg-muted/30 p-3 sm:gap-3 sm:p-4',
          interactive && 'cursor-pointer transition-colors hover:bg-muted/50',
          className,
        )}
        onClick={onClick}
        role={interactive ? 'button' : undefined}
        tabIndex={interactive ? 0 : undefined}
      >
        {Icon && (
          <div className={cn('rounded-lg bg-background p-2 sm:p-2.5', TONE_ICON[tone] || TONE_ICON.default)}>
            <Icon className="h-4 w-4 sm:h-5 sm:w-5" strokeWidth={1.75} />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-[10px] text-muted-foreground sm:text-xs">{label}</p>
          <p className="truncate text-base font-bold tabular-metrics sm:text-xl">{value}</p>
          {subtitle && (
            <p className="truncate text-[10px] text-muted-foreground sm:text-xs">{subtitle}</p>
          )}
        </div>
      </div>
    )
  }

  // compact (default) — Card shell
  return (
    <Card
      className={cn(
        'relative overflow-hidden',
        interactive && 'cursor-pointer transition-shadow hover:shadow-md',
        className,
      )}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 sm:pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground sm:text-sm">
          {label}
        </CardTitle>
        {Icon && (
          <div className={cn('rounded-lg bg-muted/50 p-1.5 sm:p-2', TONE_ICON[tone] || TONE_ICON.default)}>
            <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" strokeWidth={1.75} />
          </div>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-lg font-bold tabular-metrics sm:text-2xl">{value}</div>
        <div className="mt-0.5 flex flex-wrap items-center justify-between gap-1 sm:mt-1">
          {subtitle && (
            <p className="max-w-[80%] truncate text-[10px] text-muted-foreground sm:text-xs">
              {subtitle}
            </p>
          )}
          {TrendIcon && trend?.label && (
            <span className={cn('flex items-center text-[10px] font-medium sm:text-xs', trendColor)}>
              <TrendIcon className="mr-0.5 h-2.5 w-2.5 sm:h-3 sm:w-3" />
              {trend.label}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
