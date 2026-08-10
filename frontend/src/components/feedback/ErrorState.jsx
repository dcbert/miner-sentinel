import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * Recoverable error surface with optional retry.
 */
export default function ErrorState({
  title = 'Something went wrong',
  description = 'Could not load data. Check that the API is running and try again.',
  onRetry,
  className,
  icon: Icon = AlertTriangle,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border bg-card px-6 py-12 text-center',
        className,
      )}
      role="alert"
    >
      <div className="mb-3 rounded-lg bg-destructive/10 p-3 text-destructive">
        <Icon className="h-6 w-6" strokeWidth={1.75} />
      </div>
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" strokeWidth={1.75} />
          Retry
        </Button>
      )}
    </div>
  )
}
