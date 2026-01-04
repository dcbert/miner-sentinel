export default function PeriodSelector({ periods, selectedPeriod, onPeriodChange }) {
  return (
    <div className="flex gap-2">
      {Object.entries(periods).map(([key, period]) => (
        <button
          key={key}
          onClick={() => onPeriodChange(key)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            selectedPeriod === key
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
          }`}
        >
          {period.label}
        </button>
      ))}
    </div>
  )
}