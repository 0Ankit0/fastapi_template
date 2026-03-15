'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useVerifyPayment } from '@/hooks/use-subscription';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';

/**
 * Handles payment provider callbacks for subscription payments.
 *
 * Khalti redirect params:
 *   ?status=Completed&transaction_id=...&tidx=...&amount=...&pidx=...
 *   &purchase_order_id=SUB-<userId>-<planId>-<token>&purchase_order_name=...
 *
 * eSewa redirect params:
 *   ?data=<BASE64_JSON>&provider=esewa
 *
 * The subscription initiate-payment endpoint stores a PaymentTransaction in
 * the DB (via the finance module) and returns the provider's payment_url.
 * After the redirect back here, we:
 *   1. Parse the purchase_order_id to extract plan_id and transaction_id.
 *   2. POST /subscriptions/verify-payment to confirm and activate the sub.
 */
function SubscriptionPaymentCallbackInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const verifyPayment = useVerifyPayment();
  const [pageStatus, setPageStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [needsLimitAdjustment, setNeedsLimitAdjustment] = useState(false);
  const calledRef = useRef(false);

  useEffect(() => {
    // Guard against double-invocation in React strict mode / HMR.
    if (calledRef.current) return;
    calledRef.current = true;

    const provider = searchParams.get('provider') ?? 'khalti';

    // ── Khalti callback ───────────────────────────────────────────────────
    if (provider === 'khalti' || !searchParams.get('data')) {
      const status = searchParams.get('status');
      const pidx = searchParams.get('pidx');
      const purchaseOrderId = searchParams.get('purchase_order_id') ?? '';

      if (status !== 'Completed') {
        setPageStatus('error');
        setMessage(
          status === 'User canceled'
            ? 'Payment was cancelled. You can try again from the subscription page.'
            : `Payment was not completed (status: ${status ?? 'unknown'}).`
        );
        return;
      }

      if (!pidx) {
        setPageStatus('error');
        setMessage('Missing payment identifier (pidx). Please contact support.');
        return;
      }

      // Purchase order format: SUB-<userId>-<planId>-<randomToken>
      const parts = purchaseOrderId.split('-');
      const planId = parts.length >= 3 ? parseInt(parts[2], 10) : NaN;

      if (isNaN(planId)) {
        setPageStatus('error');
        setMessage('Could not determine plan from payment reference. Please contact support.');
        return;
      }

      // We pass pidx as the provider_token; transaction_id will be looked up
      // server-side via the pidx matching in the PaymentTransaction table.
      // For the subscription verify endpoint we need the DB transaction_id.
      // The backend's /subscriptions/verify-payment accepts transaction_id as
      // the DB row ID — find it from the finance verify flow first.
      verifySubscription(planId, pidx, provider);
      return;
    }

    // ── eSewa v2 callback ─────────────────────────────────────────────────
    const esewaData = searchParams.get('data');
    if (esewaData) {
      try {
        const decoded = JSON.parse(atob(esewaData));
        const purchaseOrderId: string = decoded.transaction_uuid ?? '';
        const parts = purchaseOrderId.split('-');
        const planId = parts.length >= 3 ? parseInt(parts[2], 10) : NaN;

        if (decoded.status !== 'COMPLETE' || isNaN(planId)) {
          setPageStatus('error');
          setMessage(`eSewa payment not completed (status: ${decoded.status ?? 'unknown'}).`);
          return;
        }

        verifySubscription(planId, decoded.transaction_uuid, 'esewa');
      } catch {
        setPageStatus('error');
        setMessage('Failed to parse eSewa response data. Please contact support.');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Calls the finance verify endpoint first (to record the payment in DB),
   * then calls the subscription verify endpoint to activate the subscription.
   */
  async function verifySubscription(planId: number, providerToken: string, provider: string) {
    try {
      // Step 1: Verify payment via finance module to get the DB transaction_id.
      const { apiClient } = await import('@/lib/api-client');
      const financeVerify = await apiClient.post('/payments/verify', {
        provider,
        pidx: provider === 'khalti' ? providerToken : undefined,
        data: provider === 'esewa' ? searchParams.get('data') : undefined,
      });

      const transactionId: number = financeVerify.data?.transaction_id;
      if (!transactionId) {
        throw new Error('Payment verification did not return a transaction ID.');
      }

      // Step 2: Activate the subscription.
      const billingInterval = sessionStorage.getItem('sub_billing_interval') ?? 'monthly';
      verifyPayment.mutate(
        {
          plan_id: planId,
          transaction_id: transactionId,
          provider_token: providerToken,
          billing_interval: billingInterval,
        },
        {
          onSuccess: (result) => {
            sessionStorage.removeItem('sub_billing_interval');
            setPageStatus('success');
            setMessage('Your subscription has been activated successfully!');
            setNeedsLimitAdjustment(result?.needs_limit_adjustment === true);
            setTimeout(() => {
              router.push(result?.needs_limit_adjustment ? '/subscription?action=adjust-limits' : '/subscription');
            }, 3000);
          },
          onError: (err: unknown) => {
            const detail =
              (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setPageStatus('error');
            setMessage(detail ?? 'Subscription activation failed. Please contact support.');
          },
        }
      );
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPageStatus('error');
      setMessage(detail ?? 'Payment verification failed. Please contact support.');
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Subscription Activation</h1>

        {pageStatus === 'loading' && (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
            <p className="text-gray-500">Verifying your payment and activating subscription…</p>
          </div>
        )}

        {pageStatus === 'success' && (
          <div className="space-y-4">
            <CheckCircle className="h-14 w-14 text-green-500 mx-auto" />
            <p className="text-gray-700 font-medium">{message}</p>
            {needsLimitAdjustment && (
              <p className="text-sm text-amber-600">
                Your new plan has lower limits. You&apos;ll be prompted to adjust your resources.
              </p>
            )}
            <p className="text-sm text-gray-400">Redirecting to subscription page…</p>
            <Link href="/subscription" className="text-sm text-blue-600 hover:underline">
              Go to Subscription
            </Link>
          </div>
        )}

        {pageStatus === 'error' && (
          <div className="space-y-4">
            <XCircle className="h-14 w-14 text-red-500 mx-auto" />
            <p className="text-gray-700">{message}</p>
            <div className="flex flex-col gap-2">
              <Link href="/subscription" className="text-sm text-blue-600 hover:underline">
                Back to Subscription
              </Link>
              <Link href="/dashboard" className="text-sm text-gray-400 hover:underline">
                Go to Dashboard
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SubscriptionPaymentCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <SubscriptionPaymentCallbackInner />
    </Suspense>
  );
}
