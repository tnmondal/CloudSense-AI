import { TrendingUp, Target, Calendar } from "lucide-react";
import { useApiData } from "../hooks/useApiData";
import { getForecastSummary, getForecastModels, getForecastProjections, getCostTrends } from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { TrendChart } from "../components/charts/TrendChart";
import { formatCurrency, formatPercent } from "../lib/format";

export function ForecastPage() {
  const summary = useApiData(getForecastSummary, []);
  const models = useApiData(getForecastModels, []);
  const projections = useApiData(() => getForecastProjections(30), []);
  const history = useApiData(getCostTrends, []);

  // Combine the tail of historical actuals with the forecast horizon so the
  // chart reads as one continuous timeline, exactly as returned by the API —
  // no values are invented, only the two already-fetched series are merged.
  const combinedSeries = (() => {
    if (!history.data || !projections.data) return null;
    const recentHistory = history.data.slice(-30).map((h) => ({
      date: h.usage_date,
      actual_cost_usd: h.net_cost_usd,
      predicted_cost_usd: null as number | null,
    }));
    const forecastPoints = projections.data.predictions.map((p) => ({
      date: p.date,
      actual_cost_usd: null as number | null,
      predicted_cost_usd: p.predicted_cost_usd,
      lower_bound_80_usd: p.lower_bound_80_usd,
      upper_bound_80_usd: p.upper_bound_80_usd,
    }));
    return [...recentHistory, ...forecastPoints];
  })();

  return (
    <div className="flex flex-col gap-6">
      <DataView {...summary}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard
              label="Champion Model"
              value={d.champion_model}
              icon={<Target size={16} />}
              subtext={`Forecasting ${d.target_metric.replace(/_/g, " ")}`}
            />
            <KpiCard
              label="Projected Monthly Spend"
              value={formatCurrency(d.projected_monthly_spend_usd, { compact: true })}
              icon={<TrendingUp size={16} />}
            />
            <KpiCard
              label="Training Window"
              value={d.train_horizon}
              icon={<Calendar size={16} />}
            />
            <KpiCard
              label="Holdout Evaluation Window"
              value={d.test_horizon}
              icon={<Calendar size={16} />}
              subtext="Chronological split — never shuffled"
            />
          </div>
        )}
      </DataView>

      <Section
        title="Historical Spend + 30-Day Forecast"
        subtitle="Last 30 days of actuals followed by the champion model's projection"
      >
        {combinedSeries ? (
          combinedSeries.length === 0 ? (
            <p className="text-sm text-ink-faint py-8 text-center">No data available.</p>
          ) : (
            <TrendChart
              data={combinedSeries}
              xKey="date"
              series={[
                { key: "actual_cost_usd", name: "Actual", color: "#5b8def" },
                { key: "predicted_cost_usd", name: "Forecast", color: "#e9c46a", dashed: true },
              ]}
              height={320}
              valueFormatter={(v) => formatCurrency(v, { compact: true })}
            />
          )
        ) : (
          <p className="text-sm text-ink-faint py-8 text-center">Loading…</p>
        )}
      </Section>

      <Section
        title="Model Benchmark"
        subtitle="Baseline vs. Ridge Regression vs. Random Forest, evaluated on a chronological holdout"
      >
        <DataView {...models} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-ink-faint border-b border-surface-border">
                    <th className="py-2 font-medium">Model</th>
                    <th className="py-2 font-medium text-right">MAE</th>
                    <th className="py-2 font-medium text-right">RMSE</th>
                    <th className="py-2 font-medium text-right">MAPE</th>
                    <th className="py-2 font-medium text-right">Train / Test Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {data
                    .slice()
                    .sort((a, b) => a.mape_pct - b.mape_pct)
                    .map((m) => (
                      <tr key={m.model_name} className="border-b border-surface-border/60">
                        <td className="py-2 text-ink">
                          {m.model_name}
                          {m.model_name === models.data?.slice().sort((a, b) => a.mape_pct - b.mape_pct)[0]?.model_name && (
                            <span className="pill ml-2 bg-positive/15 text-positive border border-positive/30">
                              Champion
                            </span>
                          )}
                        </td>
                        <td className="py-2 text-right text-ink-muted tabular-nums">
                          {formatCurrency(m.mae)}
                        </td>
                        <td className="py-2 text-right text-ink-muted tabular-nums">
                          {formatCurrency(m.rmse)}
                        </td>
                        <td className="py-2 text-right text-ink-muted tabular-nums">
                          {formatPercent(m.mape_pct)}
                        </td>
                        <td className="py-2 text-right text-ink-faint tabular-nums">
                          {m.train_samples} / {m.test_samples}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </DataView>
      </Section>

      <Section title="30-Day Projection Detail" subtitle="Daily predicted spend with 80%/95% confidence bounds">
        <DataView {...projections} isEmpty={(d) => d.predictions.length === 0}>
          {(data) => (
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-panel">
                  <tr className="text-left text-ink-faint border-b border-surface-border">
                    <th className="py-2 font-medium">Date</th>
                    <th className="py-2 font-medium text-right">Predicted</th>
                    <th className="py-2 font-medium text-right">80% Range</th>
                    <th className="py-2 font-medium text-right">95% Range</th>
                  </tr>
                </thead>
                <tbody>
                  {data.predictions.map((p) => (
                    <tr key={p.date} className="border-b border-surface-border/60">
                      <td className="py-2 text-ink">{p.date}</td>
                      <td className="py-2 text-right text-ink tabular-nums">
                        {formatCurrency(p.predicted_cost_usd)}
                      </td>
                      <td className="py-2 text-right text-ink-faint tabular-nums">
                        {formatCurrency(p.lower_bound_80_usd)} – {formatCurrency(p.upper_bound_80_usd)}
                      </td>
                      <td className="py-2 text-right text-ink-faint tabular-nums">
                        {formatCurrency(p.lower_bound_95_usd)} – {formatCurrency(p.upper_bound_95_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataView>
      </Section>
    </div>
  );
}
