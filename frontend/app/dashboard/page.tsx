"use client";

import { DashboardHome } from "@/components/dashboard/DashboardHome";
import { useAuth } from "@/providers/auth-provider";

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  return <DashboardHome user={user} />;
}
