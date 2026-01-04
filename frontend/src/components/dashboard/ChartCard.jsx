import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ChartCard({
  title,
  description,
  children,
  height = 350,
  className = ""
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-0">
        <div className="w-full overflow-hidden" style={{ height: `${height}px` }}>
          {children}
        </div>
      </CardContent>
    </Card>
  )
}