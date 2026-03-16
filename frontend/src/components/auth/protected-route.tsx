'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth-store';
import * as authApi from '@/lib/graphql/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, _hasHydrated, setUser, setTokens, logout } = useAuthStore();
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    if (!_hasHydrated) return;

    async function initAuth() {
      if (isAuthenticated) {
        try {
          const user = await authApi.currentUser();
          setUser(user);
        } catch {
          // Invalid token: continue to refresh flow
        }
        setIsInitializing(false);
        return;
      }

      const refreshToken =
        typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;

      if (!refreshToken) {
        router.push('/login');
        setIsInitializing(false);
        return;
      }

      try {
        const tokens = await authApi.refreshToken(refreshToken);
        setTokens(tokens.access, tokens.refresh);
        const user = await authApi.currentUser();
        setUser(user);
      } catch {
        logout();
        router.push('/login');
      } finally {
        setIsInitializing(false);
      }
    }

    initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated]);

  if (!_hasHydrated || isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return <>{children}</>;
}
