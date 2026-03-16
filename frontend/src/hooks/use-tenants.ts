'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as tenantApi from '@/lib/graphql/tenants';
import { useAuthStore } from '@/store/auth-store';
import { analytics } from '@/lib/analytics';
import { TenantEvents } from '@/lib/analytics/events';
import type {
  Tenant,
  TenantCreate,
  TenantInvitationCreate,
  TenantRole,
  TenantUpdate,
} from '@/types';

export function useTenants(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', params],
    queryFn: async () => tenantApi.tenants(params),
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ['tenants', id],
    queryFn: async () => tenantApi.tenant(id),
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantCreate) => tenantApi.createTenant(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      analytics.capture(TenantEvents.TENANT_CREATED, { name: data.name });
      analytics.group('organization', data.id, { name: data.name });
    },
  });
}

export function useUpdateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: TenantUpdate }) =>
      tenantApi.updateTenant(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.id] });
    },
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => tenantApi.deleteTenant(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

export function useTenantMembers(tenantId: string, params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', tenantId, 'members', params],
    queryFn: async () => tenantApi.tenantMembers(tenantId, params),
    enabled: !!tenantId,
  });
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenantId,
      userId,
      role,
    }: {
      tenantId: string;
      userId: string;
      role: TenantRole;
    }) => tenantApi.updateMemberRole(tenantId, userId, role),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'members'] });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tenantId, userId }: { tenantId: string; userId: string }) =>
      tenantApi.removeMember(tenantId, userId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'members'] });
    },
  });
}

export function useTenantInvitations(tenantId: string, params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', tenantId, 'invitations', params],
    queryFn: async () => tenantApi.tenantInvitations(tenantId, params),
    enabled: !!tenantId,
  });
}

export function useCreateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tenantId, data }: { tenantId: string; data: TenantInvitationCreate }) =>
      tenantApi.createInvitation(tenantId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'invitations'] });
      analytics.capture(TenantEvents.TENANT_MEMBER_INVITED, { tenant_id: variables.tenantId });
    },
  });
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (token: string) => tenantApi.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      analytics.capture(TenantEvents.TENANT_MEMBER_JOINED);
    },
  });
}

export function useDeleteInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tenantId, invitationId }: { tenantId: string; invitationId: string }) =>
      tenantApi.deleteInvitation(tenantId, invitationId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'invitations'] });
    },
  });
}

export function useSwitchTenant() {
  const { setTenant } = useAuthStore();

  return useMutation({
    mutationFn: async (tenant: Tenant) => {
      setTenant(tenant);
      return tenant;
    },
    onSuccess: (tenant) => {
      analytics.group('organization', tenant.id, { name: tenant.name });
    },
  });
}
