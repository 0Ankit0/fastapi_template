'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  useSubscription,
  useSubscriptionPlans,
  useCancelSubscription,
  useStartTrial,
  type SubscriptionStatus,
  type SubscriptionPlan,
  type BillingInterval,
} from '@/hooks/use-subscription';
import { extractErrorMsg } from '@/lib/error';
import { apiClient } from '@/lib/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import {
  CheckCircle, Clock, XCircle, AlertTriangle,
  CreditCard, Zap, Calendar, Info,
} from 'lucide-react';

// ── Helpers ────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<SubscriptionStatus, string> = {
  active:    'bg-green-100 text-green-700',
  trialing:  'bg-blue-100 text-blue-700',
  grace:     'bg-yellow-100 text-yellow-700',
  expired:   'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
};
const STATUS_ICONS: Record<SubscriptionStatus, React.ElementType> = {
  active:    CheckCircle,
  trialing:  Clock,
  grace:     AlertTriangle,
  expired:   XCircle,
  cancelled: XCircle,
};

function StatusBadge({ status }: { status: SubscriptionStatus }) {
  const Icon = STATUS_ICONS[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold uppercase ${STATUS_STYLES[status]}`}>
      <Icon className="h-3.5 w-3.5" />{status}
    </span>
  );
}

function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  return (
    <div className={`fixed top-4 right-4 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg text-sm font-medium ${
      type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
    }`}>
      {message}
      <button onClick={onClose} className="ml-2 text-white/80 hover:text-white">✕</button>
    </div>
  );
}

function parseFeatures(raw: string | string[] | null | undefined): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try { return JSON.parse(raw); } catch { return raw.split('\n').filter(Boolean); }
}

const INTERVAL_LABELS: Record<BillingInterval, string> = {
  monthly:   'Monthly',
  quarterly: 'Quarterly',
  yearly:    'Yearly',
};
const INTERVAL_DURATION: Record<BillingInterval, string> = {
  monthly:   '1 month',
  quarterly: '3 months',
  yearly:    '12 months',
};

function getPrice(plan: SubscriptionPlan, interval: BillingInterval): number {
  if (interval === 'quarterly' && plan.price_quarterly != null) return plan.price_quarterly;
  if (interval === 'yearly' && plan.price_yearly != null) return plan.price_yearly;
  return plan.price_monthly;
}

function getSavings(plan: SubscriptionPlan, interval: BillingInterval): number | null {
  if (interval === 'quarterly' && plan.price_quarterly != null) {
    return Math.round((1 - plan.price_quarterly / (plan.price_monthly * 3)) * 100);
  }
  if (interval === 'yearly' && plan.price_yearly != null) {
    return Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100);
  }
  return null;
}

// ── Plan Card ──────────────────────────────────────────────────────────────

function PlanCard({
  plan,
  interval,
  isCurrentPlan,
  canTrial,
  onSubscribe,
  onTrialSuccess,
  onTrialError,
  isInitiatingPayment,
}: {
  plan: SubscriptionPlan;
  interval: BillingInterval;
  isCurrentPlan: boolean;
  canTrial: boolean;
  onSubscribe: (plan: SubscriptionPlan, interval: BillingInterval) => void;
  onTrialSuccess: () => void;
  onTrialError: (msg: string) => void;
  isInitiatingPayment: boolean;
}) {
  const startTrial = useStartTrial(plan.id);
  const price = getPrice(plan, interval);
  const savings = getSavings(plan, interval);
  const features = parseFeatures(plan.features);

  return (
    <Card className={`flex flex-col transition-shadow ${isCurrentPlan ? 'ring-2 ring-blue-500' : 'hover:shadow-md'}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg">{plan.name}</CardTitle>
          {isCurrentPlan && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">Current</span>
          )}
        </div>
        {plan.description && <p className="text-sm text-gray-500 mt-1">{plan.description}</p>}
        <div className="mt-2">
          <span className="text-2xl font-bold text-gray-900">NPR {price.toLocaleString()}</span>
          <span className="text-sm text-gray-500 ml-1">/ {INTERVAL_DURATION[interval]}</span>
          {savings != null && savings > 0 && (
            <span className="ml-2 text-xs font-semibold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
              {savings}% off
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        <ul className="space-y-1.5 text-sm text-gray-600">
          <li className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
            Up to {plan.max_grounds} ground{plan.max_grounds !== 1 ? 's' : ''}
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
            Up to {plan.max_staff} staff member{plan.max_staff !== 1 ? 's' : ''}
          </li>
          {plan.trial_days > 0 && (
            <li className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-blue-500 shrink-0" />
              {plan.trial_days}-day free trial
            </li>
          )}
          {features.map((f) => (
            <li key={f} className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />{f}
            </li>
          ))}
        </ul>

        <div className="mt-auto space-y-2">
          <Button
            className="w-full bg-blue-600 hover:bg-blue-700"
            onClick={() => onSubscribe(plan, interval)}
            disabled={isInitiatingPayment}
          >
            <CreditCard className="mr-1.5 h-4 w-4" />
            {isCurrentPlan ? 'Renew Plan' : 'Subscribe'} · NPR {price.toLocaleString()}
          </Button>
          {canTrial && plan.trial_days > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="w-full border-blue-300 text-blue-600 hover:bg-blue-50"
              disabled={startTrial.isPending}
              onClick={() =>
                startTrial.mutate(undefined, {
                  onSuccess: onTrialSuccess,
                  onError: (e: unknown) => {
                    onTrialError(extractErrorMsg(e, 'Failed to start trial.'));
                  },
                })
              }
            >
              <Zap className="mr-1.5 h-3.5 w-3.5" />
              Start {plan.trial_days}-day Free Trial
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

function OwnerSubscriptionPageInner() {
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const { data: subscription, isLoading: subLoading } = useSubscription();
  const { data: plans = [], isLoading: plansLoading } = useSubscriptionPlans();
  const cancelSubscription = useCancelSubscription();

  const [selectedInterval, setSelectedInterval] = useState<BillingInterval>('monthly');
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [isInitiatingPayment, setIsInitiatingPayment] = useState(false);

  // Show a toast when redirected here after payment callback or expired subscription
  useEffect(() => {
    const reason = searchParams?.get('reason');
    const action = searchParams?.get('action');
    if (reason === 'subscription_required') {
      showToast('Your subscription is not active. Please subscribe or renew.', 'error');
    }
    if (action === 'adjust-limits') {
      showToast('Your plan was downgraded. Please review your resource limits below.', 'error');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleCancel = () => {
    cancelSubscription.mutate(false, {
      onSuccess: () => {
        setShowCancelDialog(false);
        showToast('Subscription will be cancelled at the end of the billing period.', 'success');
      },
      onError: () => {
        setShowCancelDialog(false);
        showToast('Failed to cancel subscription. Please try again.', 'error');
      },
    });
  };

  const handleSubscribe = async (plan: SubscriptionPlan, interval: BillingInterval) => {
    setIsInitiatingPayment(true);
    try {
      // Store billing interval so the callback page can pass it to verify-payment.
      sessionStorage.setItem('sub_billing_interval', interval);

      const { data } = await apiClient.post('/subscriptions/initiate-payment', {
        plan_id: plan.id,
        billing_interval: interval,
        provider: 'khalti',
        return_url: `${window.location.origin}/subscription/payment-callback`,
      });
      if (data?.payment_url) {
        window.location.href = data.payment_url;
      } else {
        showToast('Payment initiation failed. No redirect URL received.', 'error');
      }
    } catch (e: unknown) {
      showToast(extractErrorMsg(e, 'Failed to initiate payment. Please try again.'), 'error');
    } finally {
      setIsInitiatingPayment(false);
    }
  };

  const isTrialing = subscription?.status === 'trialing';
  const canTrial = !subscription || (subscription.status !== 'active' && subscription.status !== 'trialing');
  const endDate = subscription?.trial_ends_at ?? subscription?.current_period_end;

  // Available intervals based on what plans offer
  const availableIntervals: BillingInterval[] = ['monthly'];
  if (plans.some(p => p.price_quarterly != null)) availableIntervals.push('quarterly');
  if (plans.some(p => p.price_yearly != null)) availableIntervals.push('yearly');

  return (
    <div className="space-y-8">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Subscription</h1>
        <p className="text-gray-500 mt-1">Manage your plan and billing to access all owner features</p>
      </div>

      {/* No subscription banner */}
      {!subLoading && !subscription?.is_active && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 p-5 flex items-start gap-3">
          <Info className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold text-amber-800">Subscription Required</p>
            <p className="text-sm text-amber-700 mt-0.5">
              {subscription?.status === 'expired'
                ? 'Your subscription has expired. Renew below to restore full access.'
                : subscription?.status === 'cancelled'
                ? 'Your subscription was cancelled. Re-subscribe below to regain access.'
                : 'You need an active subscription to use the owner dashboard and manage grounds.'}
            </p>
          </div>
        </div>
      )}

      {/* Current plan card */}
      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-base">Current Plan</CardTitle>
        </CardHeader>
        <CardContent>
          {subLoading ? (
            <div className="space-y-3"><Skeleton className="h-6 w-48" /><Skeleton className="h-4 w-64" /></div>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <p className="font-semibold text-gray-900 text-lg">
                    {subscription?.plan?.name ?? 'No active plan'}
                  </p>
                  {subscription?.status && <StatusBadge status={subscription.status} />}
                </div>
                {endDate && (
                  <p className="text-sm text-gray-500 flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {isTrialing ? 'Trial ends' : subscription?.status === 'active' ? 'Renews on' : 'Expired'}{' '}
                    <span className="font-medium text-gray-700">
                      {new Date(endDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </span>
                  </p>
                )}
                {subscription?.billing_interval && subscription.is_active && (
                  <p className="text-xs text-gray-400">
                    Billing: {INTERVAL_LABELS[subscription.billing_interval]}
                  </p>
                )}
                {subscription?.cancel_at_period_end && (
                  <p className="text-sm text-yellow-600 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5" /> Cancels at end of current period
                  </p>
                )}
              </div>
              {subscription?.is_active && !subscription.cancel_at_period_end && (
                <Button
                  variant="outline"
                  className="border-red-200 text-red-600 hover:bg-red-50"
                  onClick={() => setShowCancelDialog(true)}
                >
                  Cancel Subscription
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Plans section */}
      <div>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">Available Plans</h2>

          {/* Interval switcher */}
          {availableIntervals.length > 1 && (
            <div className="flex items-center bg-gray-100 rounded-lg p-1 gap-1">
              {availableIntervals.map(iv => (
                <button
                  key={iv}
                  onClick={() => setSelectedInterval(iv)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    selectedInterval === iv
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {INTERVAL_LABELS[iv]}
                  {iv !== 'monthly' && plans.some(p => getSavings(p, iv) != null && (getSavings(p, iv) ?? 0) > 0) && (
                    <span className="ml-1 text-xs text-green-600 font-semibold">Save</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {plansLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-64 w-full rounded-xl" />)}
          </div>
        ) : plans.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 py-12 text-center">
            <p className="text-gray-400 text-sm">No plans available at this time. Please contact support.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map(plan => (
              <PlanCard
                key={plan.id}
                plan={plan}
                interval={selectedInterval}
                isCurrentPlan={subscription?.plan?.id === plan.id && !!subscription.is_active}
                canTrial={canTrial}
                onSubscribe={handleSubscribe}
                onTrialSuccess={() => {
                  qc.invalidateQueries({ queryKey: ['subscription'] });
                  showToast(`Free trial for ${plan.name} started! Enjoy your ${plan.trial_days} days.`, 'success');
                }}
                onTrialError={(msg) => showToast(msg, 'error')}
                isInitiatingPayment={isInitiatingPayment}
              />
            ))}
          </div>
        )}
      </div>

      {isInitiatingPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="rounded-xl bg-white px-8 py-6 shadow-xl text-center space-y-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
            <p className="font-medium text-gray-700">Redirecting to payment…</p>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={showCancelDialog}
        title="Cancel Subscription?"
        description="Your subscription will remain active until the end of the current billing period. You won't be charged again."
        confirmLabel="Yes, Cancel"
        cancelLabel="Keep Subscription"
        onConfirm={handleCancel}
        onCancel={() => setShowCancelDialog(false)}
        isLoading={cancelSubscription.isPending}
      />
    </div>
  );
}

export default function OwnerSubscriptionPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>}>
      <OwnerSubscriptionPageInner />
    </Suspense>
  );
}
