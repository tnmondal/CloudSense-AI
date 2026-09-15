import { useCallback, useEffect, useRef, useState } from "react";
import { toApiError, type ApiError } from "../services/apiClient";

export interface UseApiDataState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => void;
}

/**
 * Fetches data from a promise-returning function, exposing a consistent
 * loading / error / data lifecycle so pages never need to reimplement it.
 *
 * `deps` behaves like a useEffect dependency array: the fetcher re-runs when
 * any of them change (e.g. a selected filter or date range).
 */
export function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = []
): UseApiDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ApiError | null>(null);
  const requestId = useRef(0);

  const load = useCallback(() => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (currentRequest === requestId.current) {
          setData(result);
        }
      })
      .catch((err) => {
        if (currentRequest === requestId.current) {
          setError(toApiError(err));
        }
      })
      .finally(() => {
        if (currentRequest === requestId.current) {
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  return { data, loading, error, refetch: load };
}
