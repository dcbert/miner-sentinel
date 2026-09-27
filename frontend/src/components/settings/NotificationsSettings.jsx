/**
 * Notifications management UI: channels (Telegram / Discord) + per-event rules.
 */
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import {
  AlertTriangle,
  Award,
  Bell,
  CheckCircle2,
  Edit,
  EyeOff,
  Fan,
  Loader2,
  MessageCircle,
  Moon,
  Power,
  RefreshCw,
  Send,
  Server,
  Thermometer,
  TrendingDown,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useMemo, useState } from 'react'

const ALERT_META = {
  device_offline: {
    icon: WifiOff,
    accent: 'text-red-500',
    bg: 'bg-red-500/10',
  },
  device_online: {
    icon: Wifi,
    accent: 'text-green-500',
    bg: 'bg-green-500/10',
  },
  hashrate_stagnation: {
    icon: AlertTriangle,
    accent: 'text-amber-500',
    bg: 'bg-amber-500/10',
  },
  auto_restart: {
    icon: Power,
    accent: 'text-orange-500',
    bg: 'bg-orange-500/10',
  },
  best_difficulty: {
    icon: Award,
    accent: 'text-yellow-500',
    bg: 'bg-yellow-500/10',
  },
  temperature_high: {
    icon: Thermometer,
    accent: 'text-red-500',
    bg: 'bg-red-500/10',
  },
  fan_dead: {
    icon: Fan,
    accent: 'text-orange-500',
    bg: 'bg-orange-500/10',
  },
  pool_down: {
    icon: Server,
    accent: 'text-amber-500',
    bg: 'bg-amber-500/10',
  },
  collector_down: {
    icon: Server,
    accent: 'text-red-500',
    bg: 'bg-red-500/10',
  },
  expected_hashrate_drop: {
    icon: TrendingDown,
    accent: 'text-amber-500',
    bg: 'bg-amber-500/10',
  },
}

const ALERT_ORDER = [
  'device_offline',
  'device_online',
  'temperature_high',
  'fan_dead',
  'expected_hashrate_drop',
  'hashrate_stagnation',
  'auto_restart',
  'pool_down',
  'collector_down',
  'best_difficulty',
]

