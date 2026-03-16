'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { graphqlClient } from '@/lib/api-client';
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

const TENANTS_GRAPHQL_PATH = '/tenants';

async function graphqlRequest<T>(query: string, variables?: Record<string, unknown>) {
  const response = await graphqlClient.post<{ data?: T; errors?: Array<{ message: string }> }>(
    TENANTS_GRAPHQL_PATH,
    { query, variables }
  );

  if (response.data.errors && response.data.errors.length > 0) {
    throw new Error(response.data.errors[0].message);
  }

  return response.data.data as T;
}

interface TenantsResponse {
  items: Tenant[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export function useTenants(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', params],
    queryFn: async () => {
      const query = `query MyTenants($skip: Int, $limit: Int) { myTenants(skip: $skip, limit: $limit) { items { id name slug description is_active owner_id created_at updated_at members { id tenant_id user_id role is_active joined_at } } total skip limit has_more } }`;
      const data = await graphqlRequest<{ myTenants: TenantsResponse }>(query, params);
      return data.myTenants;
    },
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ['tenants', id],
    queryFn: async () => {
      const query = `query Tenant($tenantId: String!) { tenant(tenantId: $tenantId) { id name slug description is_active owner_id created_at updated_at members { id tenant_id user_id role is_active joined_at } } }`;
      const data = await graphqlRequest<{ tenant: TenantWithMembers }>(query, { tenantId: id });
      return data.tenant;
    },
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantCreate) => {
      const mutation = `mutation CreateTenant($data: TenantCreateInput!) { createTenant(data: $data) { id name slug description is_active owner_id created_at updated_at } }`;
      const response = await graphqlRequest<{ createTenant: Tenant }>(mutation, { data });
      return response.createTenant;
    },
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
    mutationFn: async ({ id, data }: { id: string; data: TenantUpdate }) => {
      const mutation = `mutation UpdateTenant($tenantId: String!, $data: TenantUpdateInput!) { updateTenant(tenantId: $tenantId, data: $data) { id name slug description is_active owner_id created_at updated_at } }`;
      const response = await graphqlRequest<{ updateTenant: Tenant }>(mutation, { tenantId: id, data });
      return response.updateTenant;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.id] });
    },
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const mutation = `mutation DeleteTenant($tenantId: String!) { deleteTenant(tenantId: $tenantId) }`;
      await graphqlRequest<{ deleteTenant: boolean }>(mutation, { tenantId: id });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

export function useTenantMembers(tenantId: string, params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', tenantId, 'members', params],
    queryFn: async () => {
      const query = `query TenantMembers($tenantId: String!, $skip: Int, $limit: Int) { tenantMembers(tenantId: $tenantId, skip: $skip, limit: $limit) { items { id tenant_id user_id role is_active joined_at } total skip limit has_more } }`;
      const data = await graphqlRequest<{ tenantMembers: PaginatedResponse<TenantMember> }>(query, {
        tenantId,
        ...params,
      });
      return data.tenantMembers;
    },
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
    }) => {
      const mutation = `mutation UpdateMemberRole($tenantId: String!, $userId: String!, $role: TenantRole!) { updateMemberRole(tenantId: $tenantId, userId: $userId, data: { role: $role }) { id tenant_id user_id role is_active joined_at } }`;
      const response = await graphqlRequest<{ updateMemberRole: TenantMember }>(mutation, {
        tenantId,
        userId,
        role,
      });
      return response.updateMemberRole;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'members'] });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tenantId, userId }: { tenantId: string; userId: string }) => {
      const mutation = `mutation RemoveMember($tenantId: String!, $userId: String!) { removeMember(tenantId: $tenantId, userId: $userId) }`;
      await graphqlRequest<{ removeMember: boolean }>(mutation, { tenantId, userId });
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'members'] });
    },
  });
}

export function useTenantInvitations(tenantId: string, params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tenants', tenantId, 'invitations', params],
    queryFn: async () => {
      const query = `query TenantInvitations($tenantId: String!, $skip: Int, $limit: Int) { tenantInvitations(tenantId: $tenantId, skip: $skip, limit: $limit) { items { id tenant_id email role status invited_by expires_at created_at accepted_at } total skip limit has_more } }`;
      const data = await graphqlRequest<{ tenantInvitations: PaginatedResponse<TenantInvitation> }>(query, {
        tenantId,
        ...params,
      });
      return data.tenantInvitations;
    },
    enabled: !!tenantId,
  });
}

export function useCreateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenantId,
      data,
    }: {
      tenantId: string;
      data: TenantInvitationCreate;
    }) => {
      const mutation = `mutation InviteMember($tenantId: String!, $data: TenantInvitationCreateInput!) { inviteMember(tenantId: $tenantId, data: $data) { id tenant_id email role status invited_by expires_at created_at accepted_at } }`;
      const response = await graphqlRequest<{ inviteMember: TenantInvitation }>(mutation, {
        tenantId,
        data,
      });
      return response.inviteMember;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tenants', variables.tenantId, 'invitations'] });
      analytics.capture(TenantEvents.TENANT_MEMBER_INVITED, { tenant_id: variables.tenantId });
    },
  });
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (token: string) => {
      const mutation = `mutation AcceptInvitation($data: AcceptInvitationInput!) { acceptInvitation(data: $data) { id tenant_id user_id role is_active joined_at } }`;
      const response = await graphqlRequest<{ acceptInvitation: TenantMember }>(mutation, { data: { token } });
      return response.acceptInvitation;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      analytics.capture(TenantEvents.TENANT_MEMBER_JOINED);
    },
  });
}

export function useDeleteInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tenantId,
      invitationId,
    }: {
      tenantId: string;
      invitationId: string;
    }) => {
      const mutation = `mutation RevokeInvitation($tenantId: String!, $invitationId: String!) { revokeInvitation(tenantId: $tenantId, invitationId: $invitationId) }`;
      await graphqlRequest<{ revokeInvitation: boolean }>(mutation, { tenantId, invitationId });
    },
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
