/**
 * Legacy route wrapper: /avalon/device/:deviceId → /devices/avalon/:deviceId
 */
import { Navigate, useParams } from 'react-router-dom'

export default function AvalonDeviceDetails() {
  const { deviceId } = useParams()
  if (!deviceId) return <Navigate to="/mining" replace />
  return <Navigate to={`/devices/avalon/${deviceId}`} replace />
}
