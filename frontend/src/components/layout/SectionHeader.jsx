import { cn } from '@/lib/utils'

export default function SectionHeader({
  title,
  description,
  action,
  className,
  as: Tag = 'h2',
}) {
  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-3', className)}>
      <div className="min-w-0">
        <Tag className="text-base font-semibold tracking-tight sm:text-lg">{title}</Tag>
        {description && (
          <p className="text-xs text-muted-foreground sm:text-sm">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
