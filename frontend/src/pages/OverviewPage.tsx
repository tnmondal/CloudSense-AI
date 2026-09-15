import { DollarSign, AlertTriangle, Sparkles, Leaf, Cpu, TrendingUp } from "lucide-react";
import { useApiData } from "../hooks/useApiData";
import {
  getDashboardSummary,
  getCostTrends,
  getCostByDimension,
  getAnomalies,
  getOptimizations,
} from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { TrendChart } from "../components/charts/TrendChart";
import { BreakdownBarChart } from "../components/charts/BreakdownBarChart";
import { formatCurrency, formatPercent, formatSignedPercent, formatCarbonMass } from "../lib/format";
import { optimizationCategoryLabel } from "../lib/severity";

export function OverviewPage() {
  const dashboard = useApiData(getDashboardSummary, []);
  const trends = useApiData(getCostTrends, []);
  const byService = useApiData(() => getCostByDimension("service"), []);
  const anomalies = useApiData(() => getAnomalies({ limit: 5 }), []);
  const optimizations = useApiData(() => getOptimizations({ limit: 5 }), []);

  return (
    <div className="flex flex-col gap-6">
      <DataView {...dashboard} loadingLabel="Loading executive summary…">
        {(d) => {
          const latestTrend = trends.data?.[trends.data.length - 1];
          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <KpiCard
                label="Total Cloud Spend"
                value={formatCurrency(d.financial_kpis.total_net_spend_usd, { compact: true })}
                icon={<DollarSign size={16} />}
                trendLabel={latestTrend ? formatSignedPercent(latestTrend.mom_pct) : undefined}
                trendDirection={
                  latestTrend ? (latestTrend.mom_pct >= 0 ? "up" : "down") : "neutral"
                }
                trendPositiveIsGood={false}
                subtext={`${formatCurrency(d.financial_kpis.avg_daily_spend_usd)} / day avg`}
              />
              <KpiCard
                label="Active Anomalies"
                value={String(d.incident_kpis.active_anomalies_count)}
                icon={<AlertTriangle size={16} />}
                subtext={`${formatCurrency(d.incident_kpis.total_unbudgeted_dollar_surge_usd, {
                  compact: true,
                })} unbudgeted impact`}
              />
              <KpiCard
                label="Optimization Potential"
                value={formatCurrency(
                  d.optimization_kpis.total_potential_annual_savings_usd,
                  { compact: true }
                )}
                icon={<Sparkles size={16} />}
                subtext={`${d.optimization_kpis.total_actionable_recommendations} recommendations / year`}
              />
              <KpiCard
                label="Estimated Carbon"
                value={formatCarbonMass(d.environmental_kpis.total_carbon_kg_co2e)}
                icon={<Leaf size={16} />}
                subtext="Modeled estimate, not vendor-measured"
              />
            </div>
          );
        }}
      </DataView>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Section title="Daily Cost Trend" subtitle="Net spend with 7-day rolling average" className="xl:col-span-2">
          <DataView {...trends} isEmpty={(d) => d.length === 0}>
            {(data) => (
              <TrendChart
                data={data}
                xKey="usage_date"
                series={[
                  { key: "net_cost_usd", name: "Net Cost", color: "#5b8def" },
                  { key: "rolling_7d", name: "7-Day Avg", color: "#6ec3a4", dashed: true },
                ]}
                valueFormatter={(v) => formatCurrency(v, { compact: true })}
              />
            )}
          </DataView>
        </Section>

        <Section title="Top Spending Services" subtitle="Net cloud spend by service family">
          <DataView {...byService} isEmpty={(d) => d.length === 0}>
            {(data) => (
              <BreakdownBarChart
                data={data
                  .slice(0, 6)
                  .map((s) => ({ label: s.dimension_value, value: s.net_cost_usd }))}
                height={260}
                valueFormatter={(v) => formatCurrency(v, { compact: true })}
              />
            )}
          </DataView>
        </Section>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Section
          title="Recent Anomalies"
          subtitle={
            anomalies.data
              ? `${anomalies.data.total_anomalies} detected across the observation window`
              : undefined
          }
        >
          <DataView {...anomalies} isEmpty={(d) => d.items.length === 0} emptyMessage="No anomalies detected.">
            {(data) => (
              <ul className="flex flex-col divide-y divide-surface-border">
                {data.items.map((a) => (
                  <li key={a.anomaly_id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <div className="text-sm text-ink truncate">{a.target_id}</div>
                      <div className="text-xs text-ink-faint truncate">{a.explanation}</div>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <SeverityBadge severity={a.severity} />
                      <span className="text-xs text-ink-faint">
                        {formatCurrency(a.financial_impact_usd, { compact: true })}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </DataView>
        </Section>

        <Section
          title="Top Optimization Opportunities"
          subtitle={
            optimizations.data
              ? `${formatCurrency(optimizations.data.total_potential_annual_savings_usd, { compact: true })} potential annual savings`
              : undefined
          }
        >
          <DataView {...optimizations} isEmpty={(d) => d.items.length === 0} emptyMessage="No recommendations found.">
            {(data) => (
              <ul className="flex flex-col divide-y divide-surface-border">
                {data.items.map((o) => (
                  <li key={o.recommendation_id as string} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <div className="text-sm text-ink truncate">{o.resource_name as string}</div>
                      <div className="text-xs text-ink-faint truncate">
                        {optimizationCategoryLabel(o.optimization_category as string)}
                      </div>
                    </div>
                    <span className="text-sm text-positive font-medium shrink-0">
                      {formatCurrency(o.current_monthly_cost_usd as number, { compact: true })}/mo
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </DataView>
        </Section>
      </div>

      <DataView {...dashboard}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Section title="Fleet Utilization" subtitle="Mean CPU / RAM across the estate">
              <div className="flex items-center gap-3">
                <Cpu size={20} className="text-brand-400" />
                <div>
                  <div className="text-lg font-semibold text-ink">
                    {formatPercent(d.efficiency_kpis.overall_mean_cpu_pct)} CPU
                  </div>
                  <div className="text-xs text-ink-faint">
                    {formatPercent(d.efficiency_kpis.overall_mean_ram_pct)} RAM average
                  </div>
                </div>
              </div>
            </Section>
            <Section title="Idle Waste" subtitle="Compute paid for but unused">
              <div className="text-lg font-semibold text-negative">
                {formatCurrency(d.efficiency_kpis.idle_dollar_waste_usd, { compact: true })}
              </div>
              <div className="text-xs text-ink-faint mt-1">
                {d.efficiency_kpis.idle_hours_wasted.toLocaleString()} idle compute-hours
              </div>
            </Section>
            <Section title="30-Day Forecast" subtitle={`Champion model: ${d.forecast_kpis.champion_forecasting_model}`}>
              <div className="flex items-center gap-3">
                <TrendingUp size={20} className="text-brand-400" />
                <div className="text-lg font-semibold text-ink">
                  {formatCurrency(d.forecast_kpis.projected_next_30_days_spend_usd, { compact: true })}
                </div>
              </div>
            </Section>
          </div>
        )}
      </DataView>
    </div>
  );
}
