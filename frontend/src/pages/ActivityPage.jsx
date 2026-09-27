/**
 * Activity — alert journal: problems needing attention vs highlights (records, recoveries).
 */
import EmptyState from '@/components/feedback/EmptyState'
import ErrorState from '@/components/feedback/ErrorState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardTitle } from '@/components/ui/card'
import {
  getEventMeta,
  getToneStyles,
  isHighlightEvent,
  severityTone,
} from '@/lib/activity'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/formatters'
import {
  Award,
  Bell,
  Check,
  Clock,
  Loader2,
  Moon,
  RefreshCw,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const FILTERS = [
  { id: 'problems', label: 'Needs attention', open: true, kind: 'problem' },
  { id: 'highlights', label: 'Highlights', open: false, kind: 'highlight' },
  { id: 'all', label: 'All', open: false, kind: 'all' },
]

export default function ActivityPage() {
  const [events, setEvents] = useState([])
  const [openCount, setOpenCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('problems')
  const [acting, setActing] = useState(null)

  const active = FILTERS.find((f) => f.id === filter) || FILTERS[0]

  const fetchEvents = useCallback(async () => {
    try {
      setError(null)
      const res = await api.get('/api/activity/', {
        params: {
          open: active.open ? 'true' : 'false',
          kind: active.kind,
          limit: 100,
        },
      })
      setEvents(res.data?.results || [])
      setOpenCount(res.data?.open_count ?? 0)
    } catch (err) {
      console.error(err)
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [active.open, active.kind])

  useEffect(() => {
    setLoading(true)
    fetchEvents()
    const id = setInterval(fetchEvents, 60000)
    return () => clearInterval(id)
  }, [fetchEvents])

  const act = async (id, action, body) => {
    setActing(`${id}-${action}`)
    try {
      await api.post(`/api/activity/${id}/${action}/`, body || {})
      await fetchEvents()
    } catch (err) {
      console.error(err)
    } finally {
      setActing(null)
    }
  }

  if (loading && !events.length && !error) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading activity…
      </div>
    )
  }

  if (error && !events.length) {
    return (
      <ErrorState
        title="Unable to load activity"
        description="Could not load the alert journal."
        onRetry={() => {
          setLoading(true)
          fetchEvents()
        }}
      />
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">
            {openCount === 0
              ? 'No issues need attention right now'
              : `${openCount} issue${openCount === 1 ? '' : 's'} need${openCount === 1 ? 's' : ''} attention`}
            <span className="text-muted-foreground/70"> · synced with Telegram / Discord / ntfy</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <Button
              key={f.id}
              variant={filter === f.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(f.id)}
            >
              {f.id === 'highlights' && <Award className="mr-1.5 h-3.5 w-3.5" />}
              {f.label}
              {f.id === 'problems' && openCount > 0 ? (
                <Badge variant="secondary" className="ml-1.5 h-5 px-1.5 text-[10px]">
                  {openCount}
                </Badge>
              ) : null}
            </Button>
          ))}
          <Button variant="outline" size="sm" onClick={() => fetchEvents()}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>
      </div>

      {events.length === 0 ? (
        <EmptyState
          icon={filter === 'highlights' ? Award : Bell}
          title={
            filter === 'problems'
              ? 'All clear'
              : filter === 'highlights'
                ? 'No highlights yet'
                : 'No activity yet'
          }
          description={
            filter === 'problems'
              ? 'Fleet looks healthy. Records and recoveries show under Highlights.'
              : filter === 'highlights'
                ? 'New best shares and recoveries will appear here.'
                : 'Alerts from collectors and control actions will show up here.'
          }
        />
      ) : (
        <div className="space-y-2.5">
          {events.map((ev) => {
            const meta = getEventMeta(ev.event_type)
            const tone = severityTone(ev.severity, ev.event_type)
            const styles = getToneStyles(tone)
            const Icon = meta.icon
            const isOpen = ev.is_open
            const highlight = isHighlightEvent(ev)

            return (
              <Card
                key={ev.id}
                className={cn(
                  'overflow-hidden border-border/70 transition-colors',
                  highlight && 'border-emerald-500/20 bg-emerald-500/[0.03]',
                  isOpen && tone === 'critical' && 'border-red-500/25',
                  isOpen && tone === 'warn' && 'border-amber-500/25',
                )}
              >
                <div className="flex gap-3 p-4 sm:gap-4">
                  <div
                    className={cn(
                      'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border',
                      styles.badge,
                    )}
                  >
                    <Icon className={cn('h-4.5 w-4.5 h-4 w-4', styles.icon)} />
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge variant="outline" className={cn('capitalize', styles.badge)}>
                            {highlight ? 'Highlight' : meta.label}
                          </Badge>
                          {!highlight && (
                            <Badge variant="outline" className="text-[10px] capitalize text-muted-foreground">
                              {ev.severity}
                            </Badge>
                          )}
                          {ev.is_muted && (
                            <Badge variant="outline" className="text-muted-foreground">
                              <Moon className="mr-1 h-3 w-3" />
                              Snoozed
                            </Badge>
                          )}
                          {!isOpen && !highlight && (
                            <Badge variant="outline" className="text-muted-foreground">
                              Closed
                            </Badge>
                          )}
                        </div>
                        <CardTitle className="text-base font-medium leading-snug">
                          {ev.message}
                        </CardTitle>
                        <CardDescription className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatRelativeTime(ev.created_at)}
                          </span>
                          {ev.device_name && (
                            <Link
                              to={
                                ev.device_make && ev.device_key
                                  ? `/devices/${ev.device_make}/${ev.device_key}`
                                  : '/mining'
                              }
                              className="text-primary hover:underline"
                            >
                              {ev.device_name}
                              {ev.device_make ? ` · ${ev.device_make}` : ''}
                            </Link>
                          )}
                        </CardDescription>
                      </div>
                      {isOpen && !highlight && (
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={acting === `${ev.id}-snooze`}
                            onClick={() => act(ev.id, 'snooze', { minutes: 60 })}
                          >
                            {acting === `${ev.id}-snooze` ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <>
                                <Moon className="mr-1 h-3.5 w-3.5" />
                                Snooze 1h
                              </>
                            )}
                          </Button>
                          <Button
                            size="sm"
                            disabled={acting === `${ev.id}-acknowledge`}
                            onClick={() => act(ev.id, 'acknowledge')}
                          >
                            {acting === `${ev.id}-acknowledge` ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <>
                                <Check className="mr-1 h-3.5 w-3.5" />
                                Done
                              </>
                            )}
                          </Button>
                        </div>
                      )}
                    </div>
                    {ev.payload && Object.keys(ev.payload).length > 0 && filter === 'all' && (
                      <CardContent className="p-0">
                        <pre className="overflow-x-auto rounded-md bg-muted/40 p-2 text-[10px] text-muted-foreground">
                          {JSON.stringify(ev.payload, null, 0)}
                        </pre>
                      </CardContent>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