export default function NotificationsSettings({
  settings,
  setSettings,
  onSave,
  saving,
}) {
  const [showTelegramToken, setShowTelegramToken] = useState(false)
  const [showDiscordWebhook, setShowDiscordWebhook] = useState(false)
  const [testing, setTesting] = useState(null) // 'telegram' | 'discord' | 'ntfy' | 'gotify' | 'webhook'
  const [testResult, setTestResult] = useState(null)
  const [showNtfyToken, setShowNtfyToken] = useState(false)
  const [showGotifyToken, setShowGotifyToken] = useState(false)
  const [showWebhookUrl, setShowWebhookUrl] = useState(false)

  const rules = settings.notification_rules || {}

  const enabledCount = useMemo(
    () => ALERT_ORDER.filter((k) => rules[k]?.enabled).length,
    [rules],
  )

  const channelsReady = useMemo(() => {
    const tg =
      settings.telegram_enabled &&
      (settings.telegram_bot_token_configured || settings.telegram_bot_token) &&
      settings.telegram_chat_id
    const dc =
      settings.discord_enabled &&
      (settings.discord_webhook_url_configured || settings.discord_webhook_url)
    const ntfy = settings.ntfy_enabled && !!(settings.ntfy_url || '').trim()
    const gotify =
      settings.gotify_enabled &&
      !!(settings.gotify_url || '').trim() &&
      (settings.gotify_token_configured || settings.gotify_token)
    const webhook =
      settings.webhook_enabled &&
      (settings.webhook_url_configured || settings.webhook_url)
    return {
      telegram: !!tg,
      discord: !!dc,
      ntfy: !!ntfy,
      gotify: !!gotify,
      webhook: !!webhook,
    }
  }, [settings])

  const updateRule = (key, patch) => {
    setSettings({
      ...settings,
      notification_rules: {
        ...rules,
        [key]: {
          ...(rules[key] || {}),
          ...patch,
        },
      },
    })
  }

  const runTest = async (channel) => {
    setTesting(channel)
    setTestResult(null)
    try {
      let path
      let body = { force: true }
      if (channel === 'telegram') {
        path = '/api/settings/collector/test-telegram/'
        body = {
          force: true,
          telegram_bot_token: settings.telegram_bot_token || undefined,
          telegram_chat_id: settings.telegram_chat_id || undefined,
        }
      } else if (channel === 'discord') {
        path = '/api/settings/collector/test-discord/'
        body = {
          force: true,
          discord_webhook_url: settings.discord_webhook_url || undefined,
        }
      } else {
        path = '/api/settings/collector/test-push/'
        body = {
          force: true,
          channel,
          ntfy_url: settings.ntfy_url || undefined,
          ntfy_token: settings.ntfy_token || undefined,
          gotify_url: settings.gotify_url || undefined,
          gotify_token: settings.gotify_token || undefined,
          webhook_url: settings.webhook_url || undefined,
        }
      }
      const res = await api.post(path, body)
      setTestResult({
        ok: true,
        channel,
        message: res.data?.message || 'Test sent successfully',
      })
    } catch (err) {
      setTestResult({
        ok: false,
        channel,
        message:
          err.response?.data?.error ||
          err.response?.data?.detail ||
          'Test failed',
      })
    } finally {
      setTesting(null)
    }
  }

  const channelLabel = (ch) =>
    ({
      telegram: 'Telegram',
      discord: 'Discord',
      ntfy: 'ntfy',
      gotify: 'Gotify',
      webhook: 'Webhook',
    }[ch] || ch)

  return (
    <div className="space-y-6">
      {/* Overview strip */}
      <Card className="border-border/80">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-primary/10">
                <Bell className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-semibold tracking-tight">Notifications</h2>
                <p className="text-sm text-muted-foreground mt-0.5 max-w-xl">
                  Choose delivery channels and which fleet events should alert you.
                  Secrets stay on the server; leave token fields blank to keep existing values.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="font-normal">
                {enabledCount}/{ALERT_ORDER.length} alerts on
              </Badge>
              <Badge
                variant="outline"
                className={
                  channelsReady.telegram
                    ? 'bg-green-500/10 text-green-600 border-green-500/20'
                    : 'text-muted-foreground'
                }
              >
                Telegram {channelsReady.telegram ? 'ready' : 'off'}
              </Badge>
              <Badge
                variant="outline"
                className={
                  channelsReady.discord
                    ? 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20'
                    : 'text-muted-foreground'
                }
              >
                Discord {channelsReady.discord ? 'ready' : 'off'}
              </Badge>
              <Badge
                variant="outline"
                className={
                  channelsReady.ntfy
                    ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                    : 'text-muted-foreground'
                }
              >
                ntfy {channelsReady.ntfy ? 'ready' : 'off'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {testResult && (
        <Alert variant={testResult.ok ? 'default' : 'destructive'}>
          {testResult.ok ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          <AlertDescription>
            {channelLabel(testResult.channel)}: {testResult.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Channels */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Telegram */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-sky-500/10">
                  <Send className="h-4 w-4 text-sky-500" />
                </div>
                <div>
                  <CardTitle className="text-base">Telegram</CardTitle>
                  <CardDescription className="text-xs">Bot API messages</CardDescription>
                </div>
              </div>
              <Switch
                checked={!!settings.telegram_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, telegram_enabled: checked })
                }
                aria-label="Enable Telegram"
              />
            </div>
          </CardHeader>
          <CardContent className={`space-y-4 ${settings.telegram_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div className="space-y-2">
              <Label htmlFor="tg-token">Bot token</Label>
              {settings.telegram_bot_token_configured && !showTelegramToken ? (
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/40 text-sm">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Configured
                    </Badge>
                    <span className="ml-2 text-muted-foreground text-xs">Leave blank to keep</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setShowTelegramToken(true)}
                    title="Change token"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    id="tg-token"
                    type="password"
                    autoComplete="off"
                    placeholder="123456:ABC-DEF..."
                    value={settings.telegram_bot_token || ''}
                    onChange={(e) =>
                      setSettings({ ...settings, telegram_bot_token: e.target.value })
                    }
                  />
                  {settings.telegram_bot_token_configured && (
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => {
                        setShowTelegramToken(false)
                        setSettings({ ...settings, telegram_bot_token: '' })
                      }}
                    >
                      <EyeOff className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              )}
              <p className="text-[11px] text-muted-foreground">
                Create a bot with @BotFather, then paste the token here.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tg-chat">Chat ID</Label>
              <Input
                id="tg-chat"
                placeholder="e.g. 123456789"
                value={settings.telegram_chat_id || ''}
                onChange={(e) =>
                  setSettings({ ...settings, telegram_chat_id: e.target.value })
                }
              />
              <p className="text-[11px] text-muted-foreground">
                Personal or group chat ID (@userinfobot can help).
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full sm:w-auto"
              disabled={testing === 'telegram'}
              onClick={() => runTest('telegram')}
            >
              {testing === 'telegram' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <MessageCircle className="h-4 w-4 mr-2" />
              )}
              Send test message
            </Button>
          </CardContent>
        </Card>

        {/* Discord */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10">
                  <MessageCircle className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <CardTitle className="text-base">Discord</CardTitle>
                  <CardDescription className="text-xs">Channel webhook embeds</CardDescription>
                </div>
              </div>
              <Switch
                checked={!!settings.discord_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, discord_enabled: checked })
                }
                aria-label="Enable Discord"
              />
            </div>
          </CardHeader>
          <CardContent className={`space-y-4 ${settings.discord_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div className="space-y-2">
              <Label htmlFor="dc-hook">Webhook URL</Label>
              {settings.discord_webhook_url_configured && !showDiscordWebhook ? (
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/40 text-sm">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Configured
                    </Badge>
                    <span className="ml-2 text-muted-foreground text-xs">Leave blank to keep</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setShowDiscordWebhook(true)}
                    title="Change webhook"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    id="dc-hook"
                    type="password"
                    autoComplete="off"
                    placeholder="https://discord.com/api/webhooks/..."
                    value={settings.discord_webhook_url || ''}
                    onChange={(e) =>
                      setSettings({ ...settings, discord_webhook_url: e.target.value })
                    }
                  />
                  {settings.discord_webhook_url_configured && (
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => {
                        setShowDiscordWebhook(false)
                        setSettings({ ...settings, discord_webhook_url: '' })
                      }}
                    >
                      <EyeOff className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              )}
              <p className="text-[11px] text-muted-foreground">
                Server Settings → Integrations → Webhooks → New Webhook.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full sm:w-auto"
              disabled={testing === 'discord'}
              onClick={() => runTest('discord')}
            >
              {testing === 'discord' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send test embed
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* ntfy / Gotify / webhook */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <Bell className="h-4 w-4 text-emerald-500" />
                </div>
                <div>
                  <CardTitle className="text-base">ntfy</CardTitle>
                  <CardDescription className="text-xs">Topic URL push (Umbrel-friendly)</CardDescription>
                </div>
              </div>
              <Switch
                checked={!!settings.ntfy_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, ntfy_enabled: checked })
                }
                aria-label="Enable ntfy"
              />
            </div>
          </CardHeader>
          <CardContent className={`space-y-3 ${settings.ntfy_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div className="space-y-1.5">
              <Label htmlFor="ntfy-url">Topic URL</Label>
              <Input
                id="ntfy-url"
                placeholder="https://ntfy.sh/mytopic"
                value={settings.ntfy_url || ''}
                onChange={(e) => setSettings({ ...settings, ntfy_url: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ntfy-token">Access token (optional)</Label>
              {settings.ntfy_token_configured && !showNtfyToken ? (
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/40 text-sm">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                      Configured
                    </Badge>
                  </div>
                  <Button type="button" variant="outline" size="icon" onClick={() => setShowNtfyToken(true)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Input
                  id="ntfy-token"
                  type="password"
                  autoComplete="off"
                  value={settings.ntfy_token || ''}
                  onChange={(e) => setSettings({ ...settings, ntfy_token: e.target.value })}
                />
              )}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={testing === 'ntfy'}
              onClick={() => runTest('ntfy')}
            >
              {testing === 'ntfy' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
              Send test
            </Button>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-amber-500/10">
                  <Server className="h-4 w-4 text-amber-500" />
                </div>
                <div>
                  <CardTitle className="text-base">Gotify</CardTitle>
                  <CardDescription className="text-xs">Self-hosted push server</CardDescription>
                </div>
              </div>
              <Switch
                checked={!!settings.gotify_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, gotify_enabled: checked })
                }
                aria-label="Enable Gotify"
              />
            </div>
          </CardHeader>
          <CardContent className={`space-y-3 ${settings.gotify_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div className="space-y-1.5">
              <Label htmlFor="gotify-url">Server URL</Label>
              <Input
                id="gotify-url"
                placeholder="https://gotify.example.com"
                value={settings.gotify_url || ''}
                onChange={(e) => setSettings({ ...settings, gotify_url: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="gotify-token">App token</Label>
              {settings.gotify_token_configured && !showGotifyToken ? (
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/40 text-sm">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                      Configured
                    </Badge>
                  </div>
                  <Button type="button" variant="outline" size="icon" onClick={() => setShowGotifyToken(true)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Input
                  id="gotify-token"
                  type="password"
                  autoComplete="off"
                  value={settings.gotify_token || ''}
                  onChange={(e) => setSettings({ ...settings, gotify_token: e.target.value })}
                />
              )}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={testing === 'gotify'}
              onClick={() => runTest('gotify')}
            >
              {testing === 'gotify' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
              Send test
            </Button>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-slate-500/10">
                  <Send className="h-4 w-4 text-slate-500" />
                </div>
                <div>
                  <CardTitle className="text-base">Webhook</CardTitle>
                  <CardDescription className="text-xs">Generic JSON POST</CardDescription>
                </div>
              </div>
              <Switch
                checked={!!settings.webhook_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, webhook_enabled: checked })
                }
                aria-label="Enable webhook"
              />
            </div>
          </CardHeader>
          <CardContent className={`space-y-3 ${settings.webhook_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div className="space-y-1.5">
              <Label htmlFor="webhook-url">Webhook URL</Label>
              {settings.webhook_url_configured && !showWebhookUrl ? (
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/40 text-sm">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                      Configured
                    </Badge>
                  </div>
                  <Button type="button" variant="outline" size="icon" onClick={() => setShowWebhookUrl(true)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Input
                  id="webhook-url"
                  type="password"
                  autoComplete="off"
                  placeholder="https://hooks.example.com/..."
                  value={settings.webhook_url || ''}
                  onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
                />
              )}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={testing === 'webhook'}
              onClick={() => runTest('webhook')}
            >
              {testing === 'webhook' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
              Send test
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Quiet hours + cadence */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-violet-500/10">
              <Moon className="h-4 w-4 text-violet-500" />
            </div>
            <div>
              <CardTitle className="text-base">Quiet hours & re-alert</CardTitle>
              <CardDescription className="text-xs">
                Suppress info/warn chat during quiet hours. Critical alerts always deliver.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <Label htmlFor="quiet-hours">Enable quiet hours</Label>
            <Switch
              id="quiet-hours"
              checked={!!settings.quiet_hours_enabled}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, quiet_hours_enabled: checked })
              }
            />
          </div>
          <div
            className={`grid gap-3 sm:grid-cols-3 ${settings.quiet_hours_enabled ? '' : 'opacity-50'}`}
          >
            <div className="space-y-1.5">
              <Label className="text-xs">Start (HH:MM)</Label>
              <Input
                value={settings.quiet_hours_start || '22:00'}
                disabled={!settings.quiet_hours_enabled}
                onChange={(e) =>
                  setSettings({ ...settings, quiet_hours_start: e.target.value })
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">End (HH:MM)</Label>
              <Input
                value={settings.quiet_hours_end || '07:00'}
                disabled={!settings.quiet_hours_enabled}
                onChange={(e) =>
                  setSettings({ ...settings, quiet_hours_end: e.target.value })
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Re-alert (minutes)</Label>
              <Input
                type="number"
                min={5}
                max={1440}
                value={settings.alert_repeat_minutes ?? 60}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    alert_repeat_minutes: parseInt(e.target.value, 10) || 60,
                  })
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alert rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alert events</CardTitle>
          <CardDescription>
            Defaults match previous MinerSentinel behavior. Turn individual events off or
            tune thresholds without touching channel credentials.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {ALERT_ORDER.map((key) => {
            const rule = rules[key] || { enabled: true }
            const meta = ALERT_META[key] || ALERT_META.device_offline
            const Icon = meta.icon
            return (
              <div
                key={key}
                className="rounded-xl border border-border/80 bg-card/50 p-4 transition-colors hover:bg-muted/20"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex gap-3 min-w-0">
                    <div className={`p-2 rounded-lg shrink-0 ${meta.bg}`}>
                      <Icon className={`h-4 w-4 ${meta.accent}`} />
                    </div>
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium leading-none">
                          {rule.label || key}
                        </p>
                        {!rule.enabled && (
                          <Badge variant="secondary" className="text-[10px] font-normal">
                            Off
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {rule.description || ''}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={!!rule.enabled}
                    onCheckedChange={(checked) => updateRule(key, { enabled: checked })}
                    aria-label={`Toggle ${rule.label || key}`}
                    className="shrink-0 self-end sm:self-start"
                  />
                </div>

                {/* Tunable params */}
                {key === 'hashrate_stagnation' && rule.enabled && (
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 pl-0 sm:pl-11">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Flat polls before alert</Label>
                      <Input
                        type="number"
                        min={2}
                        max={20}
                        value={rule.threshold_collections ?? 3}
                        onChange={(e) =>
                          updateRule(key, {
                            threshold_collections: parseInt(e.target.value, 10) || 3,
                          })
                        }
                      />
                      <p className="text-[10px] text-muted-foreground">
                        How many consecutive identical samples trigger the alert (2–20)
                      </p>
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Tolerance (GH/s)</Label>
                      <Input
                        type="number"
                        min={0}
                        step={0.01}
                        value={rule.tolerance_ghs ?? 0.1}
                        onChange={(e) =>
                          updateRule(key, {
                            tolerance_ghs: parseFloat(e.target.value) || 0,
                          })
                        }
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Samples within this GH/s range count as “unchanged”
                      </p>
                    </div>
                  </div>
                )}

                {key === 'best_difficulty' && rule.enabled && (
                  <div className="mt-4 max-w-xs pl-0 sm:pl-11 space-y-1.5">
                    <Label className="text-xs">Min improvement %</Label>
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={rule.min_improvement_percent ?? 5}
                      onChange={(e) =>
                        updateRule(key, {
                          min_improvement_percent: parseFloat(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-[10px] text-muted-foreground">
                      Only notify when best difficulty rises by at least this percent
                    </p>
                  </div>
                )}

                {key === 'temperature_high' && rule.enabled && (
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 pl-0 sm:pl-11">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Threshold (°C)</Label>
                      <Input
                        type="number"
                        min={40}
                        max={120}
                        value={rule.threshold_c ?? 80}
                        onChange={(e) =>
                          updateRule(key, {
                            threshold_c: parseFloat(e.target.value) || 80,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Duration (polls)</Label>
                      <Input
                        type="number"
                        min={1}
                        max={20}
                        value={rule.duration_polls ?? 2}
                        onChange={(e) =>
                          updateRule(key, {
                            duration_polls: parseInt(e.target.value, 10) || 2,
                          })
                        }
                      />
                    </div>
                  </div>
                )}

                {key === 'expected_hashrate_drop' && rule.enabled && (
                  <div className="mt-4 max-w-xs pl-0 sm:pl-11 space-y-1.5">
                    <Label className="text-xs">Drop percent vs expected</Label>
                    <Input
                      type="number"
                      min={5}
                      max={95}
                      value={rule.drop_percent ?? 30}
                      onChange={(e) =>
                        updateRule(key, {
                          drop_percent: parseFloat(e.target.value) || 30,
                        })
                      }
                    />
                  </div>
                )}

                {key === 'pool_down' && rule.enabled && (
                  <div className="mt-4 max-w-xs pl-0 sm:pl-11 space-y-1.5">
                    <Label className="text-xs">Stale after (minutes)</Label>
                    <Input
                      type="number"
                      min={5}
                      max={1440}
                      value={rule.stale_minutes ?? 30}
                      onChange={(e) =>
                        updateRule(key, {
                          stale_minutes: parseInt(e.target.value, 10) || 30,
                        })
                      }
                    />
                  </div>
                )}

                {key === 'auto_restart' && rule.enabled && (
                  <p className="mt-3 pl-0 sm:pl-11 text-[11px] text-muted-foreground">
                    Runs after stagnation is detected. Supported on Bitaxe (HTTP restart) and Avalon
                    (cgminer reboot). Disable if you prefer alerts only.
                  </p>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      <div className="flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            // Reset rules to API defaults by clearing local overrides structure
            const defaults = {}
            ALERT_ORDER.forEach((k) => {
              defaults[k] = {
                enabled: true,
                ...(k === 'hashrate_stagnation'
                  ? { threshold_collections: 3, tolerance_ghs: 0.1 }
                  : {}),
                ...(k === 'best_difficulty' ? { min_improvement_percent: 5 } : {}),
              }
            })
            setSettings({ ...settings, notification_rules: defaults })
          }}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Reset alerts to defaults
        </Button>
        <Button type="button" onClick={onSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving…
            </>
          ) : (
            'Save notification settings'
          )}
        </Button>
      </div>
    </div>
  )
}
