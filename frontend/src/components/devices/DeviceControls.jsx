/**
 * Per-device Controls tab: capability-gated reboot, fan, freq, voltage,
 * pause/resume, pool change, Avalon workmode. Confirm dialogs for destructive actions.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Fan,
  Gauge,
  Pause,
  Play,
  Power,
  RefreshCw,
  SlidersHorizontal,
  Zap,
} from 'lucide-react'

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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectOption } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { toast } from '@/components/ui/toaster'
import api from '@/lib/api'
import { isDeviceOnline } from '@/lib/devices'
import { cn } from '@/lib/utils'

const WORKMODE_OPTIONS = [
  { value: 0, label: 'Low', hint: 'Lowest power / cooler' },
  { value: 1, label: 'Mid', hint: 'Balanced' },
  { value: 2, label: 'High', hint: 'Max hashrate' },
]

const CUSTOM = '__custom__'

/** Common AxeOS / Bitaxe frequency presets (MHz) */
const FREQUENCY_PRESETS = [400, 425, 450, 475, 485, 500, 525, 550, 575, 600]

/** Common core voltage presets (mV) */
const VOLTAGE_PRESETS = [1000, 1050, 1100, 1125, 1150, 1160, 1180, 1200, 1225, 1250]

function FanSpeedSlider({
  id,
  value,
  onChange,
  min,
  max,
  disabled,
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>Manual speed</Label>
        <span className="tabular-nums text-sm font-medium text-foreground">{value}%</span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
        className={cn(
          'h-2 w-full cursor-pointer appearance-none rounded-full bg-muted',
          'accent-primary disabled:cursor-not-allowed disabled:opacity-50',
          '[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
          '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full',
          '[&::-webkit-slider-thumb]:bg-primary',
          '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4',
          '[&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0',
          '[&::-moz-range-thumb]:bg-primary',
        )}
      />
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>
    </div>
  )
}

