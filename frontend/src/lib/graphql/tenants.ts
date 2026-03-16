import { graphqlRequest } from '@/lib/graphql-client';
import type {
  PaginatedResponse,
  Tenant,
  TenantCreate,
  TenantInvitation,
  TenantInvitationCreate,
  TenantMember,
  TenantRole,
  TenantUpdate,
  TenantWithMembers,
} from '@/types';

interface TenantsResponse {
  items: Tenant[];
  total: number;
  skip: number;
  limit: number;
}

export async function tenants(params?: {
  skip?: number;
  limit?: number;
}): Promise<TenantsResponse> {
  const data = await graphqlRequest<{ tenants: TenantsResponse }, { input?: typeof params }>(
    `query Tenants($input: PaginationInput) {
      tenants(input: $input) {
        items {
          id
          name
          slug
          description
          is_active
          owner_id
          created_at
          updated_at
        }
        total
        skip
        limit
      }
    }`,
    { input: params }
  );
  return data.tenants;
}

export async function tenant(id: string): Promise<TenantWithMembers> {
  const data = await graphqlRequest<{ tenant: TenantWithMembers }, { id: string }>(
    `query Tenant($id: ID!) {
      tenant(id: $id) {
        id
        name
        slug
        description
        is_active
        owner_id
        created_at
        updated_at
        members {
          id
          tenant_id
          user_id
          role
          is_active
          joined_at
        }
      }
    }`,
    { id }
  );
  return data.tenant;
}

export async function createTenant(input: TenantCreate): Promise<Tenant> {
  const data = await graphqlRequest<{ createTenant: Tenant }, { input: TenantCreate }>(
    `mutation CreateTenant($input: TenantCreateInput!) {
      createTenant(input: $input) {
        id
        name
        slug
        description
        is_active
        owner_id
        created_at
        updated_at
      }
    }`,
    { input }
  );
  return data.createTenant;
}

export async function updateTenant(id: string, input: TenantUpdate): Promise<Tenant> {
  const data = await graphqlRequest<{ updateTenant: Tenant }, { id: string; input: TenantUpdate }>(
    `mutation UpdateTenant($id: ID!, $input: TenantUpdateInput!) {
      updateTenant(id: $id, input: $input) {
        id
        name
        slug
        description
        is_active
        owner_id
        created_at
        updated_at
      }
    }`,
    { id, input }
  );
  return data.updateTenant;
}

export async function deleteTenant(id: string): Promise<boolean> {
  const data = await graphqlRequest<{ deleteTenant: boolean }, { id: string }>(
    `mutation DeleteTenant($id: ID!) {
      deleteTenant(id: $id)
    }`,
    { id }
  );
  return data.deleteTenant;
}

export async function tenantMembers(
  tenantId: string,
  params?: { skip?: number; limit?: number }
): Promise<PaginatedResponse<TenantMember>> {
  const data = await graphqlRequest<
    { tenantMembers: PaginatedResponse<TenantMember> },
    { tenantId: string; input?: typeof params }
  >(
    `query TenantMembers($tenantId: ID!, $input: PaginationInput) {
      tenantMembers(tenantId: $tenantId, input: $input) {
        items {
          id
          tenant_id
          user_id
          role
          is_active
          joined_at
        }
        total
        skip
        limit
      }
    }`,
    { tenantId, input: params }
  );
  return data.tenantMembers;
}

export async function updateMemberRole(
  tenantId: string,
  userId: string,
  role: TenantRole
): Promise<TenantMember> {
  const data = await graphqlRequest<
    { updateTenantMemberRole: TenantMember },
    { tenantId: string; userId: string; role: TenantRole }
  >(
    `mutation UpdateTenantMemberRole($tenantId: ID!, $userId: ID!, $role: String!) {
      updateTenantMemberRole(tenantId: $tenantId, userId: $userId, role: $role) {
        id
        tenant_id
        user_id
        role
        is_active
        joined_at
      }
    }`,
    { tenantId, userId, role }
  );
  return data.updateTenantMemberRole;
}

export async function removeMember(tenantId: string, userId: string): Promise<boolean> {
  const data = await graphqlRequest<
    { removeTenantMember: boolean },
    { tenantId: string; userId: string }
  >(
    `mutation RemoveTenantMember($tenantId: ID!, $userId: ID!) {
      removeTenantMember(tenantId: $tenantId, userId: $userId)
    }`,
    { tenantId, userId }
  );
  return data.removeTenantMember;
}

export async function tenantInvitations(
  tenantId: string,
  params?: { skip?: number; limit?: number }
): Promise<PaginatedResponse<TenantInvitation>> {
  const data = await graphqlRequest<
    { tenantInvitations: PaginatedResponse<TenantInvitation> },
    { tenantId: string; input?: typeof params }
  >(
    `query TenantInvitations($tenantId: ID!, $input: PaginationInput) {
      tenantInvitations(tenantId: $tenantId, input: $input) {
        items {
          id
          tenant_id
          email
          role
          status
          invited_by
          expires_at
          created_at
          accepted_at
        }
        total
        skip
        limit
      }
    }`,
    { tenantId, input: params }
  );
  return data.tenantInvitations;
}

export async function createInvitation(
  tenantId: string,
  input: TenantInvitationCreate
): Promise<TenantInvitation> {
  const data = await graphqlRequest<
    { createTenantInvitation: TenantInvitation },
    { tenantId: string; input: TenantInvitationCreate }
  >(
    `mutation CreateTenantInvitation($tenantId: ID!, $input: TenantInvitationCreateInput!) {
      createTenantInvitation(tenantId: $tenantId, input: $input) {
        id
        tenant_id
        email
        role
        status
        invited_by
        expires_at
        created_at
        accepted_at
      }
    }`,
    { tenantId, input }
  );
  return data.createTenantInvitation;
}

export async function acceptInvitation(token: string): Promise<boolean> {
  const data = await graphqlRequest<{ acceptTenantInvitation: boolean }, { token: string }>(
    `mutation AcceptTenantInvitation($token: String!) {
      acceptTenantInvitation(token: $token)
    }`,
    { token }
  );
  return data.acceptTenantInvitation;
}

export async function deleteInvitation(tenantId: string, invitationId: string): Promise<boolean> {
  const data = await graphqlRequest<
    { deleteTenantInvitation: boolean },
    { tenantId: string; invitationId: string }
  >(
    `mutation DeleteTenantInvitation($tenantId: ID!, $invitationId: ID!) {
      deleteTenantInvitation(tenantId: $tenantId, invitationId: $invitationId)
    }`,
    { tenantId, invitationId }
  );
  return data.deleteTenantInvitation;
}
