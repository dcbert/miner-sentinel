import { cn } from '@/lib/utils'

const STATUS_META = {
  online: {
    dot: 'bg-status-online',
    text: 'text-status-online-fg',
    label: 'Online',
    pulse: true,
  },
  warning: {
    dot: 'bg-status-warning',
    text: 'text-status-warning-fg',
    label: 'Warning',
    pulse: false,
  },
  offline: {
    dot: 'bg-status-critical',
    text: 'text-status-critical-fg',
    label: 'Offline',
    pulse: false,
  },
  stale: {
    dot: 'bg-status-stale',
    text: 'text-status-stale-fg',
    label: 'Stale',
    pulse: false,
  },
  unknown: {
    dot: 'bg-status-unknown',
    text: 'text-status-unknown-fg',
    label: 'Unknown',
    pulse: false,
  },
}

const SIZES = {
  sm: 'h-2 w-2',
  md: 'h-2.5 w-2.5',
  lg: 'h-3 w-3',
}

/**
 * Operational status dot (+ optional text label).
 * Always provides accessible name via label or aria-label.
 */
export default function StatusIndicator({
  status = 'online',
  size = 'sm',
  label,
  showLabel = false,
  pulse,
  className,
  'aria-label': ariaLabel,
}) {
  const meta = STATUS_META[status] || STATUS_META.unknown
  const sizeClass = SIZES[size] || SIZES.sm
  const shouldPulse = pulse ?? meta.pulse
  const accessible = ariaLabel || label || meta.label

  return (
    <span
      className={cn('inline-flex items-center gap-1.5', className)}
      role="status"
      aria-label={accessible}
    >
      <span className="relative flex shrink-0">
        {shouldPulse && (
          <span
            className={cn(
              'status-pulse absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
              meta.dot,
              sizeClass,
            )}
            aria-hidden
          />
        )}
        <span
          className={cn('relative inline-flex rounded-full', meta.dot, sizeClass)}
          aria-hidden
        />
      </span>
      {(showLabel || label) && (
        <span className={cn('text-xs font-medium', meta.text)}>
          {label || meta.label}
        </span>
      )}
    </span>
  )
}

export { STATUS_META }
