import type { ReactNode } from "react";
import type { ApiError } from "../../services/apiClient";
import { EmptyState, ErrorState, LoadingState } from "./StateViews";

export interface DataViewProps<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  onRetry?: () => void;
  isEmpty?: (data: T) => boolean;
  emptyMessage?: string;
  loadingLabel?: string;
  children: (data: T) => ReactNode;
}

/**
 * Standard loading -> error -> empty -> content lifecycle for any page/section
 * backed by `useApiData`. Keeps this branching logic out of every page.
 */
export function DataView<T>({
  data,
  loading,
  error,
  onRetry,
  isEmpty,
  emptyMessage,
  loadingLabel,
  children,
}: DataViewProps<T>) {
  if (loading && data === null) {
    return <LoadingState label={loadingLabel} />;
  }
  if (error) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }
  if (data === null) {
    return <EmptyState message={emptyMessage} />;
  }
  if (isEmpty && isEmpty(data)) {
    return <EmptyState message={emptyMessage} />;
  }
  return <>{children(data)}</>;
}
