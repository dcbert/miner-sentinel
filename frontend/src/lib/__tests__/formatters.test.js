import { describe, expect, it } from 'vitest'
import {
  formatDifficulty,
  formatHashrate,
  formatNumber,
  formatPercent,
  formatPower,
  formatRelativeTime,
  formatShares,
  formatTemp,
  getFreshnessState,
} from '../formatters'

describe('formatNumber', () => {
  it('returns "0" for null/undefined/NaN', () => {
    expect(formatNumber(null)).toBe('0')
    expect(formatNumber(undefined)).toBe('0')
    expect(formatNumber(Number.NaN)).toBe('0')
  })
  it('formats with decimals', () => {
    expect(formatNumber(1234.567, 2)).toBe('1,234.57')
  })
})

describe('formatHashrate', () => {
  it('handles edge cases', () => {
    expect(formatHashrate(null)).toBe('0 GH/s')
    expect(formatHashrate(0)).toBe('0 GH/s')
    expect(formatHashrate(-1)).toBe('0 GH/s')
  })
  it('formats units', () => {
    expect(formatHashrate(450.5)).toBe('450.50 GH/s')
    expect(formatHashrate(2500)).toBe('2.50 TH/s')
    expect(formatHashrate(1500000)).toBe('1.50 PH/s')
  })
  it('passes through pool display strings', () => {
    expect(formatHashrate('466G')).toBe('466G')
  })
})

describe('formatShares', () => {
  it('formats compact', () => {
    expect(formatShares(500)).toBe('500')
    expect(formatShares(1500)).toBe('1.5K')
    expect(formatShares(2500000)).toBe('2.5M')
  })
})

describe('formatPower / formatTemp / formatDifficulty', () => {
  it('formatPower', () => {
    expect(formatPower(null)).toBe('N/A')
    expect(formatPower(120)).toBe('120W')
    expect(formatPower(1500)).toBe('1.5 kW')
  })
  it('formatTemp', () => {
    expect(formatTemp(null)).toBe('N/A')
    expect(formatTemp(58.4, 0)).toBe('58°C')
  })
  it('formatDifficulty', () => {
    expect(formatDifficulty(0)).toBe('0')
    expect(formatDifficulty(1e9)).toBe('1.00G')
    expect(formatDifficulty(5e6)).toBe('5.00M')
  })
  it('formatPercent', () => {
    expect(formatPercent(98.76, 1)).toBe('98.8%')
  })
})

describe('formatRelativeTime / getFreshnessState', () => {
  const now = new Date('2026-03-01T12:00:00Z')

  it('relative time bands', () => {
    expect(formatRelativeTime(new Date(now.getTime() - 5000), now)).toBe('Just now')
    expect(formatRelativeTime(new Date(now.getTime() - 45000), now)).toBe('45s ago')
    expect(formatRelativeTime(new Date(now.getTime() - 5 * 60000), now)).toBe('5m ago')
    expect(formatRelativeTime(new Date(now.getTime() - 3 * 3600000), now)).toBe('3h ago')
    expect(formatRelativeTime(null, now)).toBe(null)
  })

  it('freshness state', () => {
    expect(getFreshnessState(new Date(now.getTime() - 60000), now)).toBe('fresh')
    expect(getFreshnessState(new Date(now.getTime() - 10 * 60000), now)).toBe('aging')
    expect(getFreshnessState(new Date(now.getTime() - 30 * 60000), now)).toBe('stale')
    expect(getFreshnessState(null, now)).toBe('unknown')
  })
})
