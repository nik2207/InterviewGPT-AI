"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  cancelSubscription,
  fetchBillingHistory,
  fetchBillingOverview,
  startCheckout,
  verifyPayment,
  type BillingOverview,
} from "@/lib/api/billing";
import {
  fetchCreditBalance,
  fetchCreditCatalog,
  fetchCreditTransactions,
  startCreditTopup,
  verifyCreditTopup,
  type CreditBalance,
  type CreditCatalog,
  type CreditTransaction,
} from "@/lib/api/credits";

export default function BillingPage() {
  const router = useRouter();
  const search = useSearchParams();
  const upgrade = search.get("upgrade") as "pro" | "premium" | null;

  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [history, setHistory] = useState<
    Awaited<ReturnType<typeof fetchBillingHistory>>
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [creditBalance, setCreditBalance] = useState<CreditBalance | null>(null);
  const [creditCatalog, setCreditCatalog] = useState<CreditCatalog | null>(null);
  const [creditTxns, setCreditTxns] = useState<CreditTransaction[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [me, hist, credits, catalog, txns] = await Promise.all([
        fetchBillingOverview(),
        fetchBillingHistory(),
        fetchCreditBalance(),
        fetchCreditCatalog(),
        fetchCreditTransactions(),
      ]);
      setOverview(me);
      setHistory(hist);
      setCreditBalance(credits);
      setCreditCatalog(catalog);
      setCreditTxns(txns.items);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleUpgrade(planId: "pro" | "premium") {
    setBusy(true);
    setError(null);
    try {
      const key = `checkout-${Date.now()}`;
      const checkout = await startCheckout(planId, key);
      if (checkout.dev_mode) {
        await verifyPayment({
          razorpay_payment_id: "pay_dev",
          razorpay_subscription_id: checkout.razorpay_subscription_id,
          razorpay_signature: "dev_mode_signature",
        });
        router.push("/dashboard/billing/success");
        return;
      }
      setError(
        "Complete payment in the Razorpay checkout, then return here — access unlocks only after server verification."
      );
      window.open(
        `https://dashboard.razorpay.com/app/subscriptions/${checkout.razorpay_subscription_id}`,
        "_blank",
        "noopener,noreferrer"
      );
    } catch (upgradeError) {
      setError(getApiErrorMessage(upgradeError));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (upgrade && (upgrade === "pro" || upgrade === "premium")) {
      void handleUpgrade(upgrade);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [upgrade]);

  async function handleTopup(packId: string) {
    setBusy(true);
    setError(null);
    try {
      const idempotencyKey = `topup-${Date.now()}`;
      const checkout = await startCreditTopup(packId, idempotencyKey);
      if (checkout.dev_mode) {
        await verifyCreditTopup({
          packId,
          idempotencyKey,
          orderId: checkout.order_id,
        });
        await load();
        return;
      }
      setError("Complete payment in Razorpay, then return here to refresh your balance.");
    } catch (topupError) {
      setError(getApiErrorMessage(topupError));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    if (!window.confirm("Cancel subscription at period end?")) return;
    setBusy(true);
    try {
      await cancelSubscription(true);
      await load();
    } catch (cancelError) {
      setError(getApiErrorMessage(cancelError));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="p-6 text-sm text-slate-500">Loading billing…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
      <PageHeader
        title="Subscription & usage"
        description="Your plan, monthly usage meters, and billing history."
      />

      {overview?.disclaimer ? (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
          {overview.disclaimer}
        </p>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      {overview ? (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Current plan</h2>
          <p className="mt-1 text-lg capitalize text-app-primary">
            {overview.effective_plan_id}
            {overview.subscription?.status
              ? ` · ${overview.subscription.status.replace("_", " ")}`
              : ""}
          </p>
          {overview.subscription?.current_period_end ? (
            <p className="mt-1 text-xs text-slate-500">
              Period ends{" "}
              {new Date(overview.subscription.current_period_end).toLocaleDateString()}
            </p>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {overview.effective_plan_id !== "premium" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => handleUpgrade("pro")}
                className="rounded-lg bg-app-primary px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Upgrade to Pro
              </button>
            ) : null}
            {overview.effective_plan_id === "pro" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => handleUpgrade("premium")}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm"
              >
                Upgrade to Premium
              </button>
            ) : null}
            {overview.subscription?.status === "active" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleCancel()}
                className="rounded-lg border border-red-200 px-4 py-2 text-sm text-red-700"
              >
                Cancel subscription
              </button>
            ) : null}
            <Link href="/pricing" className="rounded-lg border border-slate-300 px-4 py-2 text-sm">
              Compare plans
            </Link>
          </div>
        </section>
      ) : null}

      {creditBalance && creditCatalog ? (
        <section
          id="credits"
          className="rounded-xl border border-slate-200 bg-white p-5 scroll-mt-20"
        >
          <h2 className="text-sm font-semibold text-slate-900">AI credits</h2>
          <p className="mt-1 text-xs text-slate-500">{creditCatalog.charging_policy}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <CreditStat label="Available" value={creditBalance.available_total} />
            <CreditStat
              label="Plan allowance left"
              value={creditBalance.plan_allowance_remaining}
            />
            <CreditStat
              label="Purchased balance"
              value={creditBalance.purchased_balance}
            />
          </div>
          {creditCatalog.topup_packs.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {creditCatalog.topup_packs.map((pack) => (
                <button
                  key={pack.pack_id}
                  type="button"
                  disabled={busy}
                  onClick={() => void handleTopup(pack.pack_id)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-left text-sm hover:bg-slate-50 disabled:opacity-50"
                >
                  <span className="font-medium">{pack.display_name}</span>
                  <span className="mt-0.5 block text-xs text-slate-600">
                    ₹{pack.price_inr}
                    {pack.expiry_days ? ` · expires in ${pack.expiry_days}d` : ""}
                  </span>
                </button>
              ))}
            </div>
          ) : null}
          <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Credit costs (server catalog)
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            {creditCatalog.operations.map((op) => (
              <li key={op.operation} className="flex justify-between gap-4">
                <span>{op.label}</span>
                <span>{op.credit_cost} credits</span>
              </li>
            ))}
          </ul>
          <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Recent credit activity
          </h3>
          {creditTxns.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No credit transactions yet.</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {creditTxns.slice(0, 15).map((txn) => (
                <li key={txn.id} className="border-b border-slate-100 pb-2">
                  {txn.label || txn.operation} · {txn.amount} · {txn.source}
                  <span className="block text-xs text-slate-500">
                    {new Date(txn.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {overview ? (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Usage this period</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {overview.usage.map((meter) => (
              <li key={meter.meter} className="flex justify-between gap-4">
                <span>{meter.label}</span>
                <span className="text-slate-600">
                  {meter.used} / {meter.limit}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Billing history</h2>
        {history.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No billing events yet.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {history.map((item) => (
              <li key={item.id} className="border-b border-slate-100 pb-2">
                {item.description} · {item.status}
                {item.amount_inr != null ? ` · ₹${item.amount_inr}` : ""}
                <span className="block text-xs text-slate-500">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function CreditStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}