function PresetOrCustom({
  id,
  label,
  unit,
  presets,
  value,
  onChange,
  disabled,
  placeholder,
}) {
  const presetSet = useMemo(() => new Set(presets.map(String)), [presets])
  const valueIsPreset = value !== '' && presetSet.has(String(value))
  const [forceCustom, setForceCustom] = useState(false)
  const showCustom = forceCustom || (value !== '' && !valueIsPreset)
  const selectValue = showCustom ? CUSTOM : valueIsPreset ? String(value) : ''

  // If external value becomes a known preset, drop custom mode
  useEffect(() => {
    if (valueIsPreset) setForceCustom(false)
  }, [valueIsPreset])

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <Label htmlFor={`${id}-preset`}>{label}</Label>
        <Select
          id={`${id}-preset`}
          value={selectValue}
          disabled={disabled}
          onValueChange={(v) => {
            if (v === CUSTOM) {
              setForceCustom(true)
              if (valueIsPreset) onChange('')
              return
            }
            setForceCustom(false)
            onChange(v)
          }}
        >
          <SelectOption value="" disabled>
            Choose a preset…
          </SelectOption>
          {presets.map((p) => (
            <SelectOption key={p} value={String(p)}>
              {p} {unit}
            </SelectOption>
          ))}
          <SelectOption value={CUSTOM}>Custom…</SelectOption>
        </Select>
      </div>
      {showCustom && (
        <div className="space-y-1.5">
          <Label htmlFor={`${id}-custom`}>Custom {unit}</Label>
          <Input
            id={`${id}-custom`}
            type="number"
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  )
}

export default function DeviceControls({ make, deviceId, device }) {
  const online = isDeviceOnline(device)
  const [caps, setCaps] = useState(null)
  const [loadingCaps, setLoadingCaps] = useState(true)
  const [busy, setBusy] = useState(null)

  const fanMin = make === 'avalon' ? 15 : 0
  const [fanAuto, setFanAuto] = useState(true)
  const [fanPercent, setFanPercent] = useState(80)
  const [frequency, setFrequency] = useState('')
  const [voltageMv, setVoltageMv] = useState('')
  const [poolUrl, setPoolUrl] = useState('')
  const [poolUser, setPoolUser] = useState('')
  const [poolPassword, setPoolPassword] = useState('')
  const [workmode, setWorkmode] = useState(1)

  const [confirm, setConfirm] = useState(null) // { title, description, run }

  useEffect(() => {
    let cancelled = false
    async function loadCaps() {
      try {
        setLoadingCaps(true)
        const res = await api.get(`/api/devices/${make}/${deviceId}/capabilities/`)
        if (!cancelled) setCaps(res.data?.capabilities || {})
      } catch (err) {
        console.error(err)
        if (!cancelled) {
          setCaps({})
          toast({ title: 'Could not load control capabilities', variant: 'destructive' })
        }
      } finally {
        if (!cancelled) setLoadingCaps(false)
      }
    }
    loadCaps()
    return () => { cancelled = true }
  }, [make, deviceId])

  // Prefill from device telemetry when present
  useEffect(() => {
    const details = device?.latest_system?.details || device?.system_info?.details || {}
    const raw = details.WORKMODE ?? details.workmode ?? details.WorkMode
    if (raw !== undefined && raw !== null && raw !== '') {
      const n = parseInt(String(raw).replace(/[^\d-]/g, ''), 10)
      if (n === 0 || n === 1 || n === 2) setWorkmode(n)
    }

    const hw = device?.latest_hardware || {}
    const sys = device?.latest_system || {}
    const freq = hw.frequency_mhz ?? sys.frequency
    if (freq != null && freq !== '' && Number(freq) > 0) {
      setFrequency(String(Math.round(Number(freq))))
    }
    const mv =
      sys.core_voltage ??
      sys.coreVoltage ??
      (hw.voltage != null && hw.voltage < 50 ? Math.round(Number(hw.voltage) * 1000) : hw.voltage)
    if (mv != null && mv !== '' && Number(mv) > 0) {
      setVoltageMv(String(Math.round(Number(mv))))
    }

    const fanPct = hw.fan_speed_percent ?? hw.fanspeed ?? details.fanspeed
    if (fanPct != null && Number(fanPct) >= 0) {
      const pct = Math.max(fanMin, Math.min(100, Math.round(Number(fanPct))))
      setFanPercent(pct)
    }
  }, [device, fanMin])

  const disabled = !online || !!busy

  async function runControl(action, params = {}) {
    setBusy(action)
    try {
      const res = await api.post(`/api/devices/${make}/${deviceId}/control/`, {
        action,
        params,
      })
      toast({
        title: `${action} succeeded`,
        description: res.data?.message || 'Command sent to device',
      })
      return true
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        'Control request failed'
      toast({ title: `${action} failed`, description: String(msg), variant: 'destructive' })
      return false
    } finally {
      setBusy(null)
    }
  }

  function requestConfirm({ title, description, action, params }) {
    setConfirm({
      title,
      description,
      run: async () => {
        setConfirm(null)
        await runControl(action, params)
      },
    })
  }

  if (loadingCaps) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-10 text-sm text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Loading controls…
        </CardContent>
      </Card>
    )
  }

  const c = caps || {}
  const anyControl = Object.values(c).some(Boolean)

  return (
    <div className="space-y-4 sm:space-y-5">
      <div className="rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
        <p className="text-sm font-medium">Remote controls</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Capability-gated actions for this firmware. Destructive changes ask for confirmation;
          every action is written to Activity.
        </p>
      </div>

      {!online && (
        <div
          className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300"
          role="status"
        >
          Device offline — controls stay disabled until the next successful poll.
        </div>
      )}

      {!anyControl && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-base">No controls available</CardTitle>
            <CardDescription>
              This make/firmware does not expose remote control APIs yet.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
        {c.reboot && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10 text-red-500">
                  <Power className="h-4 w-4" />
                </span>
                Reboot
              </CardTitle>
              <CardDescription>Restart the miner firmware / cgminer process.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                disabled={disabled}
                onClick={() =>
                  requestConfirm({
                    title: 'Reboot device?',
                    description: `${device?.device_name || device?.name || deviceId} will restart and stop hashing briefly.`,
                    action: 'reboot',
                    params: {},
                  })
                }
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${busy === 'reboot' ? 'animate-spin' : ''}`} />
                Reboot
              </Button>
            </CardContent>
          </Card>
        )}

        {c.fan && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 text-sky-500">
                  <Fan className="h-4 w-4" />
                </span>
                Fan
              </CardTitle>
              <CardDescription>
                Auto fan or fixed speed ({fanMin}–100%).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <Label htmlFor="fan-auto">Auto fan</Label>
                <Switch
                  id="fan-auto"
                  checked={fanAuto}
                  onCheckedChange={(on) => {
                    setFanAuto(on)
                    if (!on && fanPercent < fanMin) setFanPercent(fanMin)
                  }}
                  disabled={disabled}
                />
              </div>
              {!fanAuto && (
                <FanSpeedSlider
                  id="fan-pct"
                  value={Math.max(fanMin, Math.min(100, fanPercent))}
                  min={fanMin}
                  max={100}
                  disabled={disabled}
                  onChange={setFanPercent}
                />
              )}
              <Button
                disabled={disabled}
                onClick={() =>
                  runControl(
                    'fan',
                    fanAuto
                      ? { auto: true }
                      : { auto: false, percent: Math.max(fanMin, Math.min(100, fanPercent)) },
                  )
                }
              >
                Apply fan
              </Button>
            </CardContent>
          </Card>
        )}

        {c.frequency && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10 text-violet-500">
                  <Gauge className="h-4 w-4" />
                </span>
                Frequency
              </CardTitle>
              <CardDescription>Pick a common MHz preset, or enter a custom value.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <PresetOrCustom
                id="frequency"
                label="Frequency"
                unit="MHz"
                presets={FREQUENCY_PRESETS}
                value={frequency}
                onChange={setFrequency}
                disabled={disabled}
                placeholder="e.g. 490"
              />
              <Button
                disabled={disabled || !frequency || Number.isNaN(Number(frequency))}
                onClick={() =>
                  requestConfirm({
                    title: `Set frequency to ${frequency} MHz?`,
                    description: 'Overclocking can raise temps and instability. Apply only if you know your chip limits.',
                    action: 'frequency',
                    params: { mhz: Number(frequency) },
                  })
                }
              >
                Apply frequency
              </Button>
            </CardContent>
          </Card>
        )}

        {c.voltage && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
                  <Zap className="h-4 w-4" />
                </span>
                Voltage
              </CardTitle>
              <CardDescription>Pick a common mV preset, or enter a custom value.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <PresetOrCustom
                id="voltage"
                label="Core voltage"
                unit="mV"
                presets={VOLTAGE_PRESETS}
                value={voltageMv}
                onChange={setVoltageMv}
                disabled={disabled}
                placeholder="e.g. 1175"
              />
              <Button
                disabled={disabled || !voltageMv || Number.isNaN(Number(voltageMv))}
                onClick={() =>
                  requestConfirm({
                    title: `Set core voltage to ${voltageMv} mV?`,
                    description: 'Incorrect voltage can damage hardware. Double-check before applying.',
                    action: 'voltage',
                    params: { millivolts: Number(voltageMv) },
                  })
                }
              >
                Apply voltage
              </Button>
            </CardContent>
          </Card>
        )}

        {(c.pause || c.resume) && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Pause className="h-4 w-4" />
                </span>
                Pause / Resume
              </CardTitle>
              <CardDescription>Standby hashing without a full reboot (AxeOS).</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {c.pause && (
                <Button variant="secondary" disabled={disabled} onClick={() => runControl('pause')}>
                  <Pause className="mr-2 h-4 w-4" />
                  Pause
                </Button>
              )}
              {c.resume && (
                <Button disabled={disabled} onClick={() => runControl('resume')}>
                  <Play className="mr-2 h-4 w-4" />
                  Resume
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {c.workmode && (
          <Card className="border-border/70">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
                  <SlidersHorizontal className="h-4 w-4" />
                </span>
                Avalon workmode
              </CardTitle>
              <CardDescription>
                One-click Low / Mid / High power presets.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-3">
                {WORKMODE_OPTIONS.map((opt) => (
                  <Button
                    key={opt.value}
                    variant={workmode === opt.value ? 'default' : 'outline'}
                    className="h-auto flex-col items-start gap-0.5 py-3"
                    disabled={disabled}
                    onClick={() => {
                      setWorkmode(opt.value)
                      requestConfirm({
                        title: `Set Avalon workmode to ${opt.label}?`,
                        description: `${opt.hint}. This changes the miner power profile immediately.`,
                        action: 'workmode',
                        params: { mode: opt.value },
                      })
                    }}
                  >
                    <span className="font-semibold">{opt.label}</span>
                    <span className="text-xs font-normal opacity-80">{opt.hint}</span>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {c.set_pool && (
          <Card className="border-border/70 lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Pool (stratum)</CardTitle>
              <CardDescription>
                Updates primary stratum settings and restarts the device to apply.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="pool-url">Stratum URL</Label>
                <Input
                  id="pool-url"
                  placeholder="stratum+tcp://host:port"
                  value={poolUrl}
                  onChange={(e) => setPoolUrl(e.target.value)}
                  disabled={disabled}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pool-user">Worker / user</Label>
                <Input
                  id="pool-user"
                  value={poolUser}
                  onChange={(e) => setPoolUser(e.target.value)}
                  disabled={disabled}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="pool-pass">Password (optional)</Label>
                <Input
                  id="pool-pass"
                  type="password"
                  value={poolPassword}
                  onChange={(e) => setPoolPassword(e.target.value)}
                  disabled={disabled}
                />
              </div>
              <div className="flex items-end">
                <Button
                  variant="destructive"
                  disabled={disabled || !poolUrl || !poolUser}
                  onClick={() =>
                    requestConfirm({
                      title: 'Change pool and restart?',
                      description: `Primary stratum will become ${poolUrl}. Device will reboot.`,
                      action: 'set_pool',
                      params: {
                        stratum_url: poolUrl,
                        stratum_user: poolUser,
                        stratum_password: poolPassword || undefined,
                        restart: true,
                      },
                    })
                  }
                >
                  Apply pool
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Dialog open={!!confirm} onOpenChange={(open) => !open && setConfirm(null)}>
        <DialogContent onClose={() => setConfirm(null)}>
          <DialogHeader>
            <DialogTitle>{confirm?.title}</DialogTitle>
            <DialogDescription>{confirm?.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirm?.run?.()}
            >
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
