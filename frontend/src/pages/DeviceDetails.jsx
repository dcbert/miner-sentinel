/**
 * Unified device detail route: /devices/:make/:deviceId
 * One UI for all makes (Bitaxe-style layout + unified API).
 */
import { Navigate, useParams } from 'react-router-dom'
import BitAxeDeviceDetails from '@/pages/BitAxeDeviceDetails'

export default function DeviceDetails() {
  const { make, deviceId } = useParams()

  if (!make || !deviceId) {
    return <Navigate to="/mining" replace />
  }

  return <BitAxeDeviceDetails />
}
