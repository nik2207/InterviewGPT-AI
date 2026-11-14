"use client";

import Link from "next/link";

export default function BillingSuccessPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">Payment verified</h1>
      <p className="mt-2 text-sm text-slate-600">
        Your subscription was activated after server-side verification. Pro features unlock
        immediately according to your plan.
      </p>
      <Link
        href="/dashboard/billing"
        className="mt-6 inline-block rounded-lg bg-app-primary px-4 py-2 text-sm text-white"
      >
        View subscription
      </Link>
    </div>
  );
}
