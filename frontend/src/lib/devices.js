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

/** Path to device detail page. */
export function deviceDetailPath(make, deviceId) {
  return `/devices/${make}/${deviceId}`
}

/** Legacy path redirects still work; prefer unified path. */
export function legacyDevicePath(make, deviceId) {
  if (make === 'avalon') return `/avalon/device/${deviceId}`
  return `/bitaxe/device/${deviceId}`
}
