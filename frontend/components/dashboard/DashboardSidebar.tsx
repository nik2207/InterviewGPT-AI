"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "◉", exact: true },
  { href: "/dashboard/resumes", label: "Resume & Jobs", icon: "▣", exact: false },
  { href: "/dashboard/interviews", label: "Mock Interviews", icon: "◎", exact: true },
  {
    href: "/dashboard/practice",
    label: "Technical Practice",
    icon: "⌁",
    exact: true,
    planned: true,
  },
  { href: "/dashboard/applications", label: "Applications", icon: "◧", exact: false },
  { href: "/dashboard/billing", label: "Plan & Billing", icon: "₹", exact: false },
  { href: "/institution", label: "College / Placement", icon: "▦", exact: false },
  { href: "/dashboard/career", label: "Preparation Plan", icon: "◈", exact: false },
  { href: "/dashboard/company-prep", label: "Company Prep", icon: "◇", exact: true },
  { href: "/dashboard/github", label: "GitHub Analyzer", icon: "⌗", exact: true },
  {
    href: "/dashboard/interviews/history",
    label: "Insights & Reports",
    icon: "▤",
    exact: false,
  },
];

interface DashboardSidebarProps {
  open: boolean;
  onClose: () => void;
}

export function DashboardSidebar({ open, onClose }: DashboardSidebarProps) {
  const pathname = usePathname();

  function isActive(href: string, exact: boolean) {
    if (exact) {
      return pathname === href;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/50 lg:hidden ${open ? "block" : "hidden"}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-app-sidebar text-slate-200 transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center gap-2 border-b border-white/10 px-5">
          <span
            className="flex h-9 w-9 items-center justify-center rounded-control bg-app-primary text-sm font-bold text-white"
            aria-hidden="true"
          >
            IG
          </span>
          <div>
            <p className="text-sm font-semibold text-white">InterviewGPT AI</p>
            <p className="text-[11px] text-slate-400">Career prep workspace</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3" aria-label="Dashboard">
          {navItems.map((item) => {
            const active = isActive(item.href, item.exact);
            if (item.planned) {
              return (
                <span
                  key={item.href}
                  className="flex items-center gap-3 rounded-control px-3 py-2.5 text-sm text-slate-500"
                  title="Coming soon — use Mock Interviews for now"
                >
                  <span aria-hidden="true">{item.icon}</span>
                  {item.label}
                  <span className="ml-auto text-[10px] uppercase tracking-wide">
                    Soon
                  </span>
                </span>
              );
            }
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-3 rounded-control px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-app-primary ${
                  active
                    ? "bg-app-primary text-white"
                    : "text-slate-300 hover:bg-app-sidebar-hover hover:text-white"
                }`}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <p className="border-t border-white/10 p-4 text-xs text-slate-500">
          Resume analysis · mock interviews · coaching
        </p>
      </aside>
    </>
  );
}
