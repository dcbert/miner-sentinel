/**
 * Unified device detail route: /devices/:make/:deviceId
 * Delegates to make-specific detail UIs (Bitaxe-style or Avalon-style).
 */
import { Navigate, useParams } from 'react-router-dom'
import AvalonDeviceDetails from '@/pages/AvalonDeviceDetails'
import BitAxeDeviceDetails from '@/pages/BitAxeDeviceDetails'

export default function DeviceDetails() {
  const { make, deviceId } = useParams()

  if (!make || !deviceId) {
    return <Navigate to="/mining" replace />
  }

  if (make === 'avalon') {
    return <AvalonDeviceDetails />
  }

  // Default: Bitaxe-style detail page (also works for future makes with shared shape)
  return <BitAxeDeviceDetails />
}
