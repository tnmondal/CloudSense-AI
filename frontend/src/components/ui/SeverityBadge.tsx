import { severityColorClasses, severityDotClasses } from "../../lib/severity";

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`pill ${severityColorClasses(severity)}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${severityDotClasses(severity)}`} />
      {severity}
    </span>
  );
}
