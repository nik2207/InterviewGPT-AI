"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchCreditBalance, type CreditBalance } from "@/lib/api/credits";

export function CreditBalanceBadge() {
  const [balance, setBalance] = useState<CreditBalance | null>(null);

  useEffect(() => {
    let active = true;
    void fetchCreditBalance()
      .then((data) => {
        if (active) setBalance(data);
      })
      .catch(() => {
        if (active) setBalance(null);
      });
    return () => {
      active = false;
    };
  }, []);

  if (!balance) {
    return null;
  }

  return (
    <Link
      href="/dashboard/billing#credits"
      className="hidden rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 hover:bg-white sm:inline-flex sm:flex-col sm:items-end"
      title={balance.disclaimer}
    >
      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        AI credits
      </span>
      <span className="font-semibold text-brand-700">{balance.available_total}</span>
    </Link>
  );
}
