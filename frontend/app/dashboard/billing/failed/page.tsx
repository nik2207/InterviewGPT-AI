"use client";

import Link from "next/link";

export default function BillingFailedPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">Payment issue</h1>
      <p className="mt-2 text-sm text-slate-600">
        We could not verify your payment. Your plan was not upgraded. Try again or contact support
        if money was debited.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link href="/dashboard/billing" className="rounded-lg bg-app-primary px-4 py-2 text-sm text-white">
          Billing settings
        </Link>
        <Link href="/pricing" className="rounded-lg border border-slate-300 px-4 py-2 text-sm">
          Pricing
        </Link>
      </div>
    </div>
  );
}
