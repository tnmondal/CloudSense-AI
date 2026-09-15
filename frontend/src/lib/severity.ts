export type Severity = "Critical" | "High" | "Medium" | "Low" | string;

export function severityColorClasses(severity: Severity): string {
  switch (severity) {
    case "Critical":
      return "bg-severity-critical/15 text-severity-critical border border-severity-critical/30";
    case "High":
      return "bg-severity-high/15 text-severity-high border border-severity-high/30";
    case "Medium":
      return "bg-severity-medium/15 text-severity-medium border border-severity-medium/30";
    case "Low":
      return "bg-severity-low/15 text-severity-low border border-severity-low/30";
    default:
      return "bg-ink-faint/15 text-ink-muted border border-ink-faint/30";
  }
}

export function severityDotClasses(severity: Severity): string {
  switch (severity) {
    case "Critical":
      return "bg-severity-critical";
    case "High":
      return "bg-severity-high";
    case "Medium":
      return "bg-severity-medium";
    case "Low":
      return "bg-severity-low";
    default:
      return "bg-ink-faint";
  }
}

const CATEGORY_LABELS: Record<string, string> = {
  idle_zombie: "Idle / Zombie Asset",
  compute_rightsizing: "Compute Rightsizing",
  storage_lifecycle: "Storage Lifecycle",
  green_migration: "Green Region Migration",
};

export function optimizationCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}
