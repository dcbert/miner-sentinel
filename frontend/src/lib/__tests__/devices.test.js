import { describe, expect, it } from 'vitest'
import {
  deviceDetailPath,
  deviceStatusLabel,
  getDeviceStatus,
  isDeviceOnline,
  legacyDevicePath,
  makeLabel,
  ONLINE_MAX_AGE_MS,
  unwrapList,
} from '@/lib/devices'

const freshIso = () => new Date().toISOString()
const staleIso = () => new Date(Date.now() - ONLINE_MAX_AGE_MS - 60_000).toISOString()
const ancientIso = () => new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()

describe('getDeviceStatus / isDeviceOnline', () => {
  it('returns unknown/false for null', () => {
    expect(getDeviceStatus(null)).toBe('unknown')
    expect(isDeviceOnline(null)).toBe(false)
  })

  it('returns inactive when deactivated', () => {
    expect(
      getDeviceStatus({
        is_active: false,
        last_seen_at: freshIso(),
        error_message: null,
      }),
    ).toBe('inactive')
    expect(isDeviceOnline({ is_active: false, last_seen_at: freshIso() })).toBe(false)
  })

  it('returns offline when never seen or error', () => {
    expect(
      getDeviceStatus({ is_active: true, last_seen_at: null, error_message: null }),
    ).toBe('offline')
    expect(
      getDeviceStatus({
        is_active: true,
        last_seen_at: freshIso(),
        error_message: 'connection refused',
      }),
    ).toBe('offline')
  })

  it('returns online when active, freshly seen, no error', () => {
    expect(
      getDeviceStatus({
        is_active: true,
        last_seen_at: freshIso(),
        error_message: null,
      }),
    ).toBe('online')
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: freshIso(),
        error_message: null,
      }),
    ).toBe(true)
  })

  it('returns stale when last_seen aged but within hour', () => {
    expect(
      getDeviceStatus({
        is_active: true,
        last_seen_at: staleIso(),
        error_message: null,
      }),
    ).toBe('stale')
    expect(isDeviceOnline({ is_active: true, last_seen_at: staleIso() })).toBe(false)
  })

  it('returns offline when last_seen is very old', () => {
    expect(
      getDeviceStatus({
        is_active: true,
        last_seen_at: ancientIso(),
        error_message: null,
      }),
    ).toBe('offline')
  })

  it('labels map correctly', () => {
    expect(deviceStatusLabel('online')).toBe('Online')
    expect(deviceStatusLabel('inactive')).toBe('Inactive')
    expect(deviceStatusLabel('stale')).toBe('Stale')
  })
})

describe('unwrapList / paths / labels', () => {
  it('unwraps paginated and bare lists', () => {
    expect(unwrapList(null)).toEqual([])
    expect(unwrapList([1])).toEqual([1])
    expect(unwrapList({ results: [1, 2] })).toEqual([1, 2])
  })

  it('builds paths and labels', () => {
    expect(deviceDetailPath('bitaxe', 'x')).toBe('/devices/bitaxe/x')
    expect(legacyDevicePath('avalon', 'a')).toBe('/avalon/device/a')
    expect(makeLabel('bitaxe')).toBe('Bitaxe')
    expect(makeLabel('custom')).toBe('Custom')
  })
})
