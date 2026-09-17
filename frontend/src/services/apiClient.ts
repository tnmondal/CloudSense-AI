import axios, { AxiosError } from "axios";

/**
 * Base URL of the FastAPI backend. Configured via VITE_API_BASE_URL
 * (see .env.example). Defaults to the local dev server.
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20_000,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * A normalized error shape used throughout the app so components don't need
 * to know whether a failure was a network error, a timeout, or a backend
 * validation/HTTP error.
 */
export interface ApiError {
  message: string;
  status?: number;
  isNetworkError: boolean;
  isTimeout: boolean;
}

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<{ detail?: string | { msg: string }[] }>;

    if (err.code === "ECONNABORTED") {
      return {
        message: "The request took too long to respond. Please try again.",
        isNetworkError: false,
        isTimeout: true,
      };
    }

    if (!err.response) {
      return {
        message:
          "Could not reach the CloudSense AI backend. Is the FastAPI server running?",
        isNetworkError: true,
        isTimeout: false,
      };
    }

    const detail = err.response.data?.detail;
    let message = err.message;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail.map((d) => d.msg).join("; ");
    }

    return {
      message,
      status: err.response.status,
      isNetworkError: false,
      isTimeout: false,
    };
  }

  return {
    message: error instanceof Error ? error.message : "An unknown error occurred.",
    isNetworkError: false,
    isTimeout: false,
  };
}
