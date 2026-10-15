"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Overview", matchPrefix: false },
  { href: "/dashboard/resumes", label: "Resume analysis", matchPrefix: true },
  { href: "/dashboard#quick-actions", label: "Quick actions", matchPrefix: false },
  { href: "/dashboard#activity", label: "Activity", matchPrefix: false },
];

interface DashboardSidebarProps {
  open: boolean;
  onClose: () => void;
}

export function DashboardSidebar({ open, onClose }: DashboardSidebarProps) {
  const pathname = usePathname();

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-slate-900/40 lg:hidden ${
          open ? "block" : "hidden"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center border-b border-slate-200 px-6">
          <Link
            href="/dashboard"
            className="text-lg font-semibold text-brand-700"
            onClick={onClose}
          >
            InterviewGPT AI
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-4" aria-label="Dashboard">
          {navItems.map((item) => {
            const active = item.matchPrefix
              ? pathname.startsWith(item.href)
              : pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={`block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <p className="border-t border-slate-200 p-4 text-xs text-slate-500">
          Mock interviews and AI coaching — dashboard preview.
        </p>
      </aside>
    </>
  );
}
