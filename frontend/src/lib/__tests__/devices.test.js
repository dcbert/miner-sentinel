import { describe, expect, it } from 'vitest'
import {
  deviceDetailPath,
  isDeviceOnline,
  legacyDevicePath,
  makeLabel,
  unwrapList,
} from '@/lib/devices'

describe('isDeviceOnline', () => {
  it('returns false for null/undefined', () => {
    expect(isDeviceOnline(null)).toBe(false)
    expect(isDeviceOnline(undefined)).toBe(false)
  })

  it('returns false when device is deactivated', () => {
    expect(
      isDeviceOnline({
        is_active: false,
        last_seen_at: '2026-07-23T12:00:00Z',
        error_message: null,
      }),
    ).toBe(false)
  })

  it('returns false when never successfully seen', () => {
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: null,
        error_message: null,
      }),
    ).toBe(false)
  })

  it('returns false when collector recorded an error (offline)', () => {
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: '2026-07-23T12:00:00Z',
        error_message: 'connection refused',
      }),
    ).toBe(false)
  })

  it('returns true when active, seen, and no error', () => {
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: '2026-07-23T12:00:00Z',
        error_message: null,
      }),
    ).toBe(true)
  })

  it('does not treat is_active alone as online (regression)', () => {
    // Active but never contacted / offline — previously UIs showed "Online"
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: null,
        error_message: 'timeout',
      }),
    ).toBe(false)
  })

  it('returns false for invalid last_seen_at', () => {
    expect(
      isDeviceOnline({
        is_active: true,
        last_seen_at: 'not-a-date',
        error_message: null,
      }),
    ).toBe(false)
  })
})

describe('unwrapList / paths / labels', () => {
  it('unwraps paginated and bare lists', () => {
    expect(unwrapList(null)).toEqual([])
    expect(unwrapList([1])).toEqual([1])
    expect(unwrapList({ results: [1, 2] })).toEqual([1, 2])
    expect(unwrapList({ other: true })).toEqual([])
  })

  it('builds paths and labels', () => {
    expect(deviceDetailPath('bitaxe', 'x')).toBe('/devices/bitaxe/x')
    expect(legacyDevicePath('avalon', 'a')).toBe('/avalon/device/a')
    expect(makeLabel('bitaxe')).toBe('Bitaxe')
    expect(makeLabel('nmaxe')).toBe('NMAxe')
    expect(makeLabel('nerdnos')).toBe('NerdNOS')
    expect(makeLabel('unknown-make')).toBe('Unknown-make')

  })
})
