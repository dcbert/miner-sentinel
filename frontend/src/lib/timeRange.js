/**
 * Global time-range model for MinerSentinel dashboards.
 *
 * Presets are relative to "now" and recompute on each read.
 * Custom ranges are absolute from/to timestamps.
 */

export const TIME_RANGE_STORAGE_KEY = 'minersentinel.timeRange'

/** Match backend MAX_DAYS / MAX_HOURS (protect large installs). */
export const MAX_TIME_RANGE_DAYS = 90
export const MAX_TIME_RANGE_HOURS = 24 * MAX_TIME_RANGE_DAYS

/** Ordered presets shown in the picker */
export const TIME_RANGE_PRESETS = [
  { key: '1h', label: 'Last 1 hour', shortLabel: '1h', hours: 1 },
  { key: '6h', label: 'Last 6 hours', shortLabel: '6h', hours: 6 },
  { key: '24h', label: 'Last 24 hours', shortLabel: '24h', hours: 24 },
  { key: '7d', label: 'Last 7 days', shortLabel: '7d', hours: 24 * 7 },
  { key: '30d', label: 'Last 30 days', shortLabel: '30d', hours: 24 * 30 },
  { key: '90d', label: 'Last 90 days', shortLabel: '90d', hours: 24 * 90 },
]

export const DEFAULT_TIME_RANGE_KEY = '30d'

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
 * Full time-range query params for APIs.
 * Always includes hours/days duration plus absolute from/to so custom ranges
 * (and preset windows resolved at fetch time) apply correctly server-side.
 */
export function toTimeRangeParams(range) {
  if (!range) {
    return { hours: 24 * 30, days: 30 }
  }
  const params = {
    hours: range.hours,
    days: range.days,
  }
  if (range.from instanceof Date && !Number.isNaN(range.from.getTime())) {
    params.from = range.from.toISOString()
  }
  if (range.to instanceof Date && !Number.isNaN(range.to.getTime())) {
    params.to = range.to.toISOString()
  }
  return params
}

/**
 * Params for overview/analytics APIs that expect hours + days (+ from/to).
 * Uses a single window: both refer to the selected range.
 */
export function toAnalyticsParams(range) {
  return toTimeRangeParams(range)
}

/** Params for endpoints that primarily take hours (also sends from/to/days). */
export function toHoursParams(range) {
  return toTimeRangeParams(range)
}

/** Params for endpoints that primarily take days (also sends from/to/hours). */
export function toDaysParams(range) {
  return toTimeRangeParams(range)
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

// ---------------------------------------------------------------------------
// Adaptive chart time axis (depends on selected window length)
// ---------------------------------------------------------------------------

/**
 * Parse chart time values: ISO strings, Date, unix seconds/ms, or already-local strings.
 * @param {string|number|Date|null|undefined} value
 * @returns {Date|null}
 */
export function parseChartTime(value) {
  if (value == null || value === '') return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    // Heuristic: values < 1e12 are unix seconds
    const ms = value < 1e12 ? value * 1000 : value
    const d = new Date(ms)
    return Number.isNaN(d.getTime()) ? null : d
  }
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * Pick an axis formatting strategy from the window length in hours.
 *
 * | Span        | Tick label              | Tooltip                          |
 * |-------------|-------------------------|----------------------------------|
 * | ≤ 6h        | HH:mm                   | Mar 5, HH:mm                     |
 * | ≤ 48h       | Mar 5 HH:mm             | Mar 5, HH:mm                     |
 * | ≤ 14d       | Mar 5                   | Mar 5, HH:mm                     |
 * | > 14d       | Mar 5                   | Mar 5, YYYY HH:mm                |
 *
 * @param {number} hours
 * @returns {{
 *   bucket: 'minutes' | 'hours' | 'days' | 'weeks',
 *   minTickGap: number,
 *   interval: 'preserveStartEnd' | number,
 *   tick: (value: any) => string,
 *   tooltip: (value: any) => string,
 * }}
 */
export function getChartTimeAxisConfig(hours) {
  const h = Math.max(1, Number(hours) || 24)

  const fmt = (value, opts) => {
    const d = parseChartTime(value)
    if (!d) return typeof value === 'string' ? value : ''
    return d.toLocaleString(undefined, opts)
  }

  if (h <= 6) {
    return {
      bucket: 'minutes',
      minTickGap: 48,
      interval: 'preserveStartEnd',
      tick: (value) =>
        fmt(value, { hour: '2-digit', minute: '2-digit' }),
      tooltip: (value) =>
        fmt(value, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
    }
  }

  if (h <= 48) {
    return {
      bucket: 'hours',
      minTickGap: 56,
      interval: 'preserveStartEnd',
      tick: (value) =>
        fmt(value, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
      tooltip: (value) =>
        fmt(value, {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
    }
  }

  if (h <= 24 * 14) {
    return {
      bucket: 'days',
      minTickGap: 64,
      interval: 'preserveStartEnd',
      tick: (value) =>
        fmt(value, { month: 'short', day: 'numeric' }),
      tooltip: (value) =>
        fmt(value, {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
    }
  }

  // 30d / 90d / long custom
  return {
    bucket: 'weeks',
    minTickGap: 72,
    interval: 'preserveStartEnd',
    tick: (value) =>
      fmt(value, { month: 'short', day: 'numeric' }),
    tooltip: (value) =>
      fmt(value, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
  }
}

/**
 * Convenience: build axis config from a resolved range object.
 * @param {{ hours?: number } | null | undefined} range
 */
export function chartTimeAxisFromRange(range) {
  return getChartTimeAxisConfig(range?.hours ?? 24)
}
