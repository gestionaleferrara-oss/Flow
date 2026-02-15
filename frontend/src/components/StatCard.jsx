import { cn, formatCurrency } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function StatCard({ 
  label, 
  value, 
  trend, 
  trendValue, 
  icon: Icon,
  format = 'number',
  className 
}) {
  const formattedValue = format === 'currency' 
    ? formatCurrency(value) 
    : typeof value === 'number' 
      ? value.toLocaleString('it-IT')
      : value;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <div className={cn('stat-card', className)} data-testid="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-value text-foreground">{formattedValue}</p>
          <p className="stat-label">{label}</p>
          {trendValue !== undefined && (
            <div className={cn(
              'stat-trend',
              trend === 'up' && 'positive',
              trend === 'down' && 'negative'
            )}>
              <TrendIcon size={14} />
              <span>{trendValue}%</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-2 bg-primary/10 rounded-sm">
            <Icon className="w-5 h-5 text-primary" />
          </div>
        )}
      </div>
    </div>
  );
}
