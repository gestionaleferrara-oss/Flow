import { cn, formatCurrency } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

const gradientClasses = {
  blue: 'from-blue-500/20 to-blue-600/5 border-blue-500/20',
  purple: 'from-purple-500/20 to-purple-600/5 border-purple-500/20',
  cyan: 'from-cyan-500/20 to-cyan-600/5 border-cyan-500/20',
  amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/20',
  emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/20',
  pink: 'from-pink-500/20 to-pink-600/5 border-pink-500/20',
};

const iconColorClasses = {
  blue: 'text-blue-400 bg-blue-500/20',
  purple: 'text-purple-400 bg-purple-500/20',
  cyan: 'text-cyan-400 bg-cyan-500/20',
  amber: 'text-amber-400 bg-amber-500/20',
  emerald: 'text-emerald-400 bg-emerald-500/20',
  pink: 'text-pink-400 bg-pink-500/20',
};

export default function StatCard({ 
  label, value, trend, trendValue, icon: Icon,
  format = 'number', gradient = 'blue', subtitle, className, blurred = false
}) {
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const isBlurred = blurred && !pinned && !hovered;

  const formattedValue = format === 'currency' 
    ? formatCurrency(value) 
    : format === 'percent'
      ? `${value >= 0 ? '+' : ''}${value}%`
      : typeof value === 'number' 
        ? Math.abs(value).toLocaleString('it-IT')
        : value;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <div 
      className={cn(
        'relative overflow-hidden rounded-2xl p-5 transition-all duration-500',
        'bg-gradient-to-br border',
        'hover:scale-[1.02] hover:shadow-xl hover:shadow-black/20',
        gradientClasses[gradient] || gradientClasses.blue,
        className
      )} 
      data-testid="stat-card"
      onMouseEnter={blurred ? () => setHovered(true) : undefined}
      onMouseLeave={blurred ? () => setHovered(false) : undefined}
    >
      <div className="absolute -top-8 -right-8 w-24 h-24 rounded-full bg-white/5 blur-2xl" />
      
      <div className="relative z-10 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className={cn("transition-all duration-500 ease-out", isBlurred && "blur-md select-none")}>
            <p className="text-3xl font-bold tracking-tight text-white mb-1">
              {formattedValue}
            </p>
          </div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {label}
          </p>
          {subtitle && (
            <div className={cn("transition-all duration-500 ease-out", isBlurred && "blur-sm select-none")}>
              <p className="text-xs text-slate-500 mt-1 whitespace-pre-line">
                {subtitle}
              </p>
            </div>
          )}
          {trendValue !== undefined && (
            <div className={cn("transition-all duration-500 ease-out", isBlurred && "blur-sm select-none")}>
              <div className={cn(
                'inline-flex items-center gap-1 mt-2 px-2 py-1 rounded-md text-xs font-semibold',
                trend === 'up' && 'bg-emerald-500/10 text-emerald-400',
                trend === 'down' && 'bg-red-500/10 text-red-400',
                !trend && 'bg-slate-500/10 text-slate-400'
              )}>
                <TrendIcon size={12} />
                <span>{Math.abs(trendValue)}%</span>
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-col items-center gap-2">
          {Icon && (
            <div className={cn(
              'p-3 rounded-xl',
              iconColorClasses[gradient] || iconColorClasses.blue
            )}>
              <Icon className="w-5 h-5" />
            </div>
          )}
          {blurred && (
            <button
              onClick={(e) => { e.stopPropagation(); setPinned(p => !p); }}
              className={cn(
                "p-1.5 rounded-lg transition-all duration-300",
                pinned ? "bg-white/10 text-white" : "bg-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/10"
              )}
              data-testid="stat-card-eye"
            >
              <{pinned ? Eye : EyeOff} className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
