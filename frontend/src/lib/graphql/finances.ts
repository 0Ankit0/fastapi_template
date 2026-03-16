import { graphqlRequest } from '@/lib/graphql-client';
import type {
  InitiatePaymentRequest,
  InitiatePaymentResponse,
  PaymentProvider,
  PaymentTransaction,
  VerifyPaymentRequest,
  VerifyPaymentResponse,
} from '@/types';

export async function paymentProviders(): Promise<PaymentProvider[]> {
  const data = await graphqlRequest<{ paymentProviders: PaymentProvider[] }>(
    `query PaymentProviders {
      paymentProviders
    }`
  );
  return data.paymentProviders;
}

export async function initiatePayment(
  input: InitiatePaymentRequest
): Promise<InitiatePaymentResponse> {
  const data = await graphqlRequest<
    { initiatePayment: InitiatePaymentResponse },
    { input: InitiatePaymentRequest }
  >(
    `mutation InitiatePayment($input: InitiatePaymentInput!) {
      initiatePayment(input: $input) {
        transaction_id
        provider
        status
        payment_url
        provider_pidx
        extra
      }
    }`,
    { input }
  );
  return data.initiatePayment;
}

export async function verifyPayment(input: VerifyPaymentRequest): Promise<VerifyPaymentResponse> {
  const data = await graphqlRequest<
    { verifyPayment: VerifyPaymentResponse },
    { input: VerifyPaymentRequest }
  >(
    `mutation VerifyPayment($input: VerifyPaymentInput!) {
      verifyPayment(input: $input) {
        transaction_id
        provider
        status
        amount
        provider_transaction_id
        extra
      }
    }`,
    { input }
  );
  return data.verifyPayment;
}

export async function transaction(transactionId: number): Promise<PaymentTransaction> {
  const data = await graphqlRequest<
    { paymentTransaction: PaymentTransaction },
    { transactionId: number }
  >(
    `query PaymentTransaction($transactionId: Int!) {
      paymentTransaction(transactionId: $transactionId) {
        id
        provider
        status
        amount
        currency
        purchase_order_id
        purchase_order_name
        provider_transaction_id
        provider_pidx
        return_url
        website_url
        failure_reason
        created_at
        updated_at
      }
    }`,
    { transactionId }
  );
  return data.paymentTransaction;
}

export async function transactions(params?: {
  limit?: number;
  offset?: number;
  provider?: string;
}): Promise<PaymentTransaction[]> {
  const data = await graphqlRequest<
    { paymentTransactions: PaymentTransaction[] },
    { input?: { limit?: number; offset?: number; provider?: string } }
  >(
    `query PaymentTransactions($input: PaymentTransactionsFilterInput) {
      paymentTransactions(input: $input) {
        id
        provider
        status
        amount
        currency
        purchase_order_id
        purchase_order_name
        provider_transaction_id
        provider_pidx
        return_url
        website_url
        failure_reason
        created_at
        updated_at
      }
    }`,
    { input: params }
  );
  return data.paymentTransactions;
}
