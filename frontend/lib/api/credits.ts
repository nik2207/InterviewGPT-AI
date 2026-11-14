import { apiClient } from "@/lib/api/client";

export interface CreditBalance {
  available_total: number;
  plan_allowance_remaining: number;
  plan_allowance_limit: number;
  plan_allowance_used: number;
  purchased_balance: number;
  purchased_expiring_soon: number;
  period_key: string;
  disclaimer: string;
}

export interface CreditOperationCost {
  operation: string;
  label: string;
  credit_cost: number;
}

export interface CreditCatalog {
  currency: string;
  charging_policy: string;
  operations: CreditOperationCost[];
  topup_packs: Array<{
    pack_id: string;
    display_name: string;
    credits: number;
    price_inr: number;
    expiry_days: number | null;
  }>;
}

export interface CreditTransaction {
  id: string;
  idempotency_key: string;
  operation: string;
  amount: number;
  source: string;
  status: string;
  created_at: string;
  label: string;
}

export async function fetchCreditCatalog(): Promise<CreditCatalog> {
  const { data } = await apiClient.get<CreditCatalog>("/credits/catalog");
  return data;
}

export async function fetchCreditBalance(): Promise<CreditBalance> {
  const { data } = await apiClient.get<CreditBalance>("/credits/me");
  return data;
}

export async function fetchCreditTransactions(): Promise<{
  items: CreditTransaction[];
  total: number;
}> {
  const { data } = await apiClient.get<{
    items: CreditTransaction[];
    total: number;
  }>("/credits/transactions");
  return data;
}

export async function startCreditTopup(packId: string, idempotencyKey: string) {
  const { data } = await apiClient.post("/credits/topup/checkout", {
    pack_id: packId,
    idempotency_key: idempotencyKey,
  });
  return data as {
    order_id: string;
    amount_inr: number;
    credits: number;
    key_id: string | null;
    dev_mode: boolean;
  };
}

export async function verifyCreditTopup(payload: {
  packId: string;
  idempotencyKey: string;
  orderId: string;
}) {
  const { data } = await apiClient.post("/credits/topup/verify", {
    pack_id: payload.packId,
    razorpay_payment_id: "pay_dev",
    razorpay_order_id: payload.orderId,
    razorpay_signature: "dev_mode_signature",
    idempotency_key: payload.idempotencyKey,
  });
  return data as { verified: boolean; credits_added: number };
}
