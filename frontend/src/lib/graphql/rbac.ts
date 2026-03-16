import { graphqlRequest } from '@/lib/graphql-client';
import type {
  CheckPermissionResponse,
  PaginatedResponse,
  Permission,
  PermissionAssignment,
  PermissionCreate,
  Role,
  RoleAssignment,
  RoleCreate,
  RolePermissionsResponse,
  UserRolesResponse,
} from '@/types';

export async function roles(params?: {
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<Role>> {
  const data = await graphqlRequest<{ roles: PaginatedResponse<Role> }, { input?: typeof params }>(
    `query Roles($input: PaginationInput) {
      roles(input: $input) {
        items { id name description created_at updated_at }
        total
        skip
        limit
      }
    }`,
    { input: params }
  );
  return data.roles;
}

export async function role(roleId: string): Promise<Role> {
  const data = await graphqlRequest<{ role: Role }, { roleId: string }>(
    `query Role($roleId: ID!) {
      role(roleId: $roleId) { id name description created_at updated_at }
    }`,
    { roleId }
  );
  return data.role;
}

export async function createRole(input: RoleCreate): Promise<Role> {
  const data = await graphqlRequest<{ createRole: Role }, { input: RoleCreate }>(
    `mutation CreateRole($input: RoleCreateInput!) {
      createRole(input: $input) { id name description created_at updated_at }
    }`,
    { input }
  );
  return data.createRole;
}

export async function permissions(params?: {
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<Permission>> {
  const data = await graphqlRequest<
    { permissions: PaginatedResponse<Permission> },
    { input?: typeof params }
  >(
    `query Permissions($input: PaginationInput) {
      permissions(input: $input) {
        items { id resource action description created_at }
        total
        skip
        limit
      }
    }`,
    { input: params }
  );
  return data.permissions;
}

export async function createPermission(input: PermissionCreate): Promise<Permission> {
  const data = await graphqlRequest<{ createPermission: Permission }, { input: PermissionCreate }>(
    `mutation CreatePermission($input: PermissionCreateInput!) {
      createPermission(input: $input) { id resource action description created_at }
    }`,
    { input }
  );
  return data.createPermission;
}

export async function userRoles(userId: string): Promise<UserRolesResponse> {
  const data = await graphqlRequest<{ userRoles: UserRolesResponse }, { userId: string }>(
    `query UserRoles($userId: ID!) {
      userRoles(userId: $userId) {
        user_id
        roles { id name description created_at updated_at }
      }
    }`,
    { userId }
  );
  return data.userRoles;
}

export async function assignRole(input: RoleAssignment): Promise<boolean> {
  const data = await graphqlRequest<{ assignRole: boolean }, { input: RoleAssignment }>(
    `mutation AssignRole($input: RoleAssignmentInput!) {
      assignRole(input: $input)
    }`,
    { input }
  );
  return data.assignRole;
}

export async function removeRole(input: RoleAssignment): Promise<boolean> {
  const data = await graphqlRequest<{ removeRole: boolean }, { input: RoleAssignment }>(
    `mutation RemoveRole($input: RoleAssignmentInput!) {
      removeRole(input: $input)
    }`,
    { input }
  );
  return data.removeRole;
}

export async function rolePermissions(roleId: string): Promise<RolePermissionsResponse> {
  const data = await graphqlRequest<
    { rolePermissions: RolePermissionsResponse },
    { roleId: string }
  >(
    `query RolePermissions($roleId: ID!) {
      rolePermissions(roleId: $roleId) {
        role_id
        permissions { id resource action description created_at }
      }
    }`,
    { roleId }
  );
  return data.rolePermissions;
}

export async function assignPermission(input: PermissionAssignment): Promise<boolean> {
  const data = await graphqlRequest<{ assignPermission: boolean }, { input: PermissionAssignment }>(
    `mutation AssignPermission($input: PermissionAssignmentInput!) {
      assignPermission(input: $input)
    }`,
    { input }
  );
  return data.assignPermission;
}

export async function removePermission(input: PermissionAssignment): Promise<boolean> {
  const data = await graphqlRequest<{ removePermission: boolean }, { input: PermissionAssignment }>(
    `mutation RemovePermission($input: PermissionAssignmentInput!) {
      removePermission(input: $input)
    }`,
    { input }
  );
  return data.removePermission;
}

export async function checkPermission(
  userId: string,
  resource: string,
  action: string,
  domain = 'global'
): Promise<CheckPermissionResponse> {
  const data = await graphqlRequest<
    { checkPermission: CheckPermissionResponse },
    { userId: string; resource: string; action: string; domain: string }
  >(
    `query CheckPermission($userId: ID!, $resource: String!, $action: String!, $domain: String!) {
      checkPermission(userId: $userId, resource: $resource, action: $action, domain: $domain) {
        user_id
        resource
        action
        allowed
      }
    }`,
    { userId, resource, action, domain }
  );
  return data.checkPermission;
}

export async function casbinRoles(userId: string, domain = 'global') {
  const data = await graphqlRequest<
    { casbinRoles: { user_id: number; domain: string; roles: string[] } },
    { userId: string; domain: string }
  >(
    `query CasbinRoles($userId: ID!, $domain: String!) {
      casbinRoles(userId: $userId, domain: $domain) {
        user_id
        domain
        roles
      }
    }`,
    { userId, domain }
  );
  return data.casbinRoles;
}

export async function casbinPermissions(userId: string, domain = 'global') {
  const data = await graphqlRequest<
    { casbinPermissions: { user_id: number; domain: string; permissions: string[][] } },
    { userId: string; domain: string }
  >(
    `query CasbinPermissions($userId: ID!, $domain: String!) {
      casbinPermissions(userId: $userId, domain: $domain) {
        user_id
        domain
        permissions
      }
    }`,
    { userId, domain }
  );
  return data.casbinPermissions;
}
