import { formatRelativeTime, getFreshnessState } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import { Clock } from 'lucide-react'
import { useEffect, useState } from 'react'

/**
 * Shows when data was last refreshed and whether it may be stale.
 *
 * @param {Date|string|number|null} updatedAt
 * @param {boolean} [live=false] show "Live" badge for current-snapshot metrics
 */
export default function DataFreshness({
  updatedAt,
  live = false,
  className,
  thresholds,
}) {
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 15000)
    return () => clearInterval(id)
  }, [])

  const now = new Date()
  const relative = formatRelativeTime(updatedAt, now)
  const state = getFreshnessState(updatedAt, now, thresholds)

  const stateClass = {
    fresh: 'text-muted-foreground',
    aging: 'text-status-warning-fg',
    stale: 'text-status-critical-fg',
    unknown: 'text-muted-foreground',
  }[state]

  const absolute =
    updatedAt != null
      ? new Date(updatedAt).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      : null

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 text-[11px] sm:text-xs',
        stateClass,
        className,
      )}
      title={absolute || undefined}
      aria-live="polite"
    >
      <Clock className="h-3 w-3 shrink-0 opacity-70" strokeWidth={1.75} aria-hidden />
      {live && (
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-foreground/80">
          Live
        </span>
      )}
      <span>
        {relative ? (
          <>
            Updated <span className="font-medium text-foreground/90">{relative}</span>
            {state === 'stale' && (
              <span className="ml-1 font-medium">· may be stale</span>
            )}
          </>
        ) : (
          <span>Waiting for data</span>
        )}
      </span>
    </div>
  )
}
