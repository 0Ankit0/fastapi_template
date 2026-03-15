import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// ── Types ──────────────────────────────────────────────────────────────────

export type SubscriptionStatus = 'active' | 'trialing' | 'grace' | 'expired' | 'cancelled';

export interface SubscriptionPlan {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  price_monthly: number;
  price_quarterly: number | null;
  price_yearly: number | null;
  max_grounds: number;
  max_staff: number;
  trial_days: number;
  features: string | string[];  // API returns raw string; parse as needed
  is_active: boolean;
  is_public: boolean;
}

export type BillingInterval = 'monthly' | 'quarterly' | 'yearly';

export interface OwnerSubscription {
  status: SubscriptionStatus;
  plan: SubscriptionPlan | null;
  current_period_end: string | null;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  billing_interval: BillingInterval;
  is_active: boolean;
}

export interface OwnerSubscriptionAdmin {
  owner_id: number;
  plan: SubscriptionPlan | null;
  status: SubscriptionStatus;
  current_period_end: string | null;
  created_at: string;
}

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useSubscription() {
  return useQuery({
    queryKey: ['subscription', 'me'],
    queryFn: async () => {
      const { data } = await apiClient.get<OwnerSubscription>('/subscriptions/me');
      return data;
    },
  });
}

export function useSubscriptionPlans() {
  return useQuery({
    queryKey: ['subscription-plans'],
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionPlan[]>('/subscriptions/plans');
      return data;
    },
  });
}

export function useStartTrial(planId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post(`/subscriptions/trial/${planId}`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscription'] }),
  });
}

export function useVerifyPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      plan_id: number;
      transaction_id: number;
      provider_token: string;
      billing_interval?: string;
    }) => {
      const { data } = await apiClient.post('/subscriptions/verify-payment', payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscription'] }),
  });
}

export function useCancelSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (immediately: boolean) => {
      const { data } = await apiClient.post('/subscriptions/cancel', null, {
        params: { immediately },
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscription'] }),
  });
}

export function useAllSubscriptions() {
  return useQuery({
    queryKey: ['subscriptions', 'admin', 'all'],
    queryFn: async () => {
      const { data } =
        await apiClient.get<OwnerSubscriptionAdmin[]>('/subscriptions/admin/all');
      return data;
    },
  });
}

export function useActivateSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ownerId, planId }: { ownerId: number; planId: number }) => {
      const { data } = await apiClient.patch(
        `/subscriptions/admin/${ownerId}/activate`,
        null,
        { params: { plan_id: planId } },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions', 'admin'] }),
  });
}

// ── Subscription Usage ─────────────────────────────────────────────────────

export interface TenantUsageItem {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  disabled_by_limit: boolean;
}

export interface MemberUsageItem {
  id: number;
  tenant_id: number;
  invite_email: string;
  role: string;
  is_active: boolean;
  disabled_by_limit: boolean;
}

export interface SubscriptionUsage {
  max_tenants: number;
  max_staff: number;
  active_tenants: number;
  active_staff: number;
  tenants: TenantUsageItem[];
  members: MemberUsageItem[];
  exceeds_tenants: boolean;
  exceeds_staff: boolean;
}

export function useSubscriptionUsage() {
  return useQuery({
    queryKey: ['subscription', 'usage'],
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionUsage>('/subscriptions/usage');
      return data;
    },
  });
}

export function useApplyLimitAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { tenants_to_disable: number[]; members_to_disable: number[] }) => {
      const { data } = await apiClient.post('/subscriptions/apply-limit-adjustment', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription'] });
      qc.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}
