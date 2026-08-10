import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTimeRange } from '@/lib/TimeRangeContext'
import {
  TIME_RANGE_PRESETS,
  formatRangeWindow,
  fromDatetimeLocalValue,
  toDatetimeLocalValue,
} from '@/lib/timeRange'
import { cn } from '@/lib/utils'
import {
  CalendarClock,
  Check,
  ChevronDown,
  Clock,
} from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

/**
 * Navbar time-range control: presets + custom absolute window.
 * Desktop: compact chip with popover. Mobile: same chip (full-width friendly).
 */
export default function GlobalTimeRange({ className, compact = false }) {
  const { range, setPreset, setCustomRange } = useTimeRange()
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState(range.mode === 'custom' ? 'custom' : 'presets')
  const [customFrom, setCustomFrom] = useState(() => toDatetimeLocalValue(range.from))
  const [customTo, setCustomTo] = useState(() => toDatetimeLocalValue(range.to))
  const [error, setError] = useState(null)
  const rootRef = useRef(null)
  const panelId = useId()

  // Sync custom fields when opening or when selection changes externally
  useEffect(() => {
    if (open) {
      setTab(range.mode === 'custom' ? 'custom' : 'presets')
      setCustomFrom(toDatetimeLocalValue(range.from))
      setCustomTo(toDatetimeLocalValue(range.to || new Date()))
      setError(null)
    }
  }, [open, range.mode, range.from, range.to])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const onClick = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onClick)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('mousedown', onClick)
    }
  }, [open])

  const handlePreset = (key) => {
    setPreset(key)
    setError(null)
    setOpen(false)
  }

  const handleApplyCustom = () => {
    const from = fromDatetimeLocalValue(customFrom)
    const to = fromDatetimeLocalValue(customTo)
    if (!from || !to) {
      setError('Choose both start and end times')
      return
    }
    const result = setCustomRange(from, to)
    if (!result.ok) {
      setError(result.error || 'Invalid range')
      return
    }
    setError(null)
    setOpen(false)
  }

  const setQuickCustom = (hoursBack) => {
    const to = new Date()
    const from = new Date(to.getTime() - hoursBack * 60 * 60 * 1000)
    setCustomFrom(toDatetimeLocalValue(from))
    setCustomTo(toDatetimeLocalValue(to))
    setError(null)
  }

  return (
    <div ref={rootRef} className={cn('relative', className)}>
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'group flex items-center gap-2 rounded-md border border-border bg-background px-2.5 text-left transition-colors',
          'hover:bg-accent/50 hover:border-border',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          open && 'bg-accent/60 border-border',
          compact ? 'h-9 w-full max-w-full' : 'h-9 min-w-[11.5rem]',
        )}
      >
        <CalendarClock
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
          strokeWidth={1.75}
        />
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-medium leading-none text-muted-foreground">
            Range
          </span>
          <span className="mt-0.5 block truncate text-[13px] font-medium leading-tight text-foreground">
            {range.label}
          </span>
        </span>
        <ChevronDown
          className={cn(
            'h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="Select time range"
          className={cn(
            'absolute z-50 mt-1.5 w-[min(100vw-1.5rem,20rem)] rounded-lg border border-border bg-popover text-popover-foreground shadow-lg',
            'right-0 left-auto',
            compact && 'left-0 right-0 w-full',
          )}
        >
          {/* Segment tabs */}
          <div className="flex gap-0.5 border-b border-border/80 p-1">
            <button
              type="button"
              onClick={() => setTab('presets')}
              className={cn(
                'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                tab === 'presets'
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-muted/80 hover:text-foreground',
              )}
            >
              Presets
            </button>
            <button
              type="button"
              onClick={() => setTab('custom')}
              className={cn(
                'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                tab === 'custom'
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-muted/80 hover:text-foreground',
              )}
            >
              Custom
            </button>
          </div>

          {tab === 'presets' ? (
            <div className="p-2 max-h-[min(60vh,20rem)] overflow-y-auto">
              <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Relative to now
              </p>
              <ul className="space-y-0.5">
                {TIME_RANGE_PRESETS.map((preset) => {
                  const selected = range.mode === 'preset' && range.key === preset.key
                  return (
                    <li key={preset.key}>
                      <button
                        type="button"
                        onClick={() => handlePreset(preset.key)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                          selected
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'hover:bg-muted text-foreground',
                        )}
                      >
                        <Clock className={cn('h-4 w-4 shrink-0', selected ? 'text-primary' : 'text-muted-foreground')} />
                        <span className="flex-1 text-left">{preset.label}</span>
                        <span className="text-[10px] font-mono text-muted-foreground uppercase">
                          {preset.shortLabel}
                        </span>
                        {selected && <Check className="h-4 w-4 text-primary shrink-0" />}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : (
            <div className="p-3 space-y-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Absolute window
              </p>
              <div className="grid gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="tr-from" className="text-xs">From</Label>
                  <Input
                    id="tr-from"
                    type="datetime-local"
                    value={customFrom}
                    onChange={(e) => {
                      setCustomFrom(e.target.value)
                      setError(null)
                    }}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="tr-to" className="text-xs">To</Label>
                  <Input
                    id="tr-to"
                    type="datetime-local"
                    value={customTo}
                    onChange={(e) => {
                      setCustomTo(e.target.value)
                      setError(null)
                    }}
                    className="h-9 text-sm"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {[
                  { label: 'Last 24h', h: 24 },
                  { label: 'Last 7d', h: 24 * 7 },
                  { label: 'Last 30d', h: 24 * 30 },
                ].map((q) => (
                  <button
                    key={q.label}
                    type="button"
                    onClick={() => setQuickCustom(q.h)}
                    className="rounded-md border bg-muted/40 px-2 py-1 text-[10px] font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    {q.label}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setCustomTo(toDatetimeLocalValue(new Date()))}
                  className="rounded-md border bg-muted/40 px-2 py-1 text-[10px] font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  End = now
                </button>
              </div>

              {error && (
                <p className="text-xs text-destructive" role="alert">{error}</p>
              )}

              <div className="flex gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="flex-1"
                  onClick={handleApplyCustom}
                >
                  Apply range
                </Button>
              </div>
            </div>
          )}

          <div className="border-t bg-muted/30 px-3 py-2 rounded-b-xl">
            <p className="text-[10px] text-muted-foreground leading-snug">
              <span className="font-medium text-foreground/80">Active window:</span>{' '}
              {formatRangeWindow(range)}
            </p>
            <p className="text-[10px] text-muted-foreground/80 mt-0.5">
              Custom ranges up to 90 days · absolute from/to sent to the API
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
