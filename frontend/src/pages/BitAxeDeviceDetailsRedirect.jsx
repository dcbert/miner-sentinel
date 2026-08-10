/**
 * Legacy route wrapper: /bitaxe/device/:deviceId → /devices/bitaxe/:deviceId
 */
import { Navigate, useParams } from 'react-router-dom'

export default function BitAxeDeviceDetailsRedirect() {
  const { deviceId } = useParams()
  if (!deviceId) return <Navigate to="/mining" replace />
  return <Navigate to={`/devices/bitaxe/${deviceId}`} replace />
}
