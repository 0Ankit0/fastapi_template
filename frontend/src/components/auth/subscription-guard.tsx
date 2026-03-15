'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSubscription } from '@/hooks/use-subscription';
import { AlertTriangle, CreditCard, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface SubscriptionGuardProps {
  children: React.ReactNode;
}

/**
 * Wraps owner-dashboard pages that require an active subscription.
 * If the subscription is expired, cancelled, or missing, renders a
 * paywall prompt instead of the page content.
 */
export function SubscriptionGuard({ children }: SubscriptionGuardProps) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <SubscriptionGuardInner>{children}</SubscriptionGuardInner>
    </Suspense>
  );
}

function SubscriptionGuardInner({ children }: SubscriptionGuardProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: subscription, isLoading } = useSubscription();

  const reason = searchParams?.get('reason');

  useEffect(() => {
    if (!isLoading && subscription && !subscription.is_active) {
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/subscription')) {
        router.replace('/subscription?reason=subscription_required');
      }
    }
  }, [isLoading, subscription, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!subscription) {
    return <SubscriptionPaywall status="none" reason={reason} />;
  }

  if (subscription.is_active) {
    return <>{children}</>;
  }

  return <SubscriptionPaywall status={subscription.status} reason={reason} />;
}

function SubscriptionPaywall({
  status,
  reason,
}: {
  status: string;
  reason: string | null;
}) {
  const message =
    status === 'expired'
      ? 'Your subscription has expired.'
      : status === 'cancelled'
      ? 'Your subscription has been cancelled.'
      : status === 'grace'
      ? 'Your subscription is in its grace period and will expire soon.'
      : 'You need an active subscription to access this page.';

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="rounded-full bg-amber-100 p-4">
        <AlertTriangle className="h-10 w-10 text-amber-600" />
      </div>
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Subscription Required</h2>
        <p className="text-gray-500 max-w-md">{message}</p>
        {reason === 'subscription_required' && (
          <p className="text-sm text-amber-600">
            You were redirected here because your subscription is no longer active.
          </p>
        )}
      </div>
      <Link
        href="/subscription"
        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
      >
        <CreditCard className="h-4 w-4" />
        Manage Subscription
      </Link>
    </div>
  );
}
