import { Menu } from "lucide-react";
import { useApiData } from "../../hooks/useApiData";
import { getHealth } from "../../services/analyticsApi";

export function TopBar({
  title,
  onMenuClick,
}: {
  title: string;
  onMenuClick: () => void;
}) {
  const { data: health, error } = useApiData(getHealth, []);

  const isHealthy = !!health && health.status === "healthy";

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-surface-border bg-surface/85 backdrop-blur px-4 lg:px-6">
      <button
        className="lg:hidden text-ink-muted hover:text-ink"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>
      <h1 className="text-sm font-semibold text-ink">{title}</h1>

      <div className="ml-auto flex items-center gap-2 text-xs">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            error ? "bg-severity-critical" : isHealthy ? "bg-positive" : "bg-severity-medium"
          }`}
        />
        <span className="text-ink-faint hidden sm:inline">
          {error
            ? "Backend unreachable"
            : isHealthy
            ? "Backend connected"
            : "Checking backend…"}
        </span>
      </div>
    </header>
  );
}
