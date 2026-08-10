/**
 * Single source of truth for metric formatting across dashboards.
 * Prefer importing from here (or @/components/dashboard which re-exports).
 */

export const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return '0'
  const n = Number(num)
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export const formatHashrate = (hashrate_ghs) => {
  if (hashrate_ghs === null || hashrate_ghs === undefined || hashrate_ghs === 0) {
    return '0 GH/s'
  }

  // Pool display strings like "466G"
  if (typeof hashrate_ghs === 'string' && /[A-Za-z]/.test(hashrate_ghs)) {
    return hashrate_ghs
  }

  const ghs = Number(hashrate_ghs)
  if (!Number.isFinite(ghs) || ghs < 0) {
    return '0 GH/s'
  }

  if (ghs >= 1000) {
    const ths = ghs / 1000
    if (ths >= 1000) {
      const phs = ths / 1000
      return `${phs.toFixed(2)} PH/s`
    }
    return `${ths.toFixed(2)} TH/s`
  }

  return `${ghs.toFixed(2)} GH/s`
}

export const formatShares = (shares) => {
  if (shares === null || shares === undefined) return '0'
  const n = Number(shares)
  if (!Number.isFinite(n)) return '0'
  if (n >= 1000000) {
    return `${(n / 1000000).toFixed(1)}M`
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}K`
  }
  return n.toString()
}

export const formatPower = (watts, decimals = 0) => {
  if (watts === null || watts === undefined) return 'N/A'
  const n = Number(watts)
  if (!Number.isFinite(n)) return 'N/A'
  if (n >= 1000) return `${(n / 1000).toFixed(1)} kW`
  return `${n.toFixed(decimals)}W`
}

export const formatTemp = (celsius, decimals = 0) => {
  if (celsius === null || celsius === undefined) return 'N/A'
  const n = Number(celsius)
  if (!Number.isFinite(n)) return 'N/A'
  return `${n.toFixed(decimals)}°C`
}

export const formatDifficulty = (diff) => {
  if (diff === null || diff === undefined || diff === 0) return '0'
  const n = Number(diff)
  if (!Number.isFinite(n)) return '0'
  if (n >= 1e15) return `${(n / 1e15).toFixed(2)}P`
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}G`
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return Math.round(n).toLocaleString('en-US')
}

export const formatPercent = (value, decimals = 1) => {
  if (value === null || value === undefined) return '0%'
  const n = Number(value)
  if (!Number.isFinite(n)) return '0%'
  return `${n.toFixed(decimals)}%`
}

/**
 * Relative time for ops freshness (e.g. "45s ago", "3m ago", "2h ago").
 * @param {Date|string|number|null|undefined} date
 * @param {Date} [now]
 */
export const formatRelativeTime = (date, now = new Date()) => {
  if (date === null || date === undefined) return null
  const d = date instanceof Date ? date : new Date(date)
  if (!Number.isFinite(d.getTime())) return null

  const diffMs = Math.max(0, now.getTime() - d.getTime())
  const sec = Math.floor(diffMs / 1000)
  if (sec < 10) return 'Just now'
  if (sec < 60) return `${sec}s ago`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hours = Math.floor(min / 60)
  if (hours < 48) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

/**
 * Freshness band for poll-based dashboards (default 2m poll).
 * @returns {'fresh'|'aging'|'stale'|'unknown'}
 */
export const getFreshnessState = (date, now = new Date(), thresholds = {}) => {
  const freshMs = thresholds.freshMs ?? 3 * 60 * 1000
  const agingMs = thresholds.agingMs ?? 15 * 60 * 1000
  if (date === null || date === undefined) return 'unknown'
  const d = date instanceof Date ? date : new Date(date)
  if (!Number.isFinite(d.getTime())) return 'unknown'
  const age = now.getTime() - d.getTime()
  if (age < freshMs) return 'fresh'
  if (age < agingMs) return 'aging'
  return 'stale'
}

// Chart axis formatters
export const formatAxisHashrate = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '0'
  if (n >= 1000000) {
    return `${(n / 1000000).toFixed(1)}P`
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}T`
  }
  return `${n.toFixed(0)}G`
}

export const formatAxisShares = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '0'
  if (n >= 1000000000) {
    return `${(n / 1000000000).toFixed(1)}B`
  }
  if (n >= 1000000) {
    return `${(n / 1000000).toFixed(1)}M`
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}K`
  }
  return n.toString()
}

export const formatAxisDifficulty = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '0'
  if (n >= 1000000000) {
    return `${(n / 1000000000).toFixed(1)}B`
  }
  if (n >= 1000000) {
    return `${(n / 1000000).toFixed(1)}M`
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}K`
  }
  return n.toString()
}

export const formatAxisPower = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n === 0) return '0'
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}kW`
  }
  return `${n.toFixed(0)}W`
}

// Re-export adaptive time-axis helpers
export {
  chartTimeAxisFromRange,
  getChartTimeAxisConfig,
  parseChartTime,
} from '@/lib/timeRange'
