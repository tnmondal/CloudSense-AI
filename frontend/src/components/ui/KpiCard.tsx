import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

export interface KpiCardProps {
  label: string;
  value: string;
  icon?: ReactNode;
  trendLabel?: string;
  trendDirection?: "up" | "down" | "neutral";
  trendPositiveIsGood?: boolean;
  subtext?: string;
}

/**
 * A single KPI metric card: label, big value, optional trend indicator and
 * subtext. Used across the Overview and detail pages for consistent styling.
 */
export function KpiCard({
  label,
  value,
  icon,
  trendLabel,
  trendDirection = "neutral",
  trendPositiveIsGood = true,
  subtext,
}: KpiCardProps) {
  const isGood =
    trendDirection === "neutral"
      ? null
      : trendPositiveIsGood
      ? trendDirection === "up"
      : trendDirection === "down";

  return (
    <div className="card p-5 flex flex-col gap-3 min-w-0">
      <div className="flex items-center justify-between">
        <span className="card-title">{label}</span>
        {icon && <span className="text-ink-faint">{icon}</span>}
      </div>
      <div className="kpi-value truncate">{value}</div>
      {(trendLabel || subtext) && (
        <div className="flex items-center gap-2 text-xs text-ink-faint">
          {trendLabel && trendDirection !== "neutral" && (
            <span
              className={`inline-flex items-center gap-0.5 font-medium ${
                isGood ? "text-positive" : "text-negative"
              }`}
            >
              {trendDirection === "up" ? (
                <ArrowUpRight size={14} />
              ) : (
                <ArrowDownRight size={14} />
              )}
              {trendLabel}
            </span>
          )}
          {subtext && <span className="truncate">{subtext}</span>}
        </div>
      )}
    </div>
  );
}
