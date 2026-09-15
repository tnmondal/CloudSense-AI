import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { formatShortDate } from "../../lib/format";

export interface TrendSeries {
  key: string;
  name: string;
  color: string;
  /** Renders as a dashed line without fill (useful for rolling averages). */
  dashed?: boolean;
}

export interface TrendChartProps<T> {
  data: T[];
  xKey: Extract<keyof T, string>;
  series: TrendSeries[];
  height?: number;
  valueFormatter?: (value: number) => string;
  xFormatter?: (value: string) => string;
}

/**
 * Generic time-series area chart used for cost trends, carbon trends, and
 * forecast projections. Renders one primary filled area plus any number of
 * additional dashed reference lines (e.g. rolling averages).
 *
 * Generic over the row type `T` so real API response arrays (e.g.
 * `CostTrendPoint[]`) can be passed directly without a lossy cast to
 * `Record<string, unknown>[]`.
 */
export function TrendChart<T>({
  data,
  xKey,
  series,
  height = 280,
  valueFormatter,
  xFormatter,
}: TrendChartProps<T>) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="#22314f" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey={xKey}
          tickFormatter={xFormatter ?? formatShortDate}
          tick={{ fill: "#5f6f92", fontSize: 11 }}
          axisLine={{ stroke: "#22314f" }}
          tickLine={false}
          minTickGap={32}
        />
        <YAxis
          tick={{ fill: "#5f6f92", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => (valueFormatter ? valueFormatter(v) : String(v))}
          width={64}
        />
        <Tooltip
          contentStyle={{
            background: "#111a2e",
            border: "1px solid #22314f",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelFormatter={(label) => (xFormatter ?? formatShortDate)(String(label))}
          formatter={(value, name) => [
            typeof value === "number" && valueFormatter ? valueFormatter(value) : String(value),
            String(name),
          ]}
        />
        {series.length > 1 && (
          <Legend wrapperStyle={{ fontSize: 12, color: "#93a2c0" }} />
        )}
        {series.map((s, idx) =>
          idx === 0 ? (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              fill={`url(#grad-${s.key})`}
            />
          ) : (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={1.5}
              strokeDasharray={s.dashed ? "4 3" : undefined}
              fill="transparent"
            />
          )
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
