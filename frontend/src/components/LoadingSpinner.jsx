import { Loader2 } from 'lucide-react';

export default function LoadingSpinner({ fullScreen = false }) {
  if (fullScreen) {
    return (
      <div className="loader-overlay" data-testid="loading-spinner">
        <div className="loader-spinner" />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8" data-testid="loading-spinner">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );
}
