import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  DollarSign,
  Cpu,
  AlertTriangle,
  Sparkles,
  Leaf,
  TrendingUp,
  Bot,
  X,
  CloudCog,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/cost", label: "Cost Analytics", icon: DollarSign },
  { to: "/usage", label: "Usage & Utilization", icon: Cpu },
  { to: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { to: "/optimization", label: "Optimization", icon: Sparkles },
  { to: "/carbon", label: "Carbon / GreenOps", icon: Leaf },
  { to: "/forecast", label: "Forecast", icon: TrendingUp },
  { to: "/copilot", label: "AI FinOps Copilot", icon: Bot },
];

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {/* Mobile scrim */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed z-40 inset-y-0 left-0 w-64 shrink-0 border-r border-surface-border bg-surface-panel px-3 py-4 flex flex-col gap-1 transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-2 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/20 text-brand-400">
              <CloudCog size={18} />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-ink">CloudSense AI</div>
              <div className="text-[11px] text-ink-faint">FinOps Intelligence</div>
            </div>
          </div>
          <button
            className="lg:hidden text-ink-faint hover:text-ink"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link-active" : ""}`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto px-2 pt-4 text-[11px] text-ink-faint border-t border-surface-border">
          Synthetic dataset · 50,000 records · GCP-only
        </div>
      </aside>
    </>
  );
}
