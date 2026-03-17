'use client';

import { useState } from 'react';
import { useAuthStore } from '@/store/auth-store';
import {
  useNotificationDevices,
  useNotificationPreferences,
  useRegisterNotificationDevice,
  useRemoveNotificationDevice,
  useUpdateNotificationPreferences,
} from '@/hooks/use-notifications';
import { usePushConfig, useSystemCapabilities } from '@/hooks/use-system';
import { useResendVerification } from '@/hooks/use-auth';
import { registerCurrentPushDevice } from '@/lib/push-registration';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button, Skeleton } from '@/components/ui';
import {
  Bell,
  Mail,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Key,
  RefreshCw,
  ExternalLink,
  Radio,
  Smartphone,
  Trash2,
} from 'lucide-react';
import Link from 'next/link';

const TABS = [
  { id: 'account',       label: 'Account',       icon: Mail },
  { id: 'notifications', label: 'Notifications',  icon: Bell },
  { id: 'privacy',       label: 'Privacy',        icon: ShieldAlert },
] as const;

type TabId = (typeof TABS)[number]['id'];

function DeviceRow({
  device,
  onRemove,
  isPending,
}: {
  device: {
    id: number;
    provider: string;
    platform: string;
    last_seen_at: string;
  };
  onRemove: (id: number) => void;
  isPending: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Smartphone className="h-4 w-4 text-gray-500" />
            {device.provider.toUpperCase()} on {device.platform}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Last seen {new Date(device.last_seen_at).toLocaleString()}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRemove(device.id)}
          disabled={isPending}
          className="text-red-600 hover:bg-red-50 hover:text-red-700"
        >
          <Trash2 className="mr-1 h-3.5 w-3.5" />
          Remove
        </Button>
      </div>
    </div>
  );
}

