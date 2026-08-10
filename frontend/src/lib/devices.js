/**
 * Helpers for unified multi-make device API.
 */

export const MAKE_LABELS = {
  bitaxe: 'Bitaxe',
  avalon: 'Avalon',
  antminer: 'Antminer',
  whatsminer: 'Whatsminer',
  braiins: 'Braiins',
  goldshell: 'Goldshell',
  iceriver: 'IceRiver',
  other: 'Other',
}

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
 * Whether a device is currently reachable.
 *
 * `is_active` only means "enabled for collection". Reachability comes from the
 * collector: successful polls clear `error_message` and set `last_seen_at`;
 * failed polls set `error_message` and leave `last_seen_at` unchanged.
 *
 * @param {object|null|undefined} device
 * @returns {boolean}
 */
export function isDeviceOnline(device) {
  if (!device) return false
  if (device.is_active === false) return false
  if (device.error_message) return false
  if (!device.last_seen_at) return false
  const lastSeen = new Date(device.last_seen_at).getTime()
  return Number.isFinite(lastSeen)
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
