'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as financeApi from '@/lib/graphql/finances';
import { analytics } from '@/lib/analytics';
import { PaymentEvents } from '@/lib/analytics/events';
import type { InitiatePaymentRequest, VerifyPaymentRequest } from '@/types';

export function usePaymentProviders() {
  return useQuery({
    queryKey: ['payment-providers'],
    queryFn: async () => financeApi.paymentProviders(),
  });
}

export function useInitiatePayment() {
  return useMutation({
    mutationFn: async (data: InitiatePaymentRequest) => financeApi.initiatePayment(data),
    onSuccess: (data, variables) => {
      analytics.capture(PaymentEvents.PAYMENT_INITIATED, {
        provider: variables.provider,
        amount: variables.amount,
        order_id: variables.purchase_order_id,
      });
    },
  });
}

export function useVerifyPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: VerifyPaymentRequest) => financeApi.verifyPayment(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      analytics.capture(
        data.status === 'completed'
          ? PaymentEvents.PAYMENT_COMPLETED
          : PaymentEvents.PAYMENT_FAILED,
        { provider: data.provider, status: data.status }
      );
    },
  });
}

export function useTransaction(transactionId: number) {
  return useQuery({
    queryKey: ['transactions', transactionId],
    queryFn: async () => financeApi.transaction(transactionId),
    enabled: !!transactionId,
  });
}

export function useTransactions(params?: { limit?: number; offset?: number; provider?: string }) {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: async () => financeApi.transactions(params),
  });
}
