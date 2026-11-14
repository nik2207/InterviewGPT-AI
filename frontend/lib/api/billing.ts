import { apiClient } from "@/lib/api/client";

export interface PlanCatalogItem {
  plan_id: "free" | "pro" | "premium";
  display_name: string;
  price_inr: number;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  tier_rank: number;
}

export interface UsageMeterSnapshot {
  meter: string;
  label: string;
  used: number;
  limit: number;
  reset: string;
}

export interface BillingOverview {
  effective_plan_id: "free" | "pro" | "premium";
  subscription: {
    plan_id: "free" | "pro" | "premium";
    status: string;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    razorpay_subscription_id: string | null;
  } | null;
  usage: UsageMeterSnapshot[];
  disclaimer: string;
}

export async function fetchPlanCatalog(): Promise<{
  currency: string;
  plans: PlanCatalogItem[];
  disclaimer: string;
}> {
  const { data } = await apiClient.get("/billing/plans");
  return data;
}

export async function fetchBillingOverview(): Promise<BillingOverview> {
  const { data } = await apiClient.get<BillingOverview>("/billing/me");
  return data;
}

export async function startCheckout(planId: "pro" | "premium", idempotencyKey: string) {
  const { data } = await apiClient.post("/billing/checkout", {
    plan_id: planId,
    idempotency_key: idempotencyKey,
  });
  return data as {
    razorpay_subscription_id: string;
    key_id: string | null;
    dev_mode: boolean;
    plan_id: string;
  };
}

export async function verifyPayment(payload: {
  razorpay_payment_id: string;
  razorpay_subscription_id: string;
  razorpay_signature: string;
}) {
  const { data } = await apiClient.post("/billing/verify", payload);
  return data;
}

export async function cancelSubscription(atPeriodEnd = true) {
  const { data } = await apiClient.post("/billing/cancel", {
    at_period_end: atPeriodEnd,
    reason: "",
  });
  return data;
}

export async function fetchBillingHistory() {
  const { data } = await apiClient.get<{ items: Array<{
    id: string;
    event_type: string;
    amount_inr: number | null;
    status: string;
    created_at: string;
    description: string;
  }> }>("/billing/history");
  return data.items;
}
