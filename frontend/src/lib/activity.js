/**
 * Activity / alert event classification and display helpers.
 * Problems need attention; highlights are celebrations / news (not "open problems").
 */
import {
  Award,
  Fan,
  Power,
  RefreshCw,
  Server,
  Thermometer,
  TrendingDown,
  Wifi,
  WifiOff,
  Wrench,
  Zap,
} from 'lucide-react'

/** Event types that are fleet issues needing attention */
export const PROBLEM_EVENT_TYPES = new Set([
  'device_offline',
  'hashrate_stagnation',
  'auto_restart',
  'temperature_high',
  'fan_dead',
  'pool_down',
  'collector_down',
  'expected_hashrate_drop',
])

/** Celebrations / recovery news — never framed as problems */
export const HIGHLIGHT_EVENT_TYPES = new Set([
  'best_difficulty',
  'device_online',
])

export function isProblemEvent(ev) {
  if (!ev) return false
  if (HIGHLIGHT_EVENT_TYPES.has(ev.event_type)) return false
  if (ev.event_type?.startsWith('user_')) return false
  if (ev.severity === 'info') return false
  return PROBLEM_EVENT_TYPES.has(ev.event_type) || ev.severity === 'warn' || ev.severity === 'critical'
}

export function isHighlightEvent(ev) {
  if (!ev) return false
  if (HIGHLIGHT_EVENT_TYPES.has(ev.event_type)) return true
  if (ev.event_type?.startsWith('user_')) return true
  return ev.severity === 'info' && !PROBLEM_EVENT_TYPES.has(ev.event_type)
}

const EVENT_META = {
  device_offline: {
    label: 'Device offline',
    icon: WifiOff,
    tone: 'critical',
  },
  device_online: {
    label: 'Back online',
    icon: Wifi,
    tone: 'success',
  },
  hashrate_stagnation: {
    label: 'Hashrate stagnation',
    icon: TrendingDown,
    tone: 'warn',
  },
  auto_restart: {
    label: 'Auto-restart',
    icon: Power,
    tone: 'warn',
  },
  best_difficulty: {
    label: 'New best difficulty',
    icon: Award,
    tone: 'success',
  },
  temperature_high: {
    label: 'High temperature',
    icon: Thermometer,
    tone: 'critical',
  },
  fan_dead: {
    label: 'Fan not spinning',
    icon: Fan,
    tone: 'critical',
  },
  pool_down: {
    label: 'Pool unavailable',
    icon: Server,
    tone: 'warn',
  },
  collector_down: {
    label: 'Collector unhealthy',
    icon: Server,
    tone: 'critical',
  },
  expected_hashrate_drop: {
    label: 'Below expected hashrate',
    icon: TrendingDown,
    tone: 'warn',
  },
  user_reboot: {
    label: 'Reboot sent',
    icon: RefreshCw,
    tone: 'neutral',
  },
  fan_changed: {
    label: 'Fan updated',
    icon: Fan,
    tone: 'neutral',
  },
}

const TONE_STYLES = {
  critical: {
    badge: 'bg-red-500/10 text-red-600 border-red-500/20 dark:text-red-400',
    strip: 'border-red-500/30 bg-red-500/5',
    icon: 'text-red-500',
  },
  warn: {
    badge: 'bg-amber-500/10 text-amber-700 border-amber-500/20 dark:text-amber-400',
    strip: 'border-amber-500/30 bg-amber-500/5',
    icon: 'text-amber-500',
  },
  success: {
    badge: 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:text-emerald-400',
    strip: 'border-emerald-500/30 bg-emerald-500/5',
    icon: 'text-emerald-500',
  },
  neutral: {
    badge: 'bg-muted text-muted-foreground border-border',
    strip: 'border-border bg-muted/30',
    icon: 'text-muted-foreground',
  },
  info: {
    badge: 'bg-sky-500/10 text-sky-700 border-sky-500/20 dark:text-sky-400',
    strip: 'border-sky-500/30 bg-sky-500/5',
    icon: 'text-sky-500',
  },
}

export function getEventMeta(eventType) {
  if (EVENT_META[eventType]) return EVENT_META[eventType]
  if (eventType?.startsWith('user_')) {
    return { label: eventType.replace(/^user_/, '').replace(/_/g, ' '), icon: Wrench, tone: 'neutral' }
  }
  return {
    label: (eventType || 'event').replace(/_/g, ' '),
    icon: Zap,
    tone: 'info',
  }
}

export function getToneStyles(tone) {
  return TONE_STYLES[tone] || TONE_STYLES.info
}

export function severityTone(severity, eventType) {
  if (HIGHLIGHT_EVENT_TYPES.has(eventType) || eventType === 'best_difficulty') return 'success'
  if (severity === 'critical') return 'critical'
  if (severity === 'warn') return 'warn'
  if (severity === 'info') return 'info'
  return 'neutral'
}
