'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/auth-store';
import * as userApi from '@/lib/graphql/users';
import { analytics } from '@/lib/analytics';
import { UserEvents } from '@/lib/analytics/events';
import type { User, UserUpdate, PaginatedResponse } from '@/types';

export function useCurrentUser() {
  const { setUser } = useAuthStore();

  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const user = await (await import('@/lib/graphql/auth')).currentUser();
      setUser(user);
      return user;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { setUser } = useAuthStore();

  return useMutation({
    mutationFn: async (data: UserUpdate) => {
      return userApi.updateProfile(data);
    },
    onSuccess: (data) => {
      setUser(data);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(UserEvents.PROFILE_UPDATED);
    },
  });
}

export function useListUsers(params?: {
  skip?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: async () => {
      return userApi.listUsers(params);
    },
  });
}

export function useGetUser(userId: string) {
  return useQuery({
    queryKey: ['users', userId],
    queryFn: async () => {
      return userApi.getUser(userId);
    },
    enabled: !!userId,
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, data }: { userId: string; data: UserUpdate }) => {
      return userApi.updateUser(userId, data);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users', variables.userId] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: string) => {
      await userApi.deleteUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
