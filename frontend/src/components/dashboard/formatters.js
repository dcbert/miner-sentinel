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

  const ghs = Number(hashrate_ghs)
  if (!Number.isFinite(ghs) || ghs < 0) {
    return '0 GH/s'
  }

  // Convert to TH/s if >= 1000 GH/s
  if (ghs >= 1000) {
    const ths = ghs / 1000
    if (ths >= 1000) {
      // Convert to PH/s if >= 1000 TH/s
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

// Re-export adaptive time-axis helpers (window-aware chart labels)
export {
  chartTimeAxisFromRange,
  getChartTimeAxisConfig,
  parseChartTime,
} from '@/lib/timeRange'