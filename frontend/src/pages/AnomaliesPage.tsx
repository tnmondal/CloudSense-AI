import { useState } from "react";
import { useApiData } from "../hooks/useApiData";
import { getAnomalies } from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { formatCurrency, formatDate, formatNumber } from "../lib/format";
import { AlertTriangle, DollarSign, ListChecks } from "lucide-react";
import type { AnomalySeverity } from "../types/api";

const SEVERITIES: AnomalySeverity[] = ["Critical", "High", "Medium", "Low"];

export function AnomaliesPage() {
  const [severity, setSeverity] = useState<AnomalySeverity | "All">("All");

  const anomalies = useApiData(
    () => getAnomalies({ severity: severity === "All" ? undefined : severity, limit: 50 }),
    [severity]
  );

  return (
    <div className="flex flex-col gap-6">
      <DataView {...anomalies}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              label="Total Anomalies"
              value={String(d.total_anomalies)}
              icon={<ListChecks size={16} />}
              subtext="Across the full observation window"
            />
            <KpiCard
              label="Unbudgeted Dollar Impact"
              value={formatCurrency(d.total_unbudgeted_dollar_impact, { compact: true })}
              icon={<DollarSign size={16} />}
            />
            <KpiCard
              label="Critical Incidents"
              value={String(d.anomalies_by_severity.Critical ?? 0)}
              icon={<AlertTriangle size={16} />}
              subtext={`${d.anomalies_by_severity.High ?? 0} high severity`}
            />
          </div>
        )}
      </DataView>

      <Section
        title="Detected Anomalies"
        subtitle="Statistical outliers flagged by Rolling Z-Score, Modified MAD, and IQR consensus"
        action={
          <div className="flex rounded-lg border border-surface-border overflow-hidden text-xs">
            <button
              onClick={() => setSeverity("All")}
              className={`px-3 py-1.5 transition-colors ${
                severity === "All"
                  ? "bg-brand-500/20 text-brand-400"
                  : "text-ink-faint hover:text-ink hover:bg-surface-raised"
              }`}
            >
              All
            </button>
            {SEVERITIES.map((s) => (
              <button
                key={s}
                onClick={() => setSeverity(s)}
                className={`px-3 py-1.5 transition-colors ${
                  severity === s
                    ? "bg-brand-500/20 text-brand-400"
                    : "text-ink-faint hover:text-ink hover:bg-surface-raised"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        }
      >
        <DataView
          {...anomalies}
          isEmpty={(d) => d.items.length === 0}
          emptyMessage="No anomalies match this filter."
        >
          {(data) => (
            <div className="flex flex-col divide-y divide-surface-border">
              {data.items.map((a) => (
                <div key={a.anomaly_id} className="py-3 flex flex-col sm:flex-row sm:items-center gap-3">
                  <div className="flex items-center gap-3 sm:w-56 shrink-0">
                    <SeverityBadge severity={a.severity} />
                    <span className="text-xs text-ink-faint font-mono">{a.anomaly_id}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink">
                      {a.target_id}{" "}
                      <span className="text-ink-faint font-normal">· {a.service_name}</span>
                    </div>
                    <p className="text-xs text-ink-muted mt-0.5">{a.explanation}</p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs text-ink-faint">
                      <span>{formatDate(a.timestamp)}</span>
                      <span>Method: {a.detection_method}</span>
                      <span>
                        Observed {formatNumber(a.observed_value, { decimals: 2 })} vs. expected{" "}
                        {formatNumber(a.expected_value, { decimals: 2 })}
                      </span>
                      <span>Score: {a.anomaly_score.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="text-right sm:w-32 shrink-0">
                    <div className="text-sm font-medium text-negative">
                      {formatCurrency(a.financial_impact_usd, { compact: true })}
                    </div>
                    <div className="text-[11px] text-ink-faint">impact</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataView>
      </Section>
    </div>
  );
}
