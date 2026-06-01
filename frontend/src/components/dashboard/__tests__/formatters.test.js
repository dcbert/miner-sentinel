import { describe, expect, it } from 'vitest';
import {
    formatAxisDifficulty,
    formatAxisHashrate,
    formatAxisPower,
    formatAxisShares,
    formatHashrate,
    formatNumber,
    formatShares,
} from '../formatters';

describe('formatNumber', () => {
  it('returns "0" for null', () => {
    expect(formatNumber(null)).toBe('0')
  })
  it('returns "0" for undefined', () => {
    expect(formatNumber(undefined)).toBe('0')
  })
  it('formats integer with locale', () => {
    expect(formatNumber(1000)).toBe('1,000')
  })
  it('formats with decimals', () => {
    expect(formatNumber(1234.567, 2)).toBe('1,234.57')
  })
  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0')
  })
})

describe('formatHashrate', () => {
  it('returns "0 GH/s" for null', () => {
    expect(formatHashrate(null)).toBe('0 GH/s')
  })
  it('returns "0 GH/s" for undefined', () => {
    expect(formatHashrate(undefined)).toBe('0 GH/s')
  })
  it('returns "0 GH/s" for zero', () => {
    expect(formatHashrate(0)).toBe('0 GH/s')
  })
  it('formats GH/s for small values', () => {
    expect(formatHashrate(450.5)).toBe('450.50 GH/s')
  })
  it('formats TH/s for >= 1000 GH/s', () => {
    expect(formatHashrate(2500)).toBe('2.50 TH/s')
  })
  it('formats PH/s for >= 1000000 GH/s (1500 TH = 1.5 PH)', () => {
    expect(formatHashrate(1500000)).toBe('1.50 PH/s')
  })
  it('formats PH/s for exactly 2000 TH', () => {
    expect(formatHashrate(2000 * 1000)).toBe('2.00 PH/s')
  })
})

describe('formatShares', () => {
  it('returns "0" for null', () => {
    expect(formatShares(null)).toBe('0')
  })
  it('returns "0" for undefined', () => {
    expect(formatShares(undefined)).toBe('0')
  })
  it('formats small numbers as-is', () => {
    expect(formatShares(500)).toBe('500')
  })
  it('formats thousands with K suffix', () => {
    expect(formatShares(1500)).toBe('1.5K')
  })
  it('formats millions with M suffix', () => {
    expect(formatShares(2500000)).toBe('2.5M')
  })
})

describe('formatAxisHashrate', () => {
  it('returns "0" for zero', () => {
    expect(formatAxisHashrate(0)).toBe('0')
  })
  it('formats G range', () => {
    expect(formatAxisHashrate(500)).toBe('500G')
  })
  it('formats T range (>=1000)', () => {
    expect(formatAxisHashrate(1500)).toBe('1.5T')
  })
  it('formats P range (>=1000000)', () => {
    expect(formatAxisHashrate(1500000)).toBe('1.5P')
  })
  it('formats exact P range', () => {
    const result = formatAxisHashrate(2000000)
    expect(result).toContain('P')
  })
})

describe('formatAxisShares', () => {
  it('returns "0" for zero', () => {
    expect(formatAxisShares(0)).toBe('0')
  })
  it('formats small values as string', () => {
    expect(formatAxisShares(500)).toBe('500')
  })
  it('formats K range', () => {
    expect(formatAxisShares(1500)).toBe('1.5K')
  })
  it('formats M range', () => {
    expect(formatAxisShares(1500000)).toBe('1.5M')
  })
  it('formats B range', () => {
    expect(formatAxisShares(1500000000)).toBe('1.5B')
  })
})

describe('formatAxisDifficulty', () => {
  it('returns "0" for zero', () => {
    expect(formatAxisDifficulty(0)).toBe('0')
  })
  it('formats small values as string', () => {
    expect(formatAxisDifficulty(500)).toBe('500')
  })
  it('formats K range', () => {
    expect(formatAxisDifficulty(1500)).toBe('1.5K')
  })
  it('formats M range', () => {
    expect(formatAxisDifficulty(1500000)).toBe('1.5M')
  })
  it('formats B range', () => {
    expect(formatAxisDifficulty(1500000000)).toBe('1.5B')
  })
})

describe('formatAxisPower', () => {
  it('returns "0" for zero', () => {
    expect(formatAxisPower(0)).toBe('0')
  })
  it('formats W for < 1000', () => {
    expect(formatAxisPower(850)).toBe('850W')
  })
  it('formats kW for >= 1000', () => {
    expect(formatAxisPower(1500)).toBe('1.5kW')
  })
})
