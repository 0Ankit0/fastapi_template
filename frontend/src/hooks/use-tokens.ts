'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as tokenApi from '@/lib/graphql/tokens';

export function useTokens(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tokens', params],
    queryFn: async () => tokenApi.tokens(params),
  });
}

export function useRevokeToken() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tokenId: string) => tokenApi.revokeToken(tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
  });
}

export function useRevokeAllTokens() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => tokenApi.revokeAllTokens(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
  });
}
