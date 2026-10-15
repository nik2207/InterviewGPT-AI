"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { DashboardSidebar } from "@/components/dashboard/DashboardSidebar";
import { useAuth } from "@/providers/auth-provider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, status, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/auth");
    }
  }, [status, router]);

  if (status === "loading" || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-500" aria-live="polite">
          Loading your dashboard…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <DashboardSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex min-h-screen flex-1 flex-col">
        <DashboardHeader
          user={user}
          onLogout={async () => {
            await logout();
            router.replace("/auth");
          }}
          onMenuToggle={() => setSidebarOpen(true)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
