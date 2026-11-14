import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
  accent?: "primary" | "secondary" | "neutral";
}

export function StatCard({
  label,
  value,
  helper,
  icon,
  accent = "neutral",
}: StatCardProps) {
  const accentClass =
    accent === "primary"
      ? "bg-app-primary-soft text-app-primary"
      : accent === "secondary"
        ? "bg-blue-50 text-blue-600"
        : "bg-slate-100 text-slate-600";

  return (
    <article className="app-card p-5" aria-label={label}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-app-muted">{label}</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-app-ink">
            {value}
          </p>
          <p className="mt-1 text-xs text-app-muted">{helper}</p>
        </div>
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-control ${accentClass}`}
          aria-hidden="true"
        >
          {icon}
        </div>
      </div>
    </article>
  );
}
