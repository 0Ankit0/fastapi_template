'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { CapabilitySummary, ProviderStatusResponse, PushConfigResponse } from '@/types';

export function useSystemCapabilities() {
  return useQuery({
    queryKey: ['system-capabilities'],
    queryFn: async () => {
      const response = await apiClient.get<CapabilitySummary>('/system/capabilities/');
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useSystemProviders() {
  return useQuery({
    queryKey: ['system-providers'],
    queryFn: async () => {
      const response = await apiClient.get<ProviderStatusResponse>('/system/providers/');
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function usePushConfig() {
  return useQuery({
    queryKey: ['push-config'],
    queryFn: async () => {
      const response = await apiClient.get<PushConfigResponse>('/notifications/push/config/');
      return response.data;
    },
    staleTime: 60_000,
  });
}
