/**
 * Global time-range model for MinerSentinel dashboards.
 *
 * Presets are relative to "now" and recompute on each read.
 * Custom ranges are absolute from/to timestamps.
 */

export const TIME_RANGE_STORAGE_KEY = 'minersentinel.timeRange'

/** Ordered presets shown in the picker */
export const TIME_RANGE_PRESETS = [
  { key: '1h', label: 'Last 1 hour', shortLabel: '1h', hours: 1 },
  { key: '6h', label: 'Last 6 hours', shortLabel: '6h', hours: 6 },
  { key: '24h', label: 'Last 24 hours', shortLabel: '24h', hours: 24 },
  { key: '7d', label: 'Last 7 days', shortLabel: '7d', hours: 24 * 7 },
  { key: '30d', label: 'Last 30 days', shortLabel: '30d', hours: 24 * 30 },
  { key: '90d', label: 'Last 90 days', shortLabel: '90d', hours: 24 * 90 },
]

export const DEFAULT_TIME_RANGE_KEY = '24h'

const PRESET_MAP = Object.fromEntries(TIME_RANGE_PRESETS.map((p) => [p.key, p]))

/**
 * @typedef {'preset' | 'custom'} TimeRangeMode
 * @typedef {{ mode: 'preset', key: string } | { mode: 'custom', from: string, to: string }} StoredTimeRange
 * @typedef {{
 *   mode: TimeRangeMode,
 *   key: string,
 *   label: string,
 *   shortLabel: string,
 *   from: Date,
 *   to: Date,
 *   hours: number,
 *   days: number,
 * }} ResolvedTimeRange
 */

export function getPreset(key) {
  return PRESET_MAP[key] || PRESET_MAP[DEFAULT_TIME_RANGE_KEY]
}

/** Round duration to whole hours (min 1) and days (min 1). */
export function durationParts(from, to) {
  const ms = Math.max(0, to.getTime() - from.getTime())
  const hours = Math.max(1, Math.ceil(ms / (1000 * 60 * 60)))
  const days = Math.max(1, Math.ceil(hours / 24))
  return { hours, days }
}

function formatCustomLabel(from, to) {
  const opts = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  return `${from.toLocaleString(undefined, opts)} – ${to.toLocaleString(undefined, opts)}`
}

function formatCustomShort(from, to) {
  const sameDay = from.toDateString() === to.toDateString()
  if (sameDay) {
    return `${from.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
  }
  return `${from.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${to.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
}

/**
 * Resolve a stored selection into concrete from/to bounds.
 * Relative presets always end at `now` (or provided `now`).
 * @param {StoredTimeRange | null | undefined} stored
 * @param {Date} [now]
 * @returns {ResolvedTimeRange}
 */
export function resolveTimeRange(stored, now = new Date()) {
  if (stored?.mode === 'custom' && stored.from && stored.to) {
    const from = new Date(stored.from)
    const to = new Date(stored.to)
    if (!Number.isNaN(from.getTime()) && !Number.isNaN(to.getTime()) && to > from) {
      const { hours, days } = durationParts(from, to)
      return {
        mode: 'custom',
        key: 'custom',
        label: formatCustomLabel(from, to),
        shortLabel: formatCustomShort(from, to),
        from,
        to,
        hours,
        days,
      }
    }
  }

  const key = stored?.mode === 'preset' && stored.key ? stored.key : DEFAULT_TIME_RANGE_KEY
  const preset = getPreset(key)
  const to = now
  const from = new Date(to.getTime() - preset.hours * 60 * 60 * 1000)
  const { hours, days } = durationParts(from, to)
  return {
    mode: 'preset',
    key: preset.key,
    label: preset.label,
    shortLabel: preset.shortLabel,
    from,
    to,
    hours,
    days,
  }
}

/**
 * Params for overview/analytics APIs that expect hours + days.
 * Uses a single window: both refer to the selected range.
 */
export function toAnalyticsParams(range) {
  return {
    hours: range.hours,
    days: range.days,
  }
}

/** Params for endpoints that only take hours. */
export function toHoursParams(range) {
  return { hours: range.hours }
}

/** Params for endpoints that only take days. */
export function toDaysParams(range) {
  return { days: range.days }
}

/**
 * Format datetime for <input type="datetime-local" /> (local timezone).
 * @param {Date} date
 */
export function toDatetimeLocalValue(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/**
 * Parse datetime-local string as local Date.
 * @param {string} value
 */
export function fromDatetimeLocalValue(value) {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * Human-readable absolute window for subtitles.
 * @param {ResolvedTimeRange} range
 */
export function formatRangeWindow(range) {
  if (!range?.from || !range?.to) return ''
  const opts = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  return `${range.from.toLocaleString(undefined, opts)} → ${range.to.toLocaleString(undefined, opts)}`
}

/**
 * Load stored selection from localStorage.
 * @returns {StoredTimeRange}
 */
export function loadStoredTimeRange() {
  try {
    const raw = localStorage.getItem(TIME_RANGE_STORAGE_KEY)
    if (!raw) return { mode: 'preset', key: DEFAULT_TIME_RANGE_KEY }
    const parsed = JSON.parse(raw)
    if (parsed?.mode === 'custom' && parsed.from && parsed.to) {
      return { mode: 'custom', from: parsed.from, to: parsed.to }
    }
    if (parsed?.mode === 'preset' && parsed.key && PRESET_MAP[parsed.key]) {
      return { mode: 'preset', key: parsed.key }
    }
    // Legacy: bare key string or { key: '7d' }
    if (typeof parsed === 'string' && PRESET_MAP[parsed]) {
      return { mode: 'preset', key: parsed }
    }
    if (parsed?.key && PRESET_MAP[parsed.key]) {
      return { mode: 'preset', key: parsed.key }
    }
  } catch {
    // ignore corrupt storage
  }
  return { mode: 'preset', key: DEFAULT_TIME_RANGE_KEY }
}

/**
 * @param {StoredTimeRange} stored
 */
export function saveStoredTimeRange(stored) {
  try {
    localStorage.setItem(TIME_RANGE_STORAGE_KEY, JSON.stringify(stored))
  } catch {
    // private mode / quota
  }
}

/** Routes where the global time range control should be visible. */
export function isTimeRangeRoute(pathname) {
  if (!pathname) return false
  if (pathname === '/settings' || pathname.startsWith('/settings/')) return false
  if (pathname === '/login') return false
  return true
}
