'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { IPAccessControl, IPAccessControlUpdate, PaginatedResponse } from '@/types';

export function useIPAccessControls(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['ip-access', params],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<IPAccessControl>>('/ip-access/', {
        params,
      });
      return response.data;
    },
  });
}

export function useIPAccessControl(ipId: string) {
  return useQuery({
    queryKey: ['ip-access', ipId],
    queryFn: async () => {
      const response = await apiClient.get<IPAccessControl>(`/ip-access/${ipId}`);
      return response.data;
    },
    enabled: !!ipId,
  });
}

export function useUpdateIPAccess() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ipId, data }: { ipId: string; data: IPAccessControlUpdate }) => {
      const response = await apiClient.patch<IPAccessControl>(`/ip-access/${ipId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ip-access'] });
    },
  });
}

/** Called from the /ip-access/verify page to action an email link token. */
export function useVerifyIPToken() {
  return useMutation({
    mutationFn: async (t: string) => {
      const response = await apiClient.get<{ message: string }>('/ip-access/verify', {
        params: { t },
      });
      return response.data;
    },
  });
}
