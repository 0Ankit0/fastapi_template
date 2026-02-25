'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useVerifyIPToken } from '@/hooks/use-ip-access';
import { Shield, CheckCircle, XCircle, Loader2 } from 'lucide-react';

function IPVerifyInner() {
  const searchParams = useSearchParams();
  const t = searchParams.get('t') ?? '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  const verify = useVerifyIPToken();

  useEffect(() => {
    if (!t) {
      setStatus('error');
      setMessage('No verification token found in the URL.');
      return;
    }

    verify.mutate(t, {
      onSuccess: (data) => {
        setStatus('success');
        setMessage(data.message);
      },
      onError: () => {
        setStatus('error');
        setMessage('This verification link is invalid or has already been used.');
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow text-center">
        <div className="mb-4 flex justify-center">
          <Shield className="h-12 w-12 text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">IP Verification</h1>

        {status === 'loading' && (
          <div className="flex flex-col items-center gap-3 mt-4">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-500">Processing your request…</p>
          </div>
        )}

        {status === 'success' && (
          <div className="mt-4 space-y-4">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
            <p className="text-gray-700">{message}</p>
            <Link
              href="/login"
              className="inline-block mt-4 rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Go to Login
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="mt-4 space-y-4">
            <XCircle className="h-12 w-12 text-red-500 mx-auto" />
            <p className="text-gray-700">{message}</p>
            <Link
              href="/login"
              className="inline-block mt-4 text-sm text-blue-600 hover:underline"
            >
              Back to login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function IPVerifyPage() {
  return (
    <Suspense>
      <IPVerifyInner />
    </Suspense>
  );
}
