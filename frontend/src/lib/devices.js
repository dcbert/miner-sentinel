/**
 * Helpers for unified multi-make device API.
 */

export const MAKE_LABELS = {
  bitaxe: 'Bitaxe',
  avalon: 'Avalon',
  nmaxe: 'NMAxe',
  nerdnos: 'NerdNOS',
  antminer: 'Antminer',
  whatsminer: 'Whatsminer',
  braiins: 'Braiins',
  goldshell: 'Goldshell',
  iceriver: 'IceRiver',
  other: 'Other',
}

/** Makes selectable when adding a device in Settings. */
export const SUPPORTED_MAKES = [
  { value: 'bitaxe', label: 'Bitaxe' },
  { value: 'avalon', label: 'Avalon' },
  { value: 'nmaxe', label: 'NMAxe / NMAxeGamma' },
  { value: 'nerdnos', label: 'NerdNOS' },
]

/** Max age of last_seen_at to still count as online (≈ a few poll cycles). */
export const ONLINE_MAX_AGE_MS = 10 * 60 * 1000

/** After this, still enabled but data is stale (shown as Stale, not Online). */
export const STALE_MAX_AGE_MS = 60 * 60 * 1000

export function makeLabel(make) {
  return MAKE_LABELS[make] || (make ? make.charAt(0).toUpperCase() + make.slice(1) : 'Unknown')
}

/** Normalize paginated or bare list responses. */
export function unwrapList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
}

/**
 * Operational status for UI:
 * - online: enabled, recent successful poll
 * - stale: enabled, last seen aged but not failed
 * - offline: enabled but unreachable / error / never seen / very old
 * - inactive: collection disabled in registry
 * - unknown: missing device
 *
 * @param {object|null|undefined} device
 * @param {Date} [now]
 * @returns {'online'|'stale'|'offline'|'inactive'|'unknown'}
 */
export function getDeviceStatus(device, now = new Date()) {
  if (!device) return 'unknown'
  if (device.is_active === false) return 'inactive'
  if (device.error_message) return 'offline'
  if (!device.last_seen_at) return 'offline'
  const lastSeen = new Date(device.last_seen_at).getTime()
  if (!Number.isFinite(lastSeen)) return 'offline'
  const age = now.getTime() - lastSeen
  if (age <= ONLINE_MAX_AGE_MS) return 'online'
  if (age <= STALE_MAX_AGE_MS) return 'stale'
  return 'offline'
}

export function deviceStatusLabel(status) {
  const map = {
    online: 'Online',
    stale: 'Stale',
    offline: 'Offline',
    inactive: 'Inactive',
    unknown: 'Unknown',
  }
  return map[status] || 'Unknown'
}

/**
 * Whether a device is currently reachable (fresh last_seen, no error).
 *
 * `is_active` only means "enabled for collection". Reachability comes from the
 * collector: successful polls clear `error_message` and set `last_seen_at`.
 *
 * @param {object|null|undefined} device
 * @returns {boolean}
 */
export function isDeviceOnline(device) {
  return getDeviceStatus(device) === 'online'
}

/** Temperature status bands for home ASICs (°C). */
export function tempStatus(celsius) {
  const t = Number(celsius)
  if (!Number.isFinite(t)) return 'normal'
  if (t > 70) return 'danger'
  if (t > 60) return 'warning'
  return 'normal'
}

export function tempStatusClass(celsius) {
  const s = tempStatus(celsius)
  if (s === 'danger') return 'text-status-critical-fg'
  if (s === 'warning') return 'text-status-warning-fg'
  return 'text-status-online-fg'
}

/** Path to device detail page. */
export function deviceDetailPath(make, deviceId) {
  return `/devices/${make}/${deviceId}`
}

/** Legacy path redirects still work; prefer unified path. */
export function legacyDevicePath(make, deviceId) {
  if (make === 'avalon') return `/avalon/device/${deviceId}`
  return `/bitaxe/device/${deviceId}`
}
