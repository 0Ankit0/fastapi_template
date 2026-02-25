'use client';

import { useState } from 'react';
import { useInitiatePayment, usePaymentProviders } from '@/hooks/use-finances';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CreditCard, ExternalLink } from 'lucide-react';
import type { PaymentProvider, InitiatePaymentRequest } from '@/types';

interface PaymentInitiateFormProps {
  purchaseOrderId: string;
  purchaseOrderName: string;
  amount: number;
  returnUrl: string;
  onSuccess?: (paymentUrl: string) => void;
  onError?: (error: Error) => void;
}

export function PaymentInitiateForm({
  purchaseOrderId,
  purchaseOrderName,
  amount,
  returnUrl,
  onSuccess,
  onError,
}: PaymentInitiateFormProps) {
  const [selectedProvider, setSelectedProvider] = useState<PaymentProvider | ''>('');
  const { data: providers, isLoading: loadingProviders } = usePaymentProviders();
  const initiatePayment = useInitiatePayment();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider) return;

    const payload: InitiatePaymentRequest = {
      provider: selectedProvider as PaymentProvider,
      amount,
      purchase_order_id: purchaseOrderId,
      purchase_order_name: purchaseOrderName,
      return_url: returnUrl,
      website_url: typeof window !== 'undefined' ? window.location.origin : '',
    };

    initiatePayment.mutate(payload, {
      onSuccess: (data) => {
        if (data.payment_url) {
          onSuccess?.(data.payment_url);
          window.location.href = data.payment_url;
        }
      },
      onError: (err) => onError?.(err as Error),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-5 w-5" />
          Select Payment Method
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Amount: {(amount / 100).toFixed(2)}
            </label>
            <div className="grid grid-cols-2 gap-2">
              {loadingProviders && (
                <p className="text-sm text-gray-500 col-span-2">Loading providers…</p>
              )}
              {providers?.map((provider) => (
                <button
                  key={provider}
                  type="button"
                  onClick={() => setSelectedProvider(provider)}
                  className={`p-3 rounded-lg border text-sm font-medium capitalize transition-colors ${
                    selectedProvider === provider
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {provider}
                </button>
              ))}
            </div>
          </div>

          <Button
            type="submit"
            className="w-full"
            isLoading={initiatePayment.isPending}
            disabled={!selectedProvider}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Pay with {selectedProvider || '…'}
          </Button>

          {initiatePayment.error && (
            <p className="text-sm text-red-600">Payment initiation failed. Please try again.</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
