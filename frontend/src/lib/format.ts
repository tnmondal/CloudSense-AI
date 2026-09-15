export function formatCurrency(value: number, opts: { compact?: boolean } = {}): string {
  if (opts.compact) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number, opts: { compact?: boolean; decimals?: number } = {}): string {
  return new Intl.NumberFormat("en-US", {
    notation: opts.compact ? "compact" : "standard",
    maximumFractionDigits: opts.decimals ?? (opts.compact ? 1 : 0),
  }).format(value);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatSignedPercent(value: number, decimals = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatDate(isoDate: string): string {
  const d = new Date(isoDate + (isoDate.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function formatShortDate(isoDate: string): string {
  const d = new Date(isoDate + (isoDate.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Formats a mass in kilograms as kg or metric tonnes, whichever is more legible. */
export function formatCarbonMass(kg: number): string {
  if (Math.abs(kg) >= 1000) {
    return `${(kg / 1000).toFixed(2)} t CO\u2082e`;
  }
  return `${kg.toFixed(1)} kg CO\u2082e`;
}

export function formatEnergy(kwh: number): string {
  if (Math.abs(kwh) >= 1000) {
    return `${(kwh / 1000).toFixed(2)} MWh`;
  }
  return `${kwh.toFixed(1)} kWh`;
}
