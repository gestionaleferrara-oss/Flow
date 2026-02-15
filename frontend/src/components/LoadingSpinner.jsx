import { cn } from '@/lib/utils';

export default function LoadingSpinner({ fullScreen, size = 'md', className }) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-14 h-14'
  };

  const spinner = (
    <div className={cn('relative', sizeClasses[size], className)}>
      {/* Outer ring */}
      <div className="absolute inset-0 rounded-full border-2 border-white/10" />
      {/* Animated ring */}
      <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
      {/* Inner glow */}
      <div className="absolute inset-2 rounded-full bg-blue-500/10 blur-sm animate-pulse" />
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex flex-col items-center justify-center 
        bg-slate-900/90 backdrop-blur-sm z-50">
        {spinner}
        <p className="mt-4 text-sm text-slate-400 animate-pulse">Caricamento...</p>
      </div>
    );
  }

  return spinner;
}
