import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function StatsCard({
  title,
  description,
  children,
  className = ""
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {children}
      </CardContent>
    </Card>
  )
}

export function StatRow({ label, value, variant = "default" }) {
  const getVariantClass = (variant) => {
    switch (variant) {
      case 'destructive':
        return 'text-destructive'
      case 'success':
        return 'text-green-500'
      case 'warning':
        return 'text-yellow-500'
      case 'primary':
        return 'text-primary'
      default:
        return 'font-medium'
    }
  }

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`font-medium ${getVariantClass(variant)}`}>
        {value}
      </span>
    </div>
  )
}