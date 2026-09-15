import { useState } from "react";
import { useApiData } from "../hooks/useApiData";
import { getOptimizations } from "../services/analyticsApi";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { formatCurrency, formatCarbonMass } from "../lib/format";
import { optimizationCategoryLabel } from "../lib/severity";
import { Sparkles, PiggyBank, Leaf } from "lucide-react";
import type { OptimizationCategory } from "../types/api";

const CATEGORIES: OptimizationCategory[] = [
  "idle_zombie",
  "compute_rightsizing",
  "storage_lifecycle",
  "green_migration",
];

export function OptimizationPage() {
  const [category, setCategory] = useState<OptimizationCategory | "All">("All");

  const optimizations = useApiData(
    () => getOptimizations({ category: category === "All" ? undefined : category, limit: 50 }),
    [category]
  );

  return (
    <div className="flex flex-col gap-6">
      <DataView {...optimizations}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              label="Actionable Recommendations"
              value={String(d.total_recommendations)}
              icon={<Sparkles size={16} />}
            />
            <KpiCard
              label="Estimated Monthly Savings"
              value={formatCurrency(d.total_potential_monthly_savings_usd, { compact: true })}
              icon={<PiggyBank size={16} />}
              subtext={`${formatCurrency(d.total_potential_annual_savings_usd, { compact: true })} estimated / year`}
            />
            <KpiCard
              label="Avoidable Monthly Carbon"
              value={formatCarbonMass(d.total_potential_monthly_carbon_saved_kg)}
              icon={<Leaf size={16} />}
              subtext="If all recommendations are applied"
            />
          </div>
        )}
      </DataView>

      <Section
        title="Optimization Recommendations"
        subtitle="Estimated, rule-based savings — verify against your own change-management process before acting"
        action={
          <div className="flex flex-wrap rounded-lg border border-surface-border overflow-hidden text-xs">
            <button
              onClick={() => setCategory("All")}
              className={`px-3 py-1.5 transition-colors ${
                category === "All"
                  ? "bg-brand-500/20 text-brand-400"
                  : "text-ink-faint hover:text-ink hover:bg-surface-raised"
              }`}
            >
              All
            </button>
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={`px-3 py-1.5 transition-colors whitespace-nowrap ${
                  category === c
                    ? "bg-brand-500/20 text-brand-400"
                    : "text-ink-faint hover:text-ink hover:bg-surface-raised"
                }`}
              >
                {optimizationCategoryLabel(c)}
              </button>
            ))}
          </div>
        }
      >
        <DataView
          {...optimizations}
          isEmpty={(d) => d.items.length === 0}
          emptyMessage="No recommendations in this category."
        >
          {(data) => (
            <div className="flex flex-col divide-y divide-surface-border">
              {data.items.map((item) => (
                <div
                  key={item.recommendation_id}
                  className="py-3 flex flex-col lg:flex-row lg:items-center gap-3"
                >
                  <div className="lg:w-44 shrink-0">
                    <span className="pill bg-brand-500/10 text-brand-400 border border-brand-500/25">
                      {optimizationCategoryLabel(item.optimization_category)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink truncate">{item.resource_name}</div>
                    <div className="text-xs text-ink-faint font-mono truncate">
                      {item.affected_resource} · {item.department}
                    </div>
                    <p className="text-xs text-ink-muted mt-1">{item.reason}</p>
                    <p className="text-xs text-brand-400 mt-1">{item.action_item}</p>
                    <span className="text-[11px] text-ink-faint">Confidence: {item.confidence}</span>
                  </div>
                  <div className="text-right lg:w-40 shrink-0">
                    <div className="text-sm font-medium text-positive">
                      {formatCurrency(item.estimated_monthly_saving_usd, { compact: true })}/mo
                    </div>
                    <div className="text-[11px] text-ink-faint">
                      {formatCurrency(item.estimated_annual_saving_usd, { compact: true })}/yr estimated
                    </div>
                    {item.estimated_monthly_carbon_saved_kg > 0 && (
                      <div className="text-[11px] text-positive mt-0.5">
                        -{formatCarbonMass(item.estimated_monthly_carbon_saved_kg)}/mo
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataView>
      </Section>

      <p className="text-xs text-ink-faint">
        All savings figures are estimated recommendations generated by deterministic FinOps rules
        (idle/zombie detection, compute rightsizing, storage lifecycle, and green-region migration).
        They are not guaranteed outcomes.
      </p>
    </div>
  );
}
