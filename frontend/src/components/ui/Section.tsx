import type { ReactNode } from "react";

export interface SectionProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ title, subtitle, action, children, className }: SectionProps) {
  return (
    <section className={`card ${className ?? ""}`}>
      <div className="card-header">
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          {subtitle && <p className="text-xs text-ink-faint mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="px-5 pb-5">{children}</div>
    </section>
  );
}

export function DisclaimerBanner({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-severity-medium/25 bg-severity-medium/10 px-3 py-2 text-xs text-severity-medium">
      <span className="mt-px">⚠</span>
      <span>{children}</span>
    </div>
  );
}