// ── Toggle component ────────────────────────────────────────────────────────
function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
        checked ? 'bg-blue-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<TabId>('account');

  // ── Notifications ──────────────────────────────────────────────────────
  const { data: prefs, isLoading: prefsLoading } = useNotificationPreferences();
  const { data: devices } = useNotificationDevices();
  const { data: pushConfig } = usePushConfig();
  const { data: capabilities } = useSystemCapabilities();
  const updatePref = useUpdateNotificationPreferences();
  const registerDevice = useRegisterNotificationDevice();
  const removeDevice = useRemoveNotificationDevice();
  const [pushActionError, setPushActionError] = useState<string | null>(null);

  // ── Email verification ─────────────────────────────────────────────────
  const resend = useResendVerification();
  const [resentOk, setResentOk] = useState(false);
  const handleResend = () => {
    resend.mutate(undefined, {
      onSuccess: () => setResentOk(true),
    });
  };

  const handleRegisterCurrentDevice = async () => {
    if (!pushConfig?.provider) return;
    setPushActionError(null);
    try {
      const payload = await registerCurrentPushDevice(pushConfig.provider, pushConfig);
      if (!payload) {
        setPushActionError(
          'This browser could not generate a push subscription for the active provider.'
        );
        return;
      }
      registerDevice.mutate(payload, {
        onError: (error) =>
          setPushActionError(error instanceof Error ? error.message : 'Registration failed.'),
      });
    } catch (error) {
      setPushActionError(error instanceof Error ? error.message : 'Registration failed.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">App preferences and account management</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <nav className="w-48 flex-shrink-0 space-y-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex-1 space-y-5">

          {/* ── Account tab ─────────────────────────────────────────────── */}
          {activeTab === 'account' && (
            <>
              {/* Email address + verification */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="h-5 w-5" />
                    Email Address
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                      <p className="text-xs text-gray-500 mt-0.5">Your login email</p>
                    </div>
                    {user?.is_confirmed ? (
                      <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Verified
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-xs font-medium text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full">
                        <XCircle className="h-3.5 w-3.5" />
                        Unverified
                      </span>
                    )}
                  </div>

                  {!user?.is_confirmed && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3">
                      <p className="text-sm text-amber-800">
                        Your email address hasn't been verified yet. Check your inbox for the
                        verification link, or request a new one below.
                      </p>
                      {resentOk ? (
                        <p className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                          <CheckCircle2 className="h-4 w-4" />
                          Verification email sent — check your inbox.
                        </p>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleResend}
                          isLoading={resend.isPending}
                        >
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                          Resend verification email
                        </Button>
                      )}
                    </div>
                  )}

                  {user?.is_confirmed && (
                    <p className="text-xs text-gray-400">
                      To change your email address, contact support.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Username / display info (read-only, edit via Profile) */}
              <Card>
                <CardHeader>
                  <CardTitle>Account Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { label: 'Username', value: user?.username },
                    { label: 'Member since', value: user?.created_at ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '—' },
                    { label: 'Account type', value: user?.is_superuser ? 'Superuser' : 'Standard' },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <span className="text-sm text-gray-500">{label}</span>
                      <span className="text-sm font-medium text-gray-900">{value || '—'}</span>
                    </div>
                  ))}
                  <p className="pt-1 text-xs text-gray-400">
                    Update your name and avatar on the{' '}
                    <Link href="/profile" className="text-blue-600 hover:underline">
                      Profile page
                    </Link>
                    .
                  </p>
                </CardContent>
              </Card>
            </>
          )}

          {/* ── Notifications tab ────────────────────────────────────────── */}
          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Notification Channels
                </CardTitle>
              </CardHeader>
              <CardContent>
                {prefsLoading ? (
                  <div className="space-y-4">
                    {[1, 2, 3, 4].map((i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : prefs ? (
                  <div className="divide-y divide-gray-100">
                    {(
                      [
                        {
                          key: 'websocket_enabled',
                          label: 'In-App notifications',
                          desc: 'Real-time alerts inside the dashboard',
                        },
                        {
                          key: 'email_enabled',
                          label: 'Email notifications',
                          desc: 'Receive updates to your email address',
                        },
                        {
                          key: 'push_enabled',
                          label: 'Browser push notifications',
                          desc: 'Desktop or mobile push alerts using the active provider',
                        },
                        {
                          key: 'sms_enabled',
                          label: 'SMS notifications',
                          desc: 'Text messages to your phone number',
                        },
                      ] as const
                    ).map(({ key, label, desc }) => (
                      <div key={key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{label}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                        </div>
                        <Toggle
                          checked={!!prefs[key]}
                          onChange={(v) => updatePref.mutate({ [key]: v })}
                          disabled={updatePref.isPending}
                        />
                      </div>
                    ))}
                    <div className="py-3 last:pb-0">
                      <p className="text-sm font-medium text-gray-900">Runtime status</p>
                      <div className="mt-2 space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-600">
                          Notifications module:
                          <span className="ml-1 font-medium text-gray-900">
                            {capabilities?.modules.notifications === false ? 'Disabled' : 'Enabled'}
                          </span>
                        </p>
                        <p className="text-xs text-gray-600">
                          Active push provider:
                          <span className="ml-1 font-medium text-gray-900 uppercase">
                            {pushConfig?.provider ?? 'none'}
                          </span>
                        </p>
                        <p className="text-xs text-gray-600">
                          Provider readiness:
                          <span className="ml-1 font-medium text-gray-900">
                            {pushConfig?.provider
                              ? pushConfig.providers[
                                  pushConfig.provider as keyof typeof pushConfig.providers
                                ]?.enabled
                                ? 'Ready'
                                : 'Unavailable'
                              : 'No active provider'}
                          </span>
                        </p>
                        <p className="text-xs text-gray-600">
                          Registered devices:
                          <span className="ml-1 font-medium text-gray-900">
                            {devices?.length ?? 0}
                          </span>
                        </p>
                        <div className="flex flex-wrap gap-2 pt-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleRegisterCurrentDevice}
                            disabled={
                              !prefs.push_enabled ||
                              !pushConfig?.provider ||
                              registerDevice.isPending
                            }
                            isLoading={registerDevice.isPending}
                          >
                            <Radio className="mr-1.5 h-3.5 w-3.5" />
                            Register This Browser
                          </Button>
                        </div>
                        {pushActionError ? (
                          <p className="text-xs font-medium text-red-600">{pushActionError}</p>
                        ) : null}
                        {devices && devices.length > 0 ? (
                          <div className="space-y-2">
                            {devices.map((device) => (
                              <DeviceRow
                                key={device.id}
                                device={device}
                                onRemove={(id) => removeDevice.mutate(id)}
                                isPending={removeDevice.isPending}
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4">
                            <p className="text-sm font-medium text-gray-700">
                              No registered push devices.
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              Enable push notifications, then register this browser or your mobile app.
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Unable to load preferences.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* ── Privacy tab ─────────────────────────────────────────────── */}
          {activeTab === 'privacy' && (
            <div className="space-y-5">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="h-5 w-5" />
                    Active Sessions
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-gray-600">
                    View all devices and locations where your account is currently signed in. Revoke
                    any session you don't recognise.
                  </p>
                  <Link href="/tokens">
                    <Button variant="outline" size="sm">
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                      Manage sessions
                    </Button>
                  </Link>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <ShieldAlert className="h-5 w-5" />
                    Danger Zone
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-red-800">Deactivate account</p>
                      <p className="text-xs text-red-700 mt-0.5">
                        Signing out from all devices and disabling your account. You can reactivate
                        by contacting support.
                      </p>
                    </div>
                    <Link href="/tokens">
                      <Button variant="destructive" size="sm">
                        Revoke all sessions
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
