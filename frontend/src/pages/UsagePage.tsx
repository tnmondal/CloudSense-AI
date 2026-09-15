import { Cpu, MemoryStick, Clock, AlertOctagon } from "lucide-react";
import { useApiData } from "../hooks/useApiData";
import { getUsageSummary, getServiceUtilization, getUtilizationCorrelations } from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { formatCurrency, formatNumber, formatPercent } from "../lib/format";

export function UsagePage() {
  const summary = useApiData(getUsageSummary, []);
  const services = useApiData(getServiceUtilization, []);
  const correlations = useApiData(getUtilizationCorrelations, []);

  return (
    <div className="flex flex-col gap-6">
      <DataView {...summary}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard
              label="Mean CPU Utilization"
              value={formatPercent(d.overall_mean_cpu_pct)}
              icon={<Cpu size={16} />}
              subtext={`P95: ${formatPercent(d.overall_p95_cpu_pct)}`}
            />
            <KpiCard
              label="Mean RAM Utilization"
              value={formatPercent(d.overall_mean_ram_pct)}
              icon={<MemoryStick size={16} />}
              subtext={`P95: ${formatPercent(d.overall_p95_ram_pct)}`}
            />
            <KpiCard
              label="Total Compute Hours"
              value={formatNumber(d.total_compute_hours, { compact: true })}
              icon={<Clock size={16} />}
              subtext={`${formatNumber(d.total_idle_hours, { compact: true })} idle hours`}
            />
            <KpiCard
              label="Idle Cost Waste"
              value={formatCurrency(d.idle_cost_waste_usd, { compact: true })}
              icon={<AlertOctagon size={16} />}
              subtext="Paid for, never used"
            />
          </div>
        )}
      </DataView>

      <Section title="Utilization by Service Family" subtitle="CPU / RAM / storage / network profile per service">
        <DataView {...services} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-ink-faint border-b border-surface-border">
                    <th className="py-2 font-medium">Service</th>
                    <th className="py-2 font-medium text-right">Mean CPU</th>
                    <th className="py-2 font-medium text-right">P95 CPU</th>
                    <th className="py-2 font-medium text-right">Mean RAM</th>
                    <th className="py-2 font-medium text-right">Compute Hrs</th>
                    <th className="py-2 font-medium text-right">Storage (GB)</th>
                    <th className="py-2 font-medium text-right">Egress (GB)</th>
                    <th className="py-2 font-medium text-right">Requests</th>
                    <th className="py-2 font-medium text-right">Idle Assets</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((s) => (
                    <tr key={s.service_family} className="border-b border-surface-border/60">
                      <td className="py-2 text-ink">{s.service_family}</td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatPercent(s.mean_cpu_pct)}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatPercent(s.p95_cpu_pct)}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatPercent(s.mean_ram_pct)}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatNumber(s.total_compute_hours, { compact: true })}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatNumber(s.total_storage_gb, { compact: true })}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatNumber(s.total_network_egress_gb, { compact: true })}
                      </td>
                      <td className="py-2 text-right text-ink-muted tabular-nums">
                        {formatNumber(s.total_requests, { compact: true })}
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        {s.idle_resources_count > 0 ? (
                          <span className="text-severity-medium">{s.idle_resources_count}</span>
                        ) : (
                          <span className="text-ink-faint">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataView>
      </Section>

      <Section
        title="Load-to-Cost Correlations"
        subtitle="Empirical Pearson / Spearman correlations between workload utilization and billed cost"
      >
        <DataView {...correlations} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.map((c) => (
                <div key={c.workload_type} className="rounded-lg border border-surface-border p-3">
                  <div className="text-sm text-ink font-medium">{c.workload_type}</div>
                  <div className="flex gap-4 mt-2 text-xs">
                    <span className="text-ink-faint">
                      Pearson: <span className="text-ink tabular-nums">{c.pearson_correlation.toFixed(3)}</span>
                    </span>
                    <span className="text-ink-faint">
                      Spearman: <span className="text-ink tabular-nums">{c.spearman_correlation.toFixed(3)}</span>
                    </span>
                  </div>
                  <p className="text-xs text-ink-muted mt-2">{c.interpretation}</p>
                </div>
              ))}
            </div>
          )}
        </DataView>
      </Section>
    </div>
  );
}
