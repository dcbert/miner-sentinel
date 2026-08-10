import EmptyState from '@/components/feedback/EmptyState'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { BarChart3 } from 'lucide-react'

/**
 * Consistent chart shell: title, description, badges, loading/empty, height.
 */
export default function ChartFrame({
  title,
  description,
  badge,
  legend,
  loading = false,
  empty = false,
  emptyTitle = 'No samples in this range',
  emptyDescription = 'Try a different time range or wait for the next collection cycle.',
  heightClass = 'h-[220px] sm:h-[260px] lg:h-[300px]',
  className,
  children,
}) {
  return (
    <Card className={cn(className)}>
      {(title || description || badge || legend) && (
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              {title && <CardTitle className="text-base font-semibold sm:text-lg">{title}</CardTitle>}
              {description && (
                <CardDescription className="text-xs sm:text-sm">{description}</CardDescription>
              )}
            </div>
            {(badge || legend) && (
              <div className="flex flex-wrap items-center gap-2">
                {legend}
                {badge}
              </div>
            )}
          </div>
        </CardHeader>
      )}
      <CardContent>
        {loading ? (
          <Skeleton className={cn('w-full', heightClass)} />
        ) : empty ? (
          <EmptyState
            icon={BarChart3}
            title={emptyTitle}
            description={emptyDescription}
            className={cn('border-0 bg-transparent py-8', heightClass)}
          />
        ) : (
          <div className={heightClass}>{children}</div>
        )}
      </CardContent>
    </Card>
  )
}
