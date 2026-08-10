import MakeBadge from '@/components/devices/MakeBadge'
import StatusIndicator from '@/components/status/StatusIndicator'
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectOption } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import NotificationsSettings from '@/components/settings/NotificationsSettings'
import { useTheme } from '@/components/theme-provider'
import api from '@/lib/api';
import {
  deviceStatusLabel,
  getDeviceStatus,
  isDeviceOnline,
  makeLabel,
  SUPPORTED_MAKES,
  unwrapList,
} from '@/lib/devices'
import { formatRelativeTime } from '@/lib/formatters'
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Edit,
  Plus,
  RefreshCw,
  Server,
  Monitor,
  Moon,
  Settings as SettingsIcon,
  Sun,
  Trash2,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useEffect, useState } from 'react';

export default function SettingsPage() {
  // Device management (unified registry)
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState('add') // 'add' or 'edit'
  const [currentDevice, setCurrentDevice] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    device_id: '',
    device_name: '',
    make: 'bitaxe',
    ip_address: '',
    is_active: true,
  })

  // Data collector + notification settings (shared API singleton)
  const [collectorSettings, setCollectorSettings] = useState({
    polling_interval_minutes: 15,
    device_check_interval_minutes: 5,
    pool_type: 'ckpool',
    ckpool_address: '',
    ckpool_url: 'https://eusolo.ckpool.org',
    publicpool_address: '',
    publicpool_url: 'http://localhost:3334',
    telegram_enabled: false,
    telegram_bot_token: '',
    telegram_chat_id: '',
    telegram_bot_token_configured: false,
    discord_enabled: false,
    discord_webhook_url: '',
    discord_webhook_url_configured: false,
    notification_rules: {},
    energy_rate: 0.12,
    energy_currency: 'USD',
    show_revenue_stats: true,
  })
  const [collectorStatus, setCollectorStatus] = useState(null)
  const [savingSettings, setSavingSettings] = useState(false)
  const [collectorDirty, setCollectorDirty] = useState(false)
  const [settingsTab, setSettingsTab] = useState('devices')
  const [pendingTab, setPendingTab] = useState(null)
  const { theme, setTheme } = useTheme()


  // Delete confirmation
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deviceToDelete, setDeviceToDelete] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [devicesRes, collectorRes] = await Promise.all([
        api.get('/api/devices/').catch(() => ({ data: { results: [] } })),
        api.get('/api/settings/collector/').catch(() => ({ data: null })),
      ])

      setDevices(unwrapList(devicesRes.data))

      if (collectorRes.data) {
        setCollectorStatus(collectorRes.data)
        setCollectorDirty(false)
        setCollectorSettings({
          polling_interval_minutes: collectorRes.data.polling_interval_minutes || 15,
          device_check_interval_minutes: collectorRes.data.device_check_interval_minutes || 5,
          pool_type: collectorRes.data.pool_type || 'ckpool',
          ckpool_address: collectorRes.data.ckpool_address || '',
          ckpool_url: collectorRes.data.ckpool_url || 'https://eusolo.ckpool.org',
          publicpool_address: collectorRes.data.publicpool_address || '',
          publicpool_url: collectorRes.data.publicpool_url || 'http://localhost:3334',
          telegram_enabled: collectorRes.data.telegram_enabled || false,
          telegram_bot_token: '', // Never returned from API for security
          telegram_chat_id: collectorRes.data.telegram_chat_id || '',
          telegram_bot_token_configured: collectorRes.data.telegram_bot_token_configured || false,
          discord_enabled: collectorRes.data.discord_enabled || false,
          discord_webhook_url: '', // Never returned from API for security
          discord_webhook_url_configured: collectorRes.data.discord_webhook_url_configured || false,
          notification_rules: collectorRes.data.notification_rules || {},
          energy_rate: collectorRes.data.energy_rate || 0.12,
          energy_currency: collectorRes.data.energy_currency || 'USD',
          show_revenue_stats: collectorRes.data.show_revenue_stats !== undefined ? collectorRes.data.show_revenue_stats : true,
        })
      }
    } catch (err) {
      console.error('Error fetching settings data:', err)
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const updateCollectorSettings = (next) => {
    setCollectorSettings(next)
    setCollectorDirty(true)
  }

  const requestTabChange = (next) => {
    if (collectorDirty && (settingsTab === 'collector' || settingsTab === 'notifications') && next !== settingsTab) {
      setPendingTab(next)
      return
    }
    setSettingsTab(next)
  }

  const openAddDialog = () => {
    setDialogMode('add')
    setCurrentDevice(null)
    setFormData({
      device_id: '',
      device_name: '',
      make: 'bitaxe',
      ip_address: '',
      is_active: true,
    })
    setDialogOpen(true)
  }

  const openEditDialog = (device) => {
    setDialogMode('edit')
    setCurrentDevice(device)
    setFormData({
      device_id: device.device_id,
      device_name: device.device_name,
      make: device.make || 'bitaxe',
      ip_address: device.ip_address,
      is_active: device.is_active,
    })
    setDialogOpen(true)
  }

  const handleSaveDevice = async () => {
    try {
      setError(null)
      const payload = {
        device_id: formData.device_id,
        device_name: formData.device_name,
        make: formData.make,
        ip_address: formData.ip_address,
        is_active: formData.is_active,
      }

      if (dialogMode === 'add') {
        await api.post('/api/devices/', payload)
        setSuccess(`${makeLabel(formData.make)} device added successfully`)
      } else {
        await api.patch(`/api/devices/${currentDevice.id}/`, payload)
        setSuccess(`${makeLabel(formData.make)} device updated successfully`)
      }

      setDialogOpen(false)
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error saving device:', err)
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.device_id?.[0] ||
        (typeof err.response?.data === 'object' ? JSON.stringify(err.response.data) : null) ||
        'Failed to save device'
      setError(detail)
    }
  }

  const openDeleteDialog = (device) => {
    setDeviceToDelete(device)
    setDeleteDialogOpen(true)
  }

  const handleDeleteDevice = async () => {
    try {
      setError(null)
      await api.delete(`/api/devices/${deviceToDelete.id}/`)
      setSuccess(`${makeLabel(deviceToDelete.make)} device deleted successfully`)
      setDeleteDialogOpen(false)
      setDeviceToDelete(null)
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error deleting device:', err)
      setError(err.response?.data?.detail || 'Failed to delete device')
    }
  }

  const handleSaveCollectorSettings = async () => {
    try {
      setSavingSettings(true)
      setError(null)

      // Do not send empty secrets (keeps existing server-side values)
      const payload = { ...collectorSettings }
      if (!payload.telegram_bot_token) delete payload.telegram_bot_token
      if (!payload.discord_webhook_url) delete payload.discord_webhook_url

      const res = await api.post('/api/settings/collector/', payload)
      setSuccess(res.data?.message || 'Settings saved successfully')
      setCollectorDirty(false)
      // Refresh so notification_rules merges + configured flags update
      await fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error saving collector settings:', err)
      setError(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          (err.response?.data?.errors && JSON.stringify(err.response.data.errors)) ||
          'Failed to save settings',
      )
    } finally {
      setSavingSettings(false)
    }
  }

  const triggerManualPoll = async () => {
    try {
      setError(null)
      await api.post('/api/settings/collector/poll/')
      setSuccess('Manual data collection triggered')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error triggering poll:', err)
      setError('Failed to trigger data collection')
    }
  }

  const formatLastSeen = (lastSeen) => {
    if (!lastSeen) return 'Never'
    const date = new Date(lastSeen)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return date.toLocaleDateString()
  }

  const DeviceTable = ({ devices: rows }) => {
    if (rows.length === 0) {
      return (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No devices configured. Click &quot;Add Device&quot; to get started.
        </p>
      )
    }

    const statusUi = (device) => {
      const st = getDeviceStatus(device)
      const dot =
        st === 'online' ? 'online' : st === 'stale' ? 'stale' : st === 'inactive' ? 'unknown' : 'offline'
      return <StatusIndicator status={dot} showLabel label={deviceStatusLabel(st)} />
    }

    return (
      <>
        {/* Mobile cards */}
        <div className="space-y-3 md:hidden">
          {rows.map((device) => (
            <div
              key={`${device.make}-${device.device_id}`}
              className="rounded-lg border border-border/80 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium truncate">{device.device_name}</p>
                  <p className="mt-0.5 font-mono text-xs text-muted-foreground truncate">
                    {device.device_id} · {device.ip_address}
                  </p>
                </div>
                <MakeBadge make={device.make} />
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                {statusUi(device)}
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(device.last_seen_at) || 'Never'}
                </span>
              </div>
              <div className="mt-3 flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9"
                  onClick={() => openEditDialog(device)}
                  aria-label={`Edit ${device.device_name}`}
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 text-destructive hover:text-destructive"
                  onClick={() => openDeleteDialog(device)}
                  aria-label={`Delete ${device.device_name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden overflow-x-auto md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device Name</TableHead>
                <TableHead>Make</TableHead>
                <TableHead>Device ID</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Seen</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((device) => (
                <TableRow key={`${device.make}-${device.device_id}`}>
                  <TableCell className="font-medium">{device.device_name}</TableCell>
                  <TableCell>
                    <MakeBadge make={device.make} />
                  </TableCell>
                  <TableCell className="font-mono text-sm">{device.device_id}</TableCell>
                  <TableCell className="font-mono text-sm">{device.ip_address}</TableCell>
                  <TableCell>{statusUi(device)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatRelativeTime(device.last_seen_at) || 'Never'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9"
                        onClick={() => openEditDialog(device)}
                        aria-label={`Edit ${device.device_name}`}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 text-destructive hover:text-destructive"
                        onClick={() => openDeleteDialog(device)}
                        aria-label={`Delete ${device.device_name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </>
    )
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 overflow-hidden sm:space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <p className="text-xs text-muted-foreground sm:text-sm">
          Devices, collector, pool, notifications, and appearance
          {collectorDirty && (
            <span className="ml-2 font-medium text-status-warning-fg">· Unsaved changes</span>
          )}
        </p>
        <Button variant="outline" onClick={fetchData} className="w-full sm:w-auto">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="border-green-500/50 bg-green-500/10">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-500">{success}</AlertDescription>
        </Alert>
      )}

      <Tabs value={settingsTab} onValueChange={requestTabChange} className="space-y-6">
        <TabsList className="flex h-auto w-full flex-nowrap justify-start gap-0.5 overflow-x-auto sm:w-auto">
          <TabsTrigger value="devices">
            <Cpu className="h-4 w-4 mr-2" />
            Devices
          </TabsTrigger>
          <TabsTrigger value="collector">
            <Server className="h-4 w-4 mr-2" />
            Data Collector
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="h-4 w-4 mr-2" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="appearance">
            <Sun className="h-4 w-4 mr-2" />
            Appearance
          </TabsTrigger>
        </TabsList>

        {/* Devices Tab */}
        <TabsContent value="devices" className="space-y-4 sm:space-y-6">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                  <Cpu className="h-4 w-4 sm:h-5 sm:w-5" />
                  Mining Devices
                </CardTitle>
                <CardDescription className="text-xs sm:text-sm">
                  All miner makes in one registry ({devices.length} device{devices.length !== 1 ? 's' : ''})
                </CardDescription>
              </div>
              <Button onClick={openAddDialog} className="w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            </CardHeader>
            <CardContent className="px-2 sm:px-6">
              <DeviceTable devices={devices} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Data Collector Tab */}
        <TabsContent value="collector" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                Data Collector Status
              </CardTitle>
              <CardDescription>
                Monitor and configure the data collection service
              </CardDescription>
            </CardHeader>
            <CardContent className="max-w-2xl space-y-4 overflow-x-auto sm:space-y-6">
              {/* Status badges */}
              <div className="flex flex-col sm:flex-row flex-wrap gap-2 sm:gap-4 min-w-0 max-w-full">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Running
                  </Badge>
                </div>
                {collectorStatus?.next_run && (
                  <div className="flex items-center gap-2 text-muted-foreground text-xs sm:text-sm">
                    <Clock className="w-4 h-4" />
                    Next run: {new Date(collectorStatus.next_run).toLocaleTimeString()}
                  </div>
                )}
                <div className="flex items-center gap-2 text-muted-foreground text-xs sm:text-sm">
                  <Cpu className="w-4 h-4" />
                  {SUPPORTED_MAKES.map((m, i) => (
                    <span key={m.value}>
                      {i > 0 ? ', ' : ''}
                      {devices.filter((d) => d.make === m.value).length} {m.label}
                    </span>
                  ))}
                  {' '}({devices.length} total)
                </div>
              </div>

              {/* Settings form */}
              <div className="grid gap-4 grid-cols-1 w-full max-w-full">
                <div className="space-y-2 min-w-0 overflow-hidden">
                  <Label htmlFor="polling_interval" className="text-sm">Polling Interval (minutes)</Label>
                  <Input
                    id="polling_interval"
                    type="number"
                    min="1"
                    max="60"
                    className="w-full"
                    value={collectorSettings.polling_interval_minutes}
                    onChange={(e) =>
                      updateCollectorSettings({
                        ...collectorSettings,
                        polling_interval_minutes: parseInt(e.target.value) || 15,
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    How often to poll devices for new data
                  </p>
                </div>

                <div className="space-y-2 min-w-0 overflow-hidden">
                  <Label htmlFor="device_check_interval" className="text-sm">Device Check Interval (minutes)</Label>
                  <Input
                    id="device_check_interval"
                    type="number"
                    min="1"
                    max="30"
                    className="w-full"
                    value={collectorSettings.device_check_interval_minutes}
                    onChange={(e) =>
                      updateCollectorSettings({
                        ...collectorSettings,
                        device_check_interval_minutes: parseInt(e.target.value) || 5,
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    How often to check for new or updated devices
                  </p>
                </div>

                {/* Pool Type Selection */}
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="pool_type" className="text-sm">Mining Pool</Label>
                  <Select
                    id="pool_type"
                    value={collectorSettings.pool_type}
                    onValueChange={(value) =>
                      updateCollectorSettings({
                        ...collectorSettings,
                        pool_type: value,
                      })
                    }
                  >
                    <SelectOption value="ckpool">CKPool (Solo Mining)</SelectOption>
                    <SelectOption value="publicpool">Public Pool (Local/Self-hosted)</SelectOption>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Select which mining pool to use for statistics collection
                  </p>
                </div>
              </div>

              {/* CKPool Settings */}
              {collectorSettings.pool_type === 'ckpool' && (
                <div className="grid gap-4 grid-cols-1 pt-4 border-t w-full max-w-full">
                  <div className="space-y-2 min-w-0 overflow-hidden">
                    <Label htmlFor="ckpool_address" className="text-sm">CKPool Bitcoin Address</Label>
                    <Input
                      id="ckpool_address"
                      type="text"
                      className="w-full"
                      placeholder="bc1q..."
                      value={collectorSettings.ckpool_address}
                      onChange={(e) =>
                        updateCollectorSettings({
                          ...collectorSettings,
                          ckpool_address: e.target.value,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Your Bitcoin address for CKPool statistics
                    </p>
                  </div>

                  <div className="space-y-2 min-w-0 overflow-hidden">
                    <Label htmlFor="ckpool_url" className="text-sm">CKPool Server</Label>
                    <Select
                      id="ckpool_url"
                      value={
                        ['https://solo.ckpool.org', 'https://eusolo.ckpool.org', 'https://ussolo.ckpool.org'].includes(collectorSettings.ckpool_url)
                          ? collectorSettings.ckpool_url
                          : 'custom'
                      }
                      onValueChange={(value) => {
                        if (value === 'custom') {
                          updateCollectorSettings({
                            ...collectorSettings,
                            ckpool_url: '',
                          })
                        } else {
                          updateCollectorSettings({
                            ...collectorSettings,
                            ckpool_url: value,
                          })
                        }
                      }}
                    >
                      <SelectOption value="https://solo.ckpool.org">solo.ckpool.org (Main)</SelectOption>
                      <SelectOption value="https://eusolo.ckpool.org">eusolo.ckpool.org (Europe)</SelectOption>
                      <SelectOption value="https://ussolo.ckpool.org">ussolo.ckpool.org (US)</SelectOption>
                      <SelectOption value="custom">Custom Instance</SelectOption>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Select your preferred CKPool server or use a custom instance
                    </p>
                  </div>

                  {/* Custom CKPool URL input */}
                  {!['https://solo.ckpool.org', 'https://eusolo.ckpool.org', 'https://ussolo.ckpool.org'].includes(collectorSettings.ckpool_url) && (
                    <div className="space-y-2 min-w-0 overflow-hidden">
                      <Label htmlFor="ckpool_custom_url" className="text-sm">Custom CKPool URL</Label>
                      <Input
                        id="ckpool_custom_url"
                        type="text"
                        className="w-full"
                        placeholder="https://your-ckpool-instance.com"
                        value={collectorSettings.ckpool_url}
                        onChange={(e) =>
                          updateCollectorSettings({
                            ...collectorSettings,
                            ckpool_url: e.target.value,
                          })
                        }
                      />
                      <p className="text-xs text-muted-foreground">
                        Enter the full URL of your custom CKPool instance (e.g., https://mypool.local:8080)
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* PublicPool Settings */}
              {collectorSettings.pool_type === 'publicpool' && (
                <div className="grid gap-4 grid-cols-1 pt-4 border-t w-full max-w-full">
                  <div className="space-y-2 min-w-0 overflow-hidden">
                    <Label htmlFor="publicpool_address" className="text-sm">PublicPool Bitcoin Address</Label>
                    <Input
                      id="publicpool_address"
                      type="text"
                      className="w-full"
                      placeholder="bc1q..."
                      value={collectorSettings.publicpool_address}
                      onChange={(e) =>
                        updateCollectorSettings({
                          ...collectorSettings,
                          publicpool_address: e.target.value,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Your Bitcoin address for PublicPool statistics
                    </p>
                  </div>

                  <div className="space-y-2 min-w-0 overflow-hidden">
                    <Label htmlFor="publicpool_url" className="text-sm">PublicPool API URL</Label>
                    <Input
                      id="publicpool_url"
                      type="text"
                      className="w-full"
                      placeholder="http://localhost:3334"
                      value={collectorSettings.publicpool_url}
                      onChange={(e) =>
                        updateCollectorSettings({
                          ...collectorSettings,
                          publicpool_url: e.target.value,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Your local PublicPool instance URL (e.g., http://192.168.1.100:3334)
                    </p>
                  </div>
                </div>
              )}

              {/* Cost Analysis Settings */}
              <div className="pt-4 border-t space-y-4">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  <Label className="text-base font-medium">Cost Analysis</Label>
                </div>

                <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="energy_rate">Energy Rate (per kWh)</Label>
                    <div className="flex gap-2">
                      <Input
                        id="energy_rate"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="0.12"
                        value={collectorSettings.energy_rate}
                        onChange={(e) =>
                          updateCollectorSettings({
                            ...collectorSettings,
                            energy_rate: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="flex-1"
                      />
                      <Select
                        value={collectorSettings.energy_currency}
                        onValueChange={(value) =>
                          updateCollectorSettings({
                            ...collectorSettings,
                            energy_currency: value,
                          })
                        }
                        className="w-24"
                      >
                        <SelectOption value="USD">USD</SelectOption>
                        <SelectOption value="EUR">EUR</SelectOption>
                        <SelectOption value="GBP">GBP</SelectOption>
                        <SelectOption value="CHF">CHF</SelectOption>
                      </Select>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Your electricity cost per kilowatt-hour
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="show_revenue_stats">Show Revenue Statistics</Label>
                    <p className="text-xs text-muted-foreground">
                      Enable to show estimated earnings (disable for solo mining)
                    </p>
                  </div>
                  <Switch
                    id="show_revenue_stats"
                    checked={collectorSettings.show_revenue_stats}
                    onCheckedChange={(checked) =>
                      updateCollectorSettings({
                        ...collectorSettings,
                        show_revenue_stats: checked,
                      })
                    }
                  />
                </div>

              </div>

              {/* Action buttons */}
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 pt-4">
                <Button onClick={handleSaveCollectorSettings} disabled={savingSettings} className="w-full sm:w-auto">
                  {savingSettings ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Settings'
                  )}
                </Button>
                <Button variant="outline" onClick={triggerManualPoll} className="w-full sm:w-auto">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Trigger Manual Poll
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <NotificationsSettings
            settings={collectorSettings}
            setSettings={(s) => {
              setCollectorSettings((prev) => (typeof s === 'function' ? s(prev) : s))
              setCollectorDirty(true)
            }}
            onSave={handleSaveCollectorSettings}
            saving={savingSettings}
          />
        </TabsContent>

        <TabsContent value="appearance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base sm:text-lg">Theme</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Choose light, dark, or match the system preference
              </CardDescription>
            </CardHeader>
            <CardContent className="max-w-md space-y-3">
              {[
                { value: 'light', label: 'Light', icon: Sun },
                { value: 'dark', label: 'Dark', icon: Moon },
                { value: 'system', label: 'System', icon: Monitor },
              ].map((opt) => {
                const Icon = opt.icon
                const active = theme === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTheme(opt.value)}
                    className={
                      'flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ' +
                      (active
                        ? 'border-primary bg-accent/50 text-foreground'
                        : 'border-border hover:bg-muted/50 text-muted-foreground')
                    }
                  >
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                    <span className="font-medium">{opt.label}</span>
                    {active && <span className="ml-auto text-xs text-primary">Active</span>}
                  </button>
                )
              })}
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>

      {/* Unsaved changes guard */}
      <Dialog open={!!pendingTab} onOpenChange={(open) => { if (!open) setPendingTab(null) }}>
        <DialogContent onClose={() => setPendingTab(null)}>
          <DialogHeader>
            <DialogTitle>Unsaved changes</DialogTitle>
            <DialogDescription>
              You have unsaved collector or notification settings. Leave without saving?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingTab(null)}>Stay</Button>
            <Button
              variant="destructive"
              onClick={() => {
                setCollectorDirty(false)
                setSettingsTab(pendingTab)
                setPendingTab(null)
                fetchData()
              }}
            >
              Discard
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      {/* Add/Edit Device Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent onClose={() => setDialogOpen(false)}>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === 'add' ? 'Add Device' : 'Edit Device'}
            </DialogTitle>
            <DialogDescription>
              {dialogMode === 'add'
                ? 'Choose the miner make and enter connection details.'
                : 'Update the device configuration.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="make">Make</Label>
              <Select
                id="make"
                value={formData.make}
                onValueChange={(value) => setFormData({ ...formData, make: value })}
                disabled={dialogMode === 'edit'}
              >
                {SUPPORTED_MAKES.map((m) => (
                  <SelectOption key={m.value} value={m.value}>{m.label}</SelectOption>
                ))}
              </Select>
              <p className="text-xs text-muted-foreground">
                Manufacturer / firmware family (more makes can be added later)
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="device_id">Device ID</Label>
              <Input
                id="device_id"
                placeholder="e.g., bitaxe-001 or living-room"
                value={formData.device_id}
                onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
                disabled={dialogMode === 'edit'}
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier for this device within its make
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="device_name">Device Name</Label>
              <Input
                id="device_name"
                placeholder="e.g., Living Room Miner"
                value={formData.device_name}
                onChange={(e) => setFormData({ ...formData, device_name: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Friendly name for display
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="ip_address">IP Address</Label>
              <Input
                id="ip_address"
                placeholder="e.g., 192.168.1.100"
                value={formData.ip_address}
                onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                The device&apos;s local network IP address
              </p>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Active</Label>
                <p className="text-xs text-muted-foreground">
                  Enable data collection for this device
                </p>
              </div>
              <Switch
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveDevice}>
              {dialogMode === 'add' ? 'Add Device' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent onClose={() => setDeleteDialogOpen(false)}>
          <DialogHeader>
            <DialogTitle>Delete Device</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deviceToDelete?.device_name}"? This action cannot be undone.
              All historical data for this device will also be deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteDevice}>
              Delete Device
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
