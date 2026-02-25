'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCurrentUser, useUpdateProfile } from '@/hooks/use-users';
import { useChangePassword } from '@/hooks/use-auth';
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from '@/hooks/use-notifications';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button, Skeleton } from '@/components/ui';
import { Input } from '@/components/ui/input';
import { User, Lock, Bell } from 'lucide-react';

const profileSchema = z.object({
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  phone: z.string().optional(),
});

const passwordSchema = z
  .object({
    old_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

type ProfileFormData = z.infer<typeof profileSchema>;
type PasswordFormData = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { data: user, isLoading } = useCurrentUser();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const { data: prefs } = useNotificationPreferences();
  const updatePref = useUpdateNotificationPreferences();
  const [activeTab, setActiveTab] = useState('profile');

  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    values: {
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      phone: user?.phone ?? '',
    },
  });

  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Manage your account settings</p>
      </div>

      <div className="flex gap-6">
        <div className="w-56 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">
          {activeTab === 'profile' && (
            <Card>
              <CardHeader><CardTitle>Profile Information</CardTitle></CardHeader>
              <CardContent>
                <form
                  onSubmit={profileForm.handleSubmit((d) => updateProfile.mutate(d))}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="First Name"
                      {...profileForm.register('first_name')}
                      error={profileForm.formState.errors.first_name?.message}
                    />
                    <Input
                      label="Last Name"
                      {...profileForm.register('last_name')}
                      error={profileForm.formState.errors.last_name?.message}
                    />
                  </div>
                  <Input
                    label="Phone"
                    {...profileForm.register('phone')}
                    error={profileForm.formState.errors.phone?.message}
                  />
                  <Button type="submit" isLoading={updateProfile.isPending}>
                    Save Changes
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader><CardTitle>Change Password</CardTitle></CardHeader>
              <CardContent>
                <form
                  onSubmit={passwordForm.handleSubmit((d) =>
                    changePassword.mutate(
                      { current_password: d.old_password, new_password: d.new_password, confirm_password: d.new_password },
                      { onSuccess: () => passwordForm.reset() }
                    )
                  )}
                  className="space-y-4"
                >
                  <Input
                    type="password"
                    label="Current Password"
                    {...passwordForm.register('old_password')}
                    error={passwordForm.formState.errors.old_password?.message}
                  />
                  <Input
                    type="password"
                    label="New Password"
                    {...passwordForm.register('new_password')}
                    error={passwordForm.formState.errors.new_password?.message}
                  />
                  <Input
                    type="password"
                    label="Confirm New Password"
                    {...passwordForm.register('confirm_password')}
                    error={passwordForm.formState.errors.confirm_password?.message}
                  />
                  <Button type="submit" isLoading={changePassword.isPending}>
                    Update Password
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <CardHeader><CardTitle>Notification Preferences</CardTitle></CardHeader>
              <CardContent>
                {prefs ? (
                  <div className="space-y-4">
                    {(
                      [
                        { key: 'email_enabled', label: 'Email Notifications' },
                        { key: 'push_enabled', label: 'Push Notifications' },
                        { key: 'websocket_enabled', label: 'In-App (WebSocket)' },
                        { key: 'sms_enabled', label: 'SMS Notifications' },
                      ] as const
                    ).map(({ key, label }) => (
                      <div key={key} className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">{label}</p>
                        <input
                          type="checkbox"
                          checked={!!prefs[key]}
                          onChange={(e) =>
                            updatePref.mutate({ [key]: e.target.checked })
                          }
                          className="h-4 w-4 rounded"
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Loading preferences…</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
