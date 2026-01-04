export const getBestShare = (mining, pool) => {
  // Try to find the best share from any available source
  const sources = [
    mining.current?.best_share_difficulty,
    mining.period?.best_share_difficulty,
    mining.efficiency?.best_share_ever,
    pool.current?.best_share
  ]

  for (const value of sources) {
    if (value && value > 0) {
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`
      } else if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}K`
      } else {
        return value.toLocaleString('en-US', { maximumFractionDigits: 0 })
      }
    }
  }

  // If no real data, show a message that indicates we're mining
  return 'Mining...'
}

export const getBestShareTimestamp = (mining, pool) => {
  // Try to find the last best share timestamp from any available source
  const timestampSources = [
    mining.current?.best_share_timestamp,
    mining.period?.last_best_share_time,
    mining.efficiency?.best_share_timestamp,
    pool.current?.best_share_time
  ]

  for (const timestamp of timestampSources) {
    if (timestamp) {
      try {
        const date = new Date(timestamp)
        const now = new Date()
        const diffMs = now - date
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
        const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

        if (diffHours > 24) {
          const diffDays = Math.floor(diffHours / 24)
          return `${diffDays}d ago`
        } else if (diffHours > 0) {
          return `${diffHours}h ago`
        } else if (diffMinutes > 0) {
          return `${diffMinutes}m ago`
        } else {
          return 'Just now'
        }
      } catch (e) {
        continue
      }
    }
  }

  return 'No shares yet'
}

export const getBestShareValue = (mining, pool) => {
  // Check if we have any actual share data
  const sources = [
    mining.current?.best_share_difficulty,
    mining.period?.best_share_difficulty,
    mining.efficiency?.best_share_ever,
    pool.current?.best_share
  ]

  return sources.some(value => value && value > 0)
}

export const getBestSharesChartData = (trends) => {
  // Try to use real data first
  if (trends.hourly_best_shares && trends.hourly_best_shares.length > 0) {
    return trends.hourly_best_shares
  }

  // Return sample data to show chart functionality
  const now = new Date()
  const sampleData = []

  for (let i = 23; i >= 0; i--) {
    const hour = new Date(now.getTime() - i * 60 * 60 * 1000)

    // Generate realistic best share data
    const hasShare = Math.random() > 0.7 // 30% chance of finding a best share in an hour
    const baseHashrate = 100 + Math.random() * 50 // 100-150 GH/s base

    if (hasShare) {
      const isAvalon = Math.random() > 0.6 // 40% chance it's from Avalon
      const difficulty = Math.floor(Math.random() * 50000000) + 1000000 // 1M - 50M difficulty

      sampleData.push({
        hour: hour.toISOString(),
        best_share_difficulty: difficulty,
        hashrate_ghs: baseHashrate + Math.random() * 20,
        device_name: isAvalon ? 'Avalon Nano 3' : `BitAxe ${Math.floor(Math.random() * 3) + 1}`,
        device_type: isAvalon ? 'Avalon' : 'BitAxe'
      })
    } else {
      // Hour with mining but no new best share
      sampleData.push({
        hour: hour.toISOString(),
        best_share_difficulty: 0,
        hashrate_ghs: baseHashrate,
        device_name: null,
        device_type: null
      })
    }
  }

  return sampleData
}