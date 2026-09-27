/**
 * Advisor panel: ranked next actions with one-click control hooks.
 */
import {
  AlertTriangle,
  Lightbulb,
  Loader2,
  Sparkles,
  Thermometer,
  WifiOff,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from '@/components/ui/toaster'
import api from '@/lib/api'
import { deviceDetailPath } from '@/lib/devices'
import { cn } from '@/lib/utils'

const KIND_META = {
  offline: { icon: WifiOff, tone: 'text-red-500 bg-red-500/10 border-red-500/20' },
  temperature: { icon: Thermometer, tone: 'text-orange-500 bg-orange-500/10 border-orange-500/20' },
  thermal: { icon: Thermometer, tone: 'text-orange-500 bg-orange-500/10 border-orange-500/20' },
  default: { icon: AlertTriangle, tone: 'text-amber-500 bg-amber-500/10 border-amber-500/20' },
}

function kindMeta(kind) {
  const key = Object.keys(KIND_META).find((k) => (kind || '').includes(k))
  return KIND_META[key] || KIND_META.default
}

export default function AdvisorPanel() {
  const navigate = useNavigate()
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(null)
  const [confirm, setConfirm] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.get('/api/advisor/')
      setSuggestions(res.data?.suggestions || [])
    } catch (err) {
      console.error(err)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function runControl(device, control) {
    if (!device?.make || !device?.device_id || !control?.action) return
    const key = `${device.make}:${device.device_id}:${control.action}`
    setBusy(key)
    try {
      await api.post(`/api/devices/${device.make}/${device.device_id}/control/`, {
        action: control.action,
        params: control.params || {},
      })
      toast({ title: `${control.action} sent`, description: device.name })
      await load()
    } catch (err) {
      toast({
        title: 'Control failed',
        description: err.response?.data?.error || err.message,
        variant: 'destructive',
      })
    } finally {
      setBusy(null)
    }
  }

  if (loading && suggestions.length === 0) {
    return null
  }

  if (!suggestions.length) {
    return (
      <Card className="border-dashed border-border/70 bg-muted/20">
        <CardContent className="flex items-center gap-3 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-medium">Advisor has nothing urgent</p>
            <p className="text-xs text-muted-foreground">
              Suggestions appear here when devices need a reboot, cooler fans, or other attention.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Lightbulb className="h-4 w-4 text-amber-500 sm:h-5 sm:w-5" />
              Advisor
            </CardTitle>
            <CardDescription className="mt-1">
              Prioritized next actions · {suggestions.length} suggestion
              {suggestions.length === 1 ? '' : 's'}
            </CardDescription>
          </div>
          <Badge variant="secondary" className="shrink-0">
            {suggestions.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {suggestions.slice(0, 6).map((s, idx) => {
          const meta = kindMeta(s.kind)
          const Icon = meta.icon
          return (
            <div
              key={`${s.kind}-${s.device?.device_id || 'global'}-${idx}`}
              className="flex flex-col gap-3 rounded-xl border border-border/60 bg-card/50 p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex min-w-0 gap-3">
                <div
                  className={cn(
                    'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border',
                    meta.tone,
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-snug">{s.title}</p>
                  {s.detail && (
                    <p className="mt-0.5 text-xs text-muted-foreground">{s.detail}</p>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2 shrink-0 sm:justify-end">
                {s.href && (
                  <Button size="sm" variant="outline" onClick={() => navigate(s.href)}>
                    Open
                  </Button>
                )}
                {s.device && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => navigate(deviceDetailPath(s.device.make, s.device.device_id))}
                  >
                    Details
                  </Button>
                )}
                {(s.actions || []).map((a) => {
                  const key = `${s.device?.make}:${s.device?.device_id}:${a.control?.action}`
                  return (
                    <Button
                      key={a.label}
                      size="sm"
                      disabled={!!busy}
                      onClick={() => {
                        if (a.confirm) {
                          setConfirm({
                            title: a.label,
                            description: `${a.label} on ${s.device?.name || 'device'}?`,
                            run: () => runControl(s.device, a.control),
                          })
                        } else {
                          runControl(s.device, a.control)
                        }
                      }}
                    >
                      {busy === key ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
                      {a.label}
                    </Button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </CardContent>

      <Dialog open={!!confirm} onOpenChange={(open) => !open && setConfirm(null)}>
        <DialogContent onClose={() => setConfirm(null)}>
          <DialogHeader>
            <DialogTitle>{confirm?.title}</DialogTitle>
            <DialogDescription>{confirm?.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                const run = confirm?.run
                setConfirm(null)
                await run?.()
              }}
            >
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
