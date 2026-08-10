import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_TIME_RANGE_KEY,
  TIME_RANGE_STORAGE_KEY,
  durationParts,
  formatRangeWindow,
  fromDatetimeLocalValue,
  getPreset,
  isTimeRangeRoute,
  loadStoredTimeRange,
  resolveTimeRange,
  saveStoredTimeRange,
  toAnalyticsParams,
  toDatetimeLocalValue,
  toDaysParams,
  toHoursParams,
} from '@/lib/timeRange'

describe('timeRange helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  it('resolves default preset to 24h ending at now', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange(null, now)
    expect(range.key).toBe(DEFAULT_TIME_RANGE_KEY)
    expect(range.mode).toBe('preset')
    expect(range.hours).toBe(24)
    expect(range.days).toBe(1)
    expect(range.to.getTime()).toBe(now.getTime())
    expect(range.from.getTime()).toBe(now.getTime() - 24 * 60 * 60 * 1000)
    expect(range.label).toMatch(/24/i)
  })

  it('resolves 7d preset', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange({ mode: 'preset', key: '7d' }, now)
    expect(range.hours).toBe(168)
    expect(range.days).toBe(7)
    expect(range.label).toMatch(/7 days/i)
  })

  it('resolves custom absolute range', () => {
    const from = '2026-07-01T00:00:00.000Z'
    const to = '2026-07-10T00:00:00.000Z'
    const range = resolveTimeRange({ mode: 'custom', from, to })
    expect(range.mode).toBe('custom')
    expect(range.key).toBe('custom')
    expect(range.days).toBe(9)
    expect(range.label).toContain('–')
  })

  it('falls back when custom range is invalid', () => {
    const range = resolveTimeRange({ mode: 'custom', from: 'bad', to: 'also-bad' })
    expect(range.mode).toBe('preset')
    expect(range.key).toBe(DEFAULT_TIME_RANGE_KEY)
  })

  it('maps analytics/hours/days params', () => {
    const range = resolveTimeRange({ mode: 'preset', key: '30d' }, new Date())
    expect(toAnalyticsParams(range)).toEqual({ hours: range.hours, days: range.days })
    expect(toHoursParams(range)).toEqual({ hours: range.hours })
    expect(toDaysParams(range)).toEqual({ days: range.days })
  })

  it('durationParts enforces minimums', () => {
    const a = new Date('2026-01-01T00:00:00Z')
    const b = new Date('2026-01-01T00:30:00Z')
    expect(durationParts(a, b)).toEqual({ hours: 1, days: 1 })
  })

  it('round-trips datetime-local values', () => {
    const d = new Date(2026, 6, 23, 15, 30, 0)
    const local = toDatetimeLocalValue(d)
    expect(local).toMatch(/^2026-07-23T15:30$/)
    const parsed = fromDatetimeLocalValue(local)
    expect(parsed.getFullYear()).toBe(2026)
    expect(parsed.getMonth()).toBe(6)
    expect(parsed.getDate()).toBe(23)
  })

  it('persists and loads stored range', () => {
    saveStoredTimeRange({ mode: 'preset', key: '7d' })
    expect(JSON.parse(localStorage.getItem(TIME_RANGE_STORAGE_KEY)).key).toBe('7d')
    expect(loadStoredTimeRange()).toEqual({ mode: 'preset', key: '7d' })

    saveStoredTimeRange({
      mode: 'custom',
      from: '2026-01-01T00:00:00.000Z',
      to: '2026-01-02T00:00:00.000Z',
    })
    expect(loadStoredTimeRange().mode).toBe('custom')
  })

  it('isTimeRangeRoute hides settings and login', () => {
    expect(isTimeRangeRoute('/')).toBe(true)
    expect(isTimeRangeRoute('/mining')).toBe(true)
    expect(isTimeRangeRoute('/analytics')).toBe(true)
    expect(isTimeRangeRoute('/devices/bitaxe/x')).toBe(true)
    expect(isTimeRangeRoute('/settings')).toBe(false)
    expect(isTimeRangeRoute('/login')).toBe(false)
  })

  it('getPreset falls back to default', () => {
    expect(getPreset('nope').key).toBe(DEFAULT_TIME_RANGE_KEY)
  })

  it('formatRangeWindow includes arrow', () => {
    const range = resolveTimeRange({ mode: 'preset', key: '1h' }, new Date('2026-07-23T12:00:00Z'))
    expect(formatRangeWindow(range)).toContain('→')
  })
})
