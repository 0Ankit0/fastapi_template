'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as notificationApi from '@/lib/graphql/notifications';
import type { NotificationPreferenceUpdate } from '@/types';

export function useNotifications(params?: {
  unread_only?: boolean;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: async () => notificationApi.notifications(params),
  });
}

export function useGetNotification(id: number) {
  return useQuery({
    queryKey: ['notifications', id],
    queryFn: async () => notificationApi.notification(id),
    enabled: !!id,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => notificationApi.markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => notificationApi.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useDeleteNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => notificationApi.deleteNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useCreateNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { user_id: number; title: string; body: string; type?: string }) =>
      notificationApi.createNotification(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: ['notification-preferences'],
    queryFn: async () => notificationApi.notificationPreferences(),
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NotificationPreferenceUpdate) =>
      notificationApi.updateNotificationPreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}

export function useRegisterPushSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { endpoint: string; p256dh: string; auth: string }) =>
      notificationApi.registerPushSubscription(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}

export function useRemovePushSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => notificationApi.removePushSubscription(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}
