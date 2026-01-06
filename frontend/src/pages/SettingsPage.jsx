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
import api from '@/lib/api';
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Edit,
  EyeOff,
  Plus,
  RefreshCw,
  Server,
  Settings as SettingsIcon,
  Trash2,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useEffect, useState } from 'react';

export default function SettingsPage() {
  // Device management
  const [bitaxeDevices, setBitaxeDevices] = useState([])
  const [avalonDevices, setAvalonDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState('add') // 'add' or 'edit'
  const [dialogDeviceType, setDialogDeviceType] = useState('bitaxe')
  const [currentDevice, setCurrentDevice] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    device_id: '',
    device_name: '',
    ip_address: '',
    is_active: true,
  })

  // Data collector settings
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
    // Cost analysis settings
    energy_rate: 0.12,
    energy_currency: 'USD',
    show_revenue_stats: true,
  })
  const [showTelegramToken, setShowTelegramToken] = useState(false)
  const [collectorStatus, setCollectorStatus] = useState(null)
  const [savingSettings, setSavingSettings] = useState(false)


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

      const [bitaxeRes, avalonRes, collectorRes] = await Promise.all([
        api.get('/api/bitaxe/devices/').catch(() => ({ data: { results: [] } })),
        api.get('/api/avalon/devices/').catch(() => ({ data: [] })),
        api.get('/api/settings/collector/').catch(() => ({ data: null })),
      ])

      setBitaxeDevices(bitaxeRes.data.results || bitaxeRes.data || [])
      setAvalonDevices(avalonRes.data.results || avalonRes.data || [])

      if (collectorRes.data) {
        setCollectorStatus(collectorRes.data)
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
          energy_rate: collectorRes.data.energy_rate || 0.12,
          energy_currency: collectorRes.data.energy_currency || 'USD',
          show_revenue_stats: collectorRes.data.show_revenue_stats !== undefined ? collectorRes.data.show_revenue_stats : true,
        })
        // Reset token visibility when refreshing
        setShowTelegramToken(false)
      }
    } catch (err) {
      console.error('Error fetching settings data:', err)
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const openAddDialog = (deviceType) => {
    setDialogMode('add')
    setDialogDeviceType(deviceType)
    setFormData({
      device_id: '',
      device_name: '',
      ip_address: '',
      is_active: true,
    })
    setDialogOpen(true)
  }

  const openEditDialog = (device, deviceType) => {
    setDialogMode('edit')
    setDialogDeviceType(deviceType)
    setCurrentDevice(device)
    setFormData({
      device_id: device.device_id,
      device_name: device.device_name,
      ip_address: device.ip_address,
      is_active: device.is_active,
    })
    setDialogOpen(true)
  }

  const handleSaveDevice = async () => {
    try {
      setError(null)
      const endpoint = dialogDeviceType === 'bitaxe' ? '/api/bitaxe/devices' : '/api/avalon/devices'

      if (dialogMode === 'add') {
        await api.post(`${endpoint}/`, formData)
        setSuccess(`${dialogDeviceType === 'bitaxe' ? 'Bitaxe' : 'Avalon'} device added successfully`)
      } else {
        await api.put(`${endpoint}/${currentDevice.device_id}/`, formData)
        setSuccess(`${dialogDeviceType === 'bitaxe' ? 'Bitaxe' : 'Avalon'} device updated successfully`)
      }

      setDialogOpen(false)
      fetchData()

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error saving device:', err)
      setError(err.response?.data?.detail || 'Failed to save device')
    }
  }

  const openDeleteDialog = (device, deviceType) => {
    setDeviceToDelete({ ...device, deviceType })
    setDeleteDialogOpen(true)
  }

  const handleDeleteDevice = async () => {
    try {
      setError(null)
      const endpoint = deviceToDelete.deviceType === 'bitaxe' ? '/api/bitaxe/devices' : '/api/avalon/devices'
      await api.delete(`${endpoint}/${deviceToDelete.device_id}/`)

      setSuccess(`${deviceToDelete.deviceType === 'bitaxe' ? 'Bitaxe' : 'Avalon'} device deleted successfully`)
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

      await api.post('/api/settings/collector/', collectorSettings)
      setSuccess('Data collector settings saved successfully')

      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      console.error('Error saving collector settings:', err)
      setError(err.response?.data?.detail || 'Failed to save collector settings')
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

  const DeviceTable = ({ devices, deviceType }) => (
    <div className="overflow-x-auto sm:mx-0">
      <Table className="min-w-[600px]">
        <TableHeader>
          <TableRow>
            <TableHead>Device Name</TableHead>
            <TableHead className="hidden sm:table-cell">Device ID</TableHead>
            <TableHead>IP Address</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="hidden sm:table-cell">Last Seen</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No {deviceType === 'bitaxe' ? 'Bitaxe' : 'Avalon'} devices configured.
                Click "Add Device" to get started.
              </TableCell>
            </TableRow>
          ) : (
            devices.map((device) => (
              <TableRow key={device.id}>
                <TableCell className="font-medium">
                  <div>
                    {device.device_name}
                    <span className="block sm:hidden text-xs text-muted-foreground font-mono mt-0.5">
                      {device.device_id}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="font-mono text-sm hidden sm:table-cell">{device.device_id}</TableCell>
                <TableCell className="font-mono text-xs sm:text-sm">{device.ip_address}</TableCell>
                <TableCell>
                {device.is_active ? (
                  device.last_seen_at ? (
                    <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                      <Wifi className="w-3 h-3 mr-1" />
                      Online
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
                      <Clock className="w-3 h-3 mr-1" />
                      Pending
                    </Badge>
                  )
                ) : (
                  <Badge variant="outline" className="bg-gray-500/10 text-gray-500 border-gray-500/20">
                    <WifiOff className="w-3 h-3 mr-1" />
                    Inactive
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground hidden sm:table-cell">
                {formatLastSeen(device.last_seen_at)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex gap-1 sm:gap-2 justify-end">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => openEditDialog(device, deviceType)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    onClick={() => openDeleteDialog(device, deviceType)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
    </div>
  )

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
    <div className="p-3 sm:p-6 space-y-4 sm:space-y-6 overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-6 w-6 sm:h-8 sm:w-8" />
          <div>
            <h1 className="text-xl sm:text-2xl font-bold">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage devices and data collection</p>
          </div>
        </div>
        <Button variant="outline" onClick={fetchData} className="w-full sm:w-auto">
          <RefreshCw className="h-4 w-4 mr-2" />
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

      <Tabs defaultValue="devices" className="space-y-6">
        <TabsList>
          <TabsTrigger value="devices">
            <Cpu className="h-4 w-4 mr-2" />
            Devices
          </TabsTrigger>
          <TabsTrigger value="collector">
            <Server className="h-4 w-4 mr-2" />
            Data Collector
          </TabsTrigger>
        </TabsList>

        {/* Devices Tab */}
        <TabsContent value="devices" className="space-y-4 sm:space-y-6">
          {/* Bitaxe Devices */}
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                  <Cpu className="h-4 w-4 sm:h-5 sm:w-5" />
                  Bitaxe Devices
                </CardTitle>
                <CardDescription className="text-xs sm:text-sm">
                  Manage your Bitaxe mining devices
                </CardDescription>
              </div>
              <Button onClick={() => openAddDialog('bitaxe')} className="w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            </CardHeader>
            <CardContent className="px-2 sm:px-6">
              <DeviceTable devices={bitaxeDevices} deviceType="bitaxe" />
            </CardContent>
          </Card>

          {/* Avalon Devices */}
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                  <Cpu className="h-4 w-4 sm:h-5 sm:w-5" />
                  Avalon Devices
                </CardTitle>
                <CardDescription className="text-xs sm:text-sm">
                  Manage your Avalon Nano 3s mining devices
                </CardDescription>
              </div>
              <Button onClick={() => openAddDialog('avalon')} className="w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            </CardHeader>
            <CardContent className="px-2 sm:px-6">
              <DeviceTable devices={avalonDevices} deviceType="avalon" />
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
            <CardContent className="space-y-4 sm:space-y-6 overflow-x-auto">
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
                  {bitaxeDevices.length} Bitaxe, {avalonDevices.length} Avalon devices
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
                      setCollectorSettings({
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
                      setCollectorSettings({
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
                      setCollectorSettings({
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
                        setCollectorSettings({
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
                          setCollectorSettings({
                            ...collectorSettings,
                            ckpool_url: '',
                          })
                        } else {
                          setCollectorSettings({
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
                          setCollectorSettings({
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
                        setCollectorSettings({
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
                        setCollectorSettings({
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

              {/* Telegram Notifications Settings */}
              <div className="pt-4 border-t space-y-4">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4" />
                  <Label className="text-base font-medium">Telegram Notifications</Label>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="telegram_enabled">Enable Telegram Alerts</Label>
                    <p className="text-xs text-muted-foreground">
                      Receive notifications when devices go offline or come back online
                    </p>
                  </div>
                  <Switch
                    id="telegram_enabled"
                    checked={collectorSettings.telegram_enabled}
                    onCheckedChange={(checked) =>
                      setCollectorSettings({
                        ...collectorSettings,
                        telegram_enabled: checked,
                      })
                    }
                  />
                </div>

                {collectorSettings.telegram_enabled && (
                  <div className="grid gap-4 grid-cols-1 pl-3 sm:pl-4 border-l-2 border-muted w-full max-w-full">
                    <div className="space-y-2 min-w-0 overflow-hidden">
                      <Label htmlFor="telegram_bot_token">Bot Token</Label>
                      {collectorSettings.telegram_bot_token_configured && !showTelegramToken ? (
                        <div className="flex gap-2">
                          <div className="flex-1 flex items-center px-3 py-2 rounded-md border bg-muted/50">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                              Configured
                            </Badge>
                          </div>
                          <Button
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
                            id="telegram_bot_token"
                            type="password"
                            placeholder="Enter your Telegram Bot Token"
                            value={collectorSettings.telegram_bot_token}
                            onChange={(e) =>
                              setCollectorSettings({
                                ...collectorSettings,
                                telegram_bot_token: e.target.value,
                              })
                            }
                          />
                          {collectorSettings.telegram_bot_token_configured && (
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => {
                                setShowTelegramToken(false)
                                setCollectorSettings({
                                  ...collectorSettings,
                                  telegram_bot_token: '',
                                })
                              }}
                              title="Cancel"
                            >
                              <EyeOff className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Create a bot via @BotFather on Telegram to get your token
                      </p>
                    </div>

                    <div className="space-y-2 min-w-0 overflow-hidden">
                      <Label htmlFor="telegram_chat_id">Chat ID</Label>
                      <Input
                        id="telegram_chat_id"
                        type="text"
                        placeholder="e.g., 123456789 or -100123456789"
                        value={collectorSettings.telegram_chat_id}
                        onChange={(e) =>
                          setCollectorSettings({
                            ...collectorSettings,
                            telegram_chat_id: e.target.value,
                          })
                        }
                      />
                      <p className="text-xs text-muted-foreground">
                        Your personal chat ID or group chat ID (use @userinfobot to find it)
                      </p>
                    </div>
                  </div>
                )}
              </div>

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
                          setCollectorSettings({
                            ...collectorSettings,
                            energy_rate: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="flex-1"
                      />
                      <Select
                        value={collectorSettings.energy_currency}
                        onValueChange={(value) =>
                          setCollectorSettings({
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
                      setCollectorSettings({
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
      </Tabs>

      {/* Add/Edit Device Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent onClose={() => setDialogOpen(false)}>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === 'add' ? 'Add' : 'Edit'} {dialogDeviceType === 'bitaxe' ? 'Bitaxe' : 'Avalon'} Device
            </DialogTitle>
            <DialogDescription>
              {dialogMode === 'add'
                ? 'Enter the details for the new device.'
                : 'Update the device configuration.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="device_id">Device ID</Label>
              <Input
                id="device_id"
                placeholder="e.g., bitaxe-001 or avalon-001"
                value={formData.device_id}
                onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
                disabled={dialogMode === 'edit'}
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier for this device
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
                The device's local network IP address
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
