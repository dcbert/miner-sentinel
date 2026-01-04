export const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return '0'
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export const formatHashrate = (hashrate_ghs) => {
  if (hashrate_ghs === null || hashrate_ghs === undefined || hashrate_ghs === 0) {
    return '0 GH/s'
  }

  // Convert to TH/s if >= 1000 GH/s
  if (hashrate_ghs >= 1000) {
    const ths = hashrate_ghs / 1000
    if (ths >= 1000) {
      // Convert to PH/s if >= 1000 TH/s
      const phs = ths / 1000
      return `${phs.toFixed(2)} PH/s`
    }
    return `${ths.toFixed(2)} TH/s`
  }

  return `${hashrate_ghs.toFixed(2)} GH/s`
}

export const formatShares = (shares) => {
  if (shares === null || shares === undefined) return '0'
  if (shares >= 1000000) {
    return `${(shares / 1000000).toFixed(1)}M`
  }
  if (shares >= 1000) {
    return `${(shares / 1000).toFixed(1)}K`
  }
  return shares.toString()
}

// Chart axis formatters
export const formatAxisHashrate = (value) => {
  if (value === 0) return '0'
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}P`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}T`
  }
  return `${value.toFixed(0)}G`
}

export const formatAxisShares = (value) => {
  if (value === 0) return '0'
  if (value >= 1000000000) {
    return `${(value / 1000000000).toFixed(1)}B`
  }
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

export const formatAxisDifficulty = (value) => {
  if (value === 0) return '0'
  if (value >= 1000000000) {
    return `${(value / 1000000000).toFixed(1)}B`
  }
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

export const formatAxisPower = (value) => {
  if (value === 0) return '0'
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}kW`
  }
  return `${value.toFixed(0)}W`
}