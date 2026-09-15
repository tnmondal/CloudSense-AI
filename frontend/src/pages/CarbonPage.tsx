import { useState } from "react";
import { Leaf, Zap, Globe2, ArrowRightLeft } from "lucide-react";
import { useApiData } from "../hooks/useApiData";
import {
  getCarbonSummary,
  getCarbonByRegion,
  getCarbonTrends,
  simulateGreenMigration,
} from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section, DisclaimerBanner } from "../components/ui/Section";
import { TrendChart } from "../components/charts/TrendChart";
import { BreakdownBarChart } from "../components/charts/BreakdownBarChart";
import { formatCarbonMass, formatEnergy, formatNumber } from "../lib/format";
import { toApiError, type ApiError } from "../services/apiClient";

export function CarbonPage() {
  const summary = useApiData(getCarbonSummary, []);
  const byRegion = useApiData(getCarbonByRegion, []);
  const trends = useApiData(getCarbonTrends, []);

  const [selectedResource, setSelectedResource] = useState("");
  const [selectedTargetRegion, setSelectedTargetRegion] = useState("europe-west6");
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<ApiError | null>(null);

  const runSimulation = async () => {
    if (!selectedResource.trim()) return;
    setSimLoading(true);
    setSimError(null);
    setSimResult(null);
    try {
      const result = await simulateGreenMigration(selectedResource.trim(), selectedTargetRegion);
      setSimResult(result as Record<string, unknown>);
    } catch (err) {
      setSimError(toApiError(err));
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <DataView {...summary}>
        {(d) => (
          <>
            <DisclaimerBanner>{d.disclaimer}</DisclaimerBanner>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-4">
              <KpiCard
                label="Total Estimated Carbon"
                value={formatCarbonMass(d.total_carbon_kg_co2e)}
                icon={<Leaf size={16} />}
              />
              <KpiCard
                label="Scope 2 (Operational)"
                value={formatCarbonMass(d.total_scope2_operational_kg_co2e)}
                icon={<Zap size={16} />}
                subtext="Location-based grid electricity"
              />
              <KpiCard
                label="Scope 3 (Embodied)"
                value={formatCarbonMass(d.total_scope3_embodied_kg_co2e)}
                icon={<Globe2 size={16} />}
                subtext="Hardware manufacturing footprint"
              />
              <KpiCard
                label="Total Energy Consumed"
                value={formatEnergy(d.total_energy_consumed_kwh)}
                icon={<Zap size={16} />}
                subtext={`${d.avg_carbon_intensity_gco2_per_dollar.toFixed(1)} gCO\u2082e / $ spent`}
              />
            </div>
          </>
        )}
      </DataView>

      <Section title="Carbon Trend Over Time" subtitle="Daily estimated emissions with 7-day rolling average">
        <DataView {...trends} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <TrendChart
              data={data}
              xKey="usage_date"
              series={[
                { key: "total_carbon_kg", name: "Daily Carbon (kg)", color: "#6ec3a4" },
                { key: "rolling_7d_carbon", name: "7-Day Avg", color: "#5b8def", dashed: true },
              ]}
              valueFormatter={(v) => `${formatNumber(v, { compact: true })} kg`}
            />
          )}
        </DataView>
      </Section>

      <Section title="Carbon by Region" subtitle="Regional grid intensity drives most of the variance">
        <DataView {...byRegion} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BreakdownBarChart
                data={data.map((r) => ({ label: r.region_name, value: r.total_carbon_kg_co2e }))}
                height={Math.max(220, data.length * 44)}
                valueFormatter={(v) => `${formatNumber(v, { compact: true })} kg`}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-ink-faint border-b border-surface-border">
                      <th className="py-2 font-medium">Region</th>
                      <th className="py-2 font-medium text-right">Grid Intensity</th>
                      <th className="py-2 font-medium text-right">Total Carbon</th>
                      <th className="py-2 font-medium text-right">gCO₂e / $</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((r) => (
                      <tr key={r.region_id} className="border-b border-surface-border/60">
                        <td className="py-2 text-ink">{r.region_name}</td>
                        <td className="py-2 text-right text-ink-muted tabular-nums">
                          {r.grid_intensity_gco2_per_kwh.toFixed(0)} g/kWh
                        </td>
                        <td className="py-2 text-right text-ink tabular-nums">
                          {formatCarbonMass(r.total_carbon_kg_co2e)}
                        </td>
                        <td className="py-2 text-right text-ink-muted tabular-nums">
                          {r.carbon_per_dollar_gco2e.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </DataView>
      </Section>

      <Section
        title="Green Migration Simulator"
        subtitle="Estimate the carbon impact of relocating a resource to a lower-carbon-intensity region"
      >
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
          <div className="flex-1">
            <label htmlFor="resource-id" className="block text-xs text-ink-faint mb-1">
              Resource ID
            </label>
            <input
              id="resource-id"
              type="text"
              placeholder="e.g. gke-pool-core-012"
              value={selectedResource}
              onChange={(e) => setSelectedResource(e.target.value)}
              className="w-full rounded-lg bg-surface-raised border border-surface-border px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="sm:w-56">
            <label htmlFor="target-region" className="block text-xs text-ink-faint mb-1">
              Target Region
            </label>
            <input
              id="target-region"
              type="text"
              value={selectedTargetRegion}
              onChange={(e) => setSelectedTargetRegion(e.target.value)}
              className="w-full rounded-lg bg-surface-raised border border-surface-border px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <button
            onClick={runSimulation}
            disabled={simLoading || !selectedResource.trim()}
            className="flex items-center justify-center gap-2 rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 transition-colors"
          >
            <ArrowRightLeft size={15} />
            {simLoading ? "Simulating\u2026" : "Simulate"}
          </button>
        </div>

        {simError && (
          <p className="text-xs text-severity-critical mt-3">{simError.message}</p>
        )}

        {simResult && (
          <pre className="mt-4 rounded-lg border border-surface-border bg-surface-raised p-3 text-xs text-ink-muted overflow-x-auto">
            {JSON.stringify(simResult, null, 2)}
          </pre>
        )}

        <p className="text-xs text-ink-faint mt-3">
          Enter a real resource ID from the Cost Analytics resource table (e.g. one shown in
          the "Top Cost Resources" list) to simulate migrating it to a target region ID such as{" "}
          <code className="text-ink-muted">europe-west6</code> (Zurich) or{" "}
          <code className="text-ink-muted">us-central1</code> (Iowa).
        </p>
      </Section>
    </div>
  );
}
