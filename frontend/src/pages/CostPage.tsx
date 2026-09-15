import { useState } from "react";
import { useApiData } from "../hooks/useApiData";
import {
  getCostSummary,
  getCostTrends,
  getCostByDimension,
  getCostResources,
} from "../services/analyticsApi";
import type { CostDimension } from "../types/api";
import { DataView } from "../components/ui/DataView";
import { KpiCard } from "../components/ui/KpiCard";
import { Section } from "../components/ui/Section";
import { TrendChart } from "../components/charts/TrendChart";
import { BreakdownBarChart } from "../components/charts/BreakdownBarChart";
import { formatCurrency, formatDate, formatPercent } from "../lib/format";
import { DollarSign, Percent, TrendingDown } from "lucide-react";

const DIMENSIONS: { value: CostDimension; label: string }[] = [
  { value: "service", label: "Service" },
  { value: "region", label: "Region" },
  { value: "department", label: "Department" },
];

export function CostPage() {
  const [dimension, setDimension] = useState<CostDimension>("service");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const summary = useApiData(getCostSummary, []);
  const trends = useApiData(getCostTrends, []);
  const breakdown = useApiData(() => getCostByDimension(dimension), [dimension]);
  const resources = useApiData(
    () => getCostResources({ page, page_size: 10, search: search || undefined }),
    [page, search]
  );

  return (
    <div className="flex flex-col gap-6">
      <DataView {...summary}>
        {(d) => (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard
              label="Total Net Spend"
              value={formatCurrency(d.total_net_cost_usd, { compact: true })}
              icon={<DollarSign size={16} />}
            />
            <KpiCard
              label="Total List Cost"
              value={formatCurrency(d.total_list_cost_usd, { compact: true })}
              icon={<DollarSign size={16} />}
            />
            <KpiCard
              label="Discounts Realized"
              value={formatCurrency(d.total_discounts_usd, { compact: true })}
              icon={<Percent size={16} />}
              subtext={`${formatPercent(
                (d.total_discounts_usd / d.total_list_cost_usd) * 100
              )} of list cost`}
            />
            <KpiCard
              label="Avg Daily Spend"
              value={formatCurrency(d.avg_daily_cost_usd)}
              icon={<TrendingDown size={16} />}
              subtext={d.pricing_consistency_verified ? "Pricing verified consistent" : "Pricing inconsistency detected"}
            />
          </div>
        )}
      </DataView>

      <Section title="Cost Trend Over Time" subtitle="Daily net spend with 7-day and 30-day rolling averages">
        <DataView {...trends} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <TrendChart
              data={data}
              xKey="usage_date"
              series={[
                { key: "net_cost_usd", name: "Net Cost", color: "#5b8def" },
                { key: "rolling_7d", name: "7-Day Avg", color: "#6ec3a4", dashed: true },
                { key: "rolling_30d", name: "30-Day Avg", color: "#e9c46a", dashed: true },
              ]}
              height={320}
              valueFormatter={(v) => formatCurrency(v, { compact: true })}
            />
          )}
        </DataView>
      </Section>

      <Section
        title="Cost Breakdown"
        subtitle="Net spend by dimension"
        action={
          <div className="flex rounded-lg border border-surface-border overflow-hidden text-xs">
            {DIMENSIONS.map((d) => (
              <button
                key={d.value}
                onClick={() => setDimension(d.value)}
                className={`px-3 py-1.5 transition-colors ${
                  dimension === d.value
                    ? "bg-brand-500/20 text-brand-400"
                    : "text-ink-faint hover:text-ink hover:bg-surface-raised"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        }
      >
        <DataView {...breakdown} isEmpty={(d) => d.length === 0}>
          {(data) => (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BreakdownBarChart
                data={data.map((d) => ({ label: d.dimension_value, value: d.net_cost_usd }))}
                height={Math.max(240, data.length * 40)}
                valueFormatter={(v) => formatCurrency(v, { compact: true })}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-ink-faint border-b border-surface-border">
                      <th className="py-2 font-medium">{DIMENSIONS.find((x) => x.value === dimension)?.label}</th>
                      <th className="py-2 font-medium text-right">Net Spend</th>
                      <th className="py-2 font-medium text-right">Share</th>
                      <th className="py-2 font-medium text-right">Resources</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row) => (
                      <tr key={row.dimension_value} className="border-b border-surface-border/60">
                        <td className="py-2 text-ink">{row.dimension_value}</td>
                        <td className="py-2 text-right text-ink tabular-nums">
                          {formatCurrency(row.net_cost_usd)}
                        </td>
                        <td className="py-2 text-right text-ink-faint tabular-nums">
                          {formatPercent(row.spend_share_pct)}
                        </td>
                        <td className="py-2 text-right text-ink-faint tabular-nums">
                          {row.active_resources_count}
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
        title="Top Cost Resources"
        subtitle="Search and page through the most expensive cloud assets"
        action={
          <input
            type="text"
            placeholder="Search resources…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="rounded-lg bg-surface-raised border border-surface-border px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        }
      >
        <DataView {...resources} isEmpty={(d) => d.items.length === 0} emptyMessage="No matching resources.">
          {(data) => (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-ink-faint border-b border-surface-border">
                      <th className="py-2 font-medium">Resource</th>
                      <th className="py-2 font-medium">Service</th>
                      <th className="py-2 font-medium">Region</th>
                      <th className="py-2 font-medium">Department</th>
                      <th className="py-2 font-medium text-right">Total Spend</th>
                      <th className="py-2 font-medium text-right">Avg / Day</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((r) => (
                      <tr key={r.resource_id} className="border-b border-surface-border/60">
                        <td className="py-2 text-ink">
                          {r.resource_name}
                          <div className="text-xs text-ink-faint font-mono">{r.resource_id}</div>
                        </td>
                        <td className="py-2 text-ink-muted">{r.service_name}</td>
                        <td className="py-2 text-ink-muted">{r.region_name}</td>
                        <td className="py-2 text-ink-muted">{r.department}</td>
                        <td className="py-2 text-right text-ink tabular-nums">
                          {formatCurrency(r.total_net_spend_usd)}
                        </td>
                        <td className="py-2 text-right text-ink-faint tabular-nums">
                          {formatCurrency(r.avg_daily_spend_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between pt-3 text-xs text-ink-faint">
                <span>
                  Page {data.page} of {data.total_pages} · {data.total_items} resources
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={data.page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="rounded-md border border-surface-border px-2.5 py-1 disabled:opacity-40 hover:bg-surface-raised"
                  >
                    Previous
                  </button>
                  <button
                    disabled={data.page >= data.total_pages}
                    onClick={() => setPage((p) => p + 1)}
                    className="rounded-md border border-surface-border px-2.5 py-1 disabled:opacity-40 hover:bg-surface-raised"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </DataView>
      </Section>
      <p className="text-xs text-ink-faint">
        Dates shown reflect the dataset's synthetic time span. Example latest date:{" "}
        {trends.data && trends.data.length > 0
          ? formatDate(trends.data[trends.data.length - 1].usage_date)
          : "—"}
      </p>
    </div>
  );
}
