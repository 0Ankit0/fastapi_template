'use client';

import { useState } from 'react';
import {
  useAllSubscriptions,
  useActivateSubscription,
  useSubscriptionPlans,
  type SubscriptionStatus,
  type OwnerSubscriptionAdmin,
} from '@/hooks/use-subscription';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { extractErrorMsg } from '@/lib/error';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, CheckCircle, Clock, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────

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
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${STATUS_STYLES[status]}`}
    >
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}

// ── Toast ──────────────────────────────────────────────────────────────────

function Toast({
  message,
  type,
  onClose,
}: {
  message: string;
  type: 'success' | 'error';
  onClose: () => void;
}) {
  return (
    <div
      className={`fixed top-4 right-4 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg text-sm font-medium ${
        type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
      }`}
    >
      {message}
      <button onClick={onClose} className="ml-2 text-white/80 hover:text-white">
        ✕
      </button>
    </div>
  );
}

// ── Activate dialog ────────────────────────────────────────────────────────

function ActivateDialog({
  subscription,
  planOptions,
  onClose,
  onSuccess,
  onError,
}: {
  subscription: OwnerSubscriptionAdmin;
  planOptions: { id: number; name: string }[];
  onClose: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const [planId, setPlanId] = useState<number>(
    subscription.plan?.id ?? planOptions[0]?.id ?? 0,
  );
  const activate = useActivateSubscription();

  const handleActivate = () => {
    if (!planId) return;
    activate.mutate(
      { ownerId: subscription.owner_id, planId },
      {
        onSuccess: () => {
          onSuccess();
          onClose();
        },
        onError: (err: unknown) => {
          onError(extractErrorMsg(err, 'Failed to activate subscription.'));
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white border border-gray-200 p-6 shadow-xl">
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          Manually Activate — Owner #{subscription.owner_id}
        </h2>
        <div className="space-y-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Plan</label>
            <select
              value={planId}
              onChange={(e) => setPlanId(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {planOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-5 flex gap-2">
          <Button
            onClick={handleActivate}
            isLoading={activate.isPending}
            className="flex-1 bg-blue-600 hover:bg-blue-700"
          >
            Activate
          </Button>
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

const ALL_STATUSES: SubscriptionStatus[] = ['active', 'trialing', 'grace', 'expired', 'cancelled'];

const STAT_COLORS: Record<string, string> = {
  Active:    'text-green-600 bg-green-50',
  Trialing:  'text-blue-600 bg-blue-50',
  Expired:   'text-red-600 bg-red-50',
  Cancelled: 'text-gray-500 bg-gray-100',
};

export default function AdminSubscriptionsPage() {
  const { data: subscriptions = [], isLoading } = useAllSubscriptions();
  const { data: plans = [] } = useSubscriptionPlans();

  const [statusFilter, setStatusFilter] = useState<SubscriptionStatus | 'ALL'>('ALL');
  const [activating, setActivating] = useState<OwnerSubscriptionAdmin | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const filtered =
    statusFilter === 'ALL'
      ? subscriptions
      : subscriptions.filter((s) => s.status === statusFilter);

  const counts = ALL_STATUSES.reduce(
    (acc, s) => {
      acc[s] = subscriptions.filter((sub) => sub.status === s).length;
      return acc;
    },
    {} as Record<SubscriptionStatus, number>,
  );

  const statCards = [
    { label: 'Active',    count: counts.active },
    { label: 'Trialing',  count: counts.trialing },
    { label: 'Expired',   count: counts.expired },
    { label: 'Cancelled', count: counts.cancelled },
  ];

  return (
    <div className="space-y-6">
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Subscriptions</h1>
        <p className="text-gray-500 mt-1">Manage owner subscriptions</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {statCards.map((s) => (
          <Card key={s.label} className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => setStatusFilter(s.label.toLowerCase() as SubscriptionStatus)}>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className={`rounded-full p-3 ${STAT_COLORS[s.label] ?? 'text-gray-600 bg-gray-100'}`}>
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">{s.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{s.count}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-500">Filter:</span>
        {(['ALL', ...ALL_STATUSES] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-gray-900">
            Owner Subscriptions
            <span className="ml-2 text-sm font-normal text-gray-400">({filtered.length})</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-gray-400">
              No subscriptions found.
            </p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 text-left">
                  {['Owner ID', 'Plan', 'Status', 'Period End', 'Created', 'Actions'].map((col) => (
                    <th
                      key={col}
                      className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-gray-400"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((sub) => (
                  <tr
                    key={sub.owner_id}
                    className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-mono text-gray-600">{sub.owner_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-800">
                      {sub.plan?.name ?? <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={sub.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {sub.current_period_end
                        ? new Date(sub.current_period_end).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setActivating(sub)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                        title="Manually Activate"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Activate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {activating && (
        <ActivateDialog
          subscription={activating}
          planOptions={plans.map((p) => ({ id: p.id, name: p.name }))}
          onClose={() => setActivating(null)}
          onSuccess={() => showToast(`Subscription activated for owner #${activating.owner_id}.`, 'success')}
          onError={(msg) => showToast(msg, 'error')}
        />
      )}
    </div>
  );
}


// ── Types ──────────────────────────────────────────────────────────────────
