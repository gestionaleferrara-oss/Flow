import { cn } from '@/lib/utils';

export default function LoadingSpinner({ fullScreen, size = 'md', className }) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  };

  const spinner = (
    <div className={cn('relative', sizeClasses[size], className)}>
      {/* Soft glowing orbs animation */}
      <div className="absolute inset-0 rounded-full">
        <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-blue-400/30 to-cyan-400/30 blur-md animate-pulse" />
      </div>
      {/* Rotating gradient ring */}
      <div className="absolute inset-0 rounded-full animate-spin" style={{ animationDuration: '1.5s' }}>
        <div className="w-full h-full rounded-full bg-gradient-conic from-blue-500 via-transparent to-transparent" 
          style={{ 
            background: 'conic-gradient(from 0deg, rgba(59, 130, 246, 0.8), rgba(59, 130, 246, 0.4), rgba(59, 130, 246, 0.1), transparent 70%)',
            mask: 'radial-gradient(farthest-side, transparent calc(100% - 3px), white calc(100% - 3px))',
            WebkitMask: 'radial-gradient(farthest-side, transparent calc(100% - 3px), white calc(100% - 3px))'
          }} 
        />
      </div>
      {/* Soft center glow */}
      <div className="absolute inset-3 rounded-full bg-gradient-to-br from-blue-400/20 to-cyan-400/10 blur-sm" />
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center 
        bg-slate-900/80 backdrop-blur-md z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
}
