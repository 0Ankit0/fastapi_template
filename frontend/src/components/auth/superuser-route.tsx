'use client';

import { useEffect } from 'react';
import { useRouter } from '@/lib/router';
import { ProtectedRoute } from './protected-route';
import { useAuthStore } from '@/store/auth-store';
import { useCheckPermission } from '@/hooks/use-rbac';

export function SuperuserRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();
  const router = useRouter();
  const { data: permissionCheck, isLoading } = useCheckPermission(
    user?.id ?? '',
    'rbac',
    'manage'
  );

  const hasAdminAccess = Boolean(user?.is_superuser || permissionCheck?.allowed);

  useEffect(() => {
    if (user && !isLoading && !hasAdminAccess) {
      router.replace('/dashboard');
    }
  }, [hasAdminAccess, isLoading, router, user]);

  if (user && (isLoading || !hasAdminAccess)) return null;

  return <ProtectedRoute>{children}</ProtectedRoute>;
}
