import { Badge } from '@/components/ui/badge'
import { makeLabel } from '@/lib/devices'
import { cn } from '@/lib/utils'
import { Cpu, HardDrive, Monitor, Server } from 'lucide-react'

const MAKE_VISUAL = {
  bitaxe: { token: 'make-1', Icon: Cpu },
  avalon: { token: 'make-2', Icon: Server },
  nmaxe: { token: 'make-3', Icon: Cpu },
  nerdnos: { token: 'make-4', Icon: HardDrive },
  other: { token: 'make-neutral', Icon: Monitor },
}

function resolveMake(make) {
  if (MAKE_VISUAL[make]) return MAKE_VISUAL[make]
  return MAKE_VISUAL.other
}

/** Outline badge + optional icon for device manufacturer. */
export default function MakeBadge({ make, showIcon = false, className }) {
  const { token, Icon } = resolveMake(make)
  const label = makeLabel(make)

  return (
    <Badge
      variant="outline"
      className={cn(
        'gap-1 border-border/80 font-normal text-muted-foreground',
        className,
      )}
    >
      {showIcon && (
        <Icon
          className="h-3 w-3 shrink-0"
          style={{ color: `var(--${token})` }}
          strokeWidth={1.75}
          aria-hidden
        />
      )}
      <span
        className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: `var(--${token})` }}
        aria-hidden
      />
      {label}
    </Badge>
  )
}

export function makeIconPlateClass(make) {
  const { token } = resolveMake(make)
  return {
    plate: 'bg-muted',
    iconStyle: { color: `var(--${token})` },
    Icon: resolveMake(make).Icon,
  }
}

export { MAKE_VISUAL }
