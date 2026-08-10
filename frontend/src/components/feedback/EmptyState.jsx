import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useNavigate } from 'react-router-dom'

/**
 * Empty / zero-data state with optional CTA.
 * action: { label, to? | onClick? }
 */
export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}) {
  const navigate = useNavigate()
  const handleAction = () => {
    if (action?.onClick) action.onClick()
    else if (action?.to) navigate(action.to)
  }
  const cta = action ? (
    <Button size="sm" className="mt-4" onClick={handleAction}>
      {action.label}
    </Button>
  ) : null

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/20 px-6 py-12 text-center',
        className,
      )}
    >
      {Icon && (
        <div className="mb-3 rounded-lg bg-muted p-3 text-muted-foreground">
          <Icon className="h-6 w-6" strokeWidth={1.75} />
        </div>
      )}
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {cta}
    </div>
  )
}
