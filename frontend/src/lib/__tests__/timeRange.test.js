import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_TIME_RANGE_KEY,
  MAX_TIME_RANGE_DAYS,
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
  toTimeRangeParams,
} from '@/lib/timeRange'

describe('timeRange helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  it('defaults to 30d ending at now', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange(null, now)
    expect(range.key).toBe('30d')
    expect(range.key).toBe(DEFAULT_TIME_RANGE_KEY)
    expect(range.mode).toBe('preset')
    expect(range.hours).toBe(24 * 30)
    expect(range.days).toBe(30)
    expect(range.to.getTime()).toBe(now.getTime())
    expect(range.from.getTime()).toBe(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    expect(range.label).toMatch(/30 days/i)
  })

  it('resolves 7d preset', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange({ mode: 'preset', key: '7d' }, now)
    expect(range.hours).toBe(168)
    expect(range.days).toBe(7)
    expect(range.label).toMatch(/7 days/i)
  })

  it('resolves 1h without inflating days for display duration', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange({ mode: 'preset', key: '1h' }, now)
    expect(range.hours).toBe(1)
    // days is ceil(hours/24) minimum 1 — API uses hours as the single window
    expect(range.days).toBe(1)
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

  it('maps analytics/hours/days params with absolute from/to', () => {
    const now = new Date('2026-07-23T12:00:00.000Z')
    const range = resolveTimeRange({ mode: 'preset', key: '30d' }, now)
    const params = toAnalyticsParams(range)
    expect(params.hours).toBe(range.hours)
    expect(params.days).toBe(range.days)
    expect(params.from).toBe(range.from.toISOString())
    expect(params.to).toBe(range.to.toISOString())
    expect(toHoursParams(range)).toEqual(params)
    expect(toDaysParams(range)).toEqual(params)
    expect(toTimeRangeParams(range)).toEqual(params)
  })

  it('includes absolute bounds for custom ranges', () => {
    const from = '2026-06-01T00:00:00.000Z'
    const to = '2026-06-08T00:00:00.000Z'
    const range = resolveTimeRange({ mode: 'custom', from, to })
    const params = toTimeRangeParams(range)
    expect(params.from).toBe(new Date(from).toISOString())
    expect(params.to).toBe(new Date(to).toISOString())
    expect(params.hours).toBe(range.hours)
    expect(params.days).toBe(range.days)
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

  it('caps custom range constant matches backend', () => {
    expect(MAX_TIME_RANGE_DAYS).toBe(90)
  })

  it('formatRangeWindow includes arrow', () => {
    const range = resolveTimeRange({ mode: 'preset', key: '1h' }, new Date('2026-07-23T12:00:00Z'))
    expect(formatRangeWindow(range)).toContain('→')
  })
})
