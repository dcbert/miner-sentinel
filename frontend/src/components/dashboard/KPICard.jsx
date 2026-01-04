import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

export default function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  progress,
  badge,
  trend,
  className = ""
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
        {progress !== undefined && (
          <Progress value={progress} className="mt-2 h-2" />
        )}
        {badge && (
          <div className="mt-2 flex items-center gap-2">
            <Badge variant={badge.variant}>{badge.text}</Badge>
          </div>
        )}
        {trend && (
          <div className="mt-2 flex items-center text-xs">
            <trend.icon className={`h-3 w-3 mr-1 ${trend.color}`} />
            <span className={trend.color}>{trend.text}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}