import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
}

export function StatCard({ label, value, helper, icon }: StatCardProps) {
  return (
    <article
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"
      aria-label={label}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            {value}
          </p>
          <p className="mt-1 text-xs text-slate-500">{helper}</p>
        </div>
        <div
          className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600"
          aria-hidden="true"
        >
          {icon}
        </div>
      </div>
    </article>
  );
}
