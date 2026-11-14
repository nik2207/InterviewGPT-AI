"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/providers/auth-provider";

const links = [
  { href: "/institution", label: "Overview", exact: true },
  { href: "/institution/analytics", label: "Analytics" },
  { href: "/institution/students", label: "Students" },
  { href: "/institution/cohorts", label: "Cohorts" },
  { href: "/institution/assignments", label: "Assignments" },
  { href: "/institution/reports", label: "Reports" },
  { href: "/institution/roles", label: "Roles & invites" },
  { href: "/institution/admin", label: "Administration" },
];

export default function InstitutionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { status } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/auth");
      return;
    }
    if (status === "authenticated") setReady(true);
  }, [status, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading institution workspace…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-app-bg">
      <header className="border-b border-slate-200 bg-white px-4 py-4 lg:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              Placement workspace
            </p>
            <h1 className="text-lg font-semibold text-slate-900">College & institution dashboard</h1>
          </div>
          <Link href="/dashboard" className="text-sm text-slate-600 hover:text-brand-700">
            ← Back to personal dashboard
          </Link>
        </div>
        <nav className="mx-auto mt-4 flex max-w-6xl flex-wrap gap-2">
          {links.map((link) => {
            const active = link.exact
              ? pathname === link.href
              : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  active
                    ? "bg-brand-700 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl p-4 lg:p-8">{children}</main>
    </div>
  );
}
