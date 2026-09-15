import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

const PALETTE = [
  "#5b8def",
  "#6ec3a4",
  "#e9c46a",
  "#f2994a",
  "#e5484d",
  "#9b7de6",
  "#4fb8d4",
  "#d47fb0",
];

export interface BreakdownDatum {
  label: string;
  value: number;
}

export interface BreakdownBarChartProps {
  data: BreakdownDatum[];
  height?: number;
  valueFormatter?: (value: number) => string;
}

/** Horizontal bar chart for ranked dimension breakdowns (top N by spend, etc). */
export function BreakdownBarChart({ data, height = 320, valueFormatter }: BreakdownBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
      >
        <CartesianGrid stroke="#22314f" strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: "#5f6f92", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => (valueFormatter ? valueFormatter(v) : String(v))}
        />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fill: "#93a2c0", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={140}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
          contentStyle={{
            background: "#111a2e",
            border: "1px solid #22314f",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value) => [
            typeof value === "number" && valueFormatter ? valueFormatter(value) : String(value),
            "Net Spend",
          ]}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={18}>
          {data.map((_, idx) => (
            <Cell key={idx} fill={PALETTE[idx % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
