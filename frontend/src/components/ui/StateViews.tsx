import { AlertTriangle, Inbox, Loader2, WifiOff } from "lucide-react";
import type { ApiError } from "../../services/apiClient";

export function LoadingState({ label = "Loading data\u2026" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-faint">
      <Loader2 className="animate-spin" size={26} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function InlineLoading() {
  return (
    <div className="flex items-center gap-2 text-ink-faint text-sm">
      <Loader2 className="animate-spin" size={14} />
      Loading…
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: ApiError;
  onRetry?: () => void;
}) {
  const Icon = error.isNetworkError ? WifiOff : AlertTriangle;
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
      <Icon className="text-severity-high" size={26} />
      <p className="text-sm text-ink-muted max-w-md">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-lg border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-ink hover:bg-surface-border transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message = "No data available." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-faint">
      <Inbox size={26} />
      <span className="text-sm">{message}</span>
    </div>
  );
}
