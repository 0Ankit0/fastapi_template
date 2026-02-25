'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    
    if (accessToken) {
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', accessToken);
        // Force a page reload to ensure all states (api client headers etc) are updated
        // or just use router.push if using a store that reacts to storage
        // But window.location.href ensures a clean slate for the app bootstrapping
        window.location.href = '/dashboard'; 
      }
    } else {
        router.push('/login?error=social_auth_failed');
    }
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="animate-pulse flex flex-col items-center">
        <div className="h-4 w-4 bg-primary rounded-full mb-2"></div>
        <p className="text-sm text-muted-foreground">Authenticating...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CallbackContent />
    </Suspense>
  );
}
