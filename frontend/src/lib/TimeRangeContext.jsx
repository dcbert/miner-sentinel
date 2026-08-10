import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'
import {
  DEFAULT_TIME_RANGE_KEY,
  loadStoredTimeRange,
  resolveTimeRange,
  saveStoredTimeRange,
} from '@/lib/timeRange'

const TimeRangeContext = createContext(null)

export function TimeRangeProvider({ children }) {
  const [stored, setStored] = useState(() => loadStoredTimeRange())
  // Tick bumps when we want relative ranges to re-resolve "now" without changing selection
  const [tick, setTick] = useState(0)

  const range = useMemo(
    () => resolveTimeRange(stored, new Date()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [stored, tick],
  )

  const setPreset = useCallback((key) => {
    const next = { mode: 'preset', key: key || DEFAULT_TIME_RANGE_KEY }
    setStored(next)
    saveStoredTimeRange(next)
  }, [])

  const setCustomRange = useCallback((from, to) => {
    const fromDate = from instanceof Date ? from : new Date(from)
    const toDate = to instanceof Date ? to : new Date(to)
    if (Number.isNaN(fromDate.getTime()) || Number.isNaN(toDate.getTime())) {
      return { ok: false, error: 'Invalid date range' }
    }
    if (toDate <= fromDate) {
      return { ok: false, error: 'End must be after start' }
    }
    // Cap custom window at 365 days to protect API
    const maxMs = 365 * 24 * 60 * 60 * 1000
    if (toDate.getTime() - fromDate.getTime() > maxMs) {
      return { ok: false, error: 'Range cannot exceed 365 days' }
    }
    const next = {
      mode: 'custom',
      from: fromDate.toISOString(),
      to: toDate.toISOString(),
    }
    setStored(next)
    saveStoredTimeRange(next)
    return { ok: true }
  }, [])

  const refreshBounds = useCallback(() => {
    setTick((t) => t + 1)
  }, [])

  const value = useMemo(
    () => ({
      range,
      stored,
      setPreset,
      setCustomRange,
      refreshBounds,
    }),
    [range, stored, setPreset, setCustomRange, refreshBounds],
  )

  return (
    <TimeRangeContext.Provider value={value}>
      {children}
    </TimeRangeContext.Provider>
  )
}

export function useTimeRange() {
  const ctx = useContext(TimeRangeContext)
  if (!ctx) {
    throw new Error('useTimeRange must be used within TimeRangeProvider')
  }
  return ctx
}

/**
 * Safe hook for components that may render outside the provider (tests).
 * Falls back to default 24h range.
 */
export function useTimeRangeOptional() {
  const ctx = useContext(TimeRangeContext)
  if (ctx) return ctx
  const range = resolveTimeRange({ mode: 'preset', key: DEFAULT_TIME_RANGE_KEY })
  return {
    range,
    stored: { mode: 'preset', key: DEFAULT_TIME_RANGE_KEY },
    setPreset: () => {},
    setCustomRange: () => ({ ok: false }),
    refreshBounds: () => {},
  }
}
