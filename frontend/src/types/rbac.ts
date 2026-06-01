// RBAC module types

export interface Role {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: string;
  resource: string;
  action: string;
  description: string;
  created_at: string;
}

export interface RoleCreate {
  name: string;
  description?: string;
}

export interface PermissionCreate {
  resource: string;
  action: string;
  description?: string;
}

export interface RoleAssignment {
  user_id: string;
  role_id: string;
}

export interface PermissionAssignment {
  role_id: string;
  permission_id: string;
}

export interface UserRolesResponse {
  user_id: string;
  roles: Role[];
}

export interface RolePermissionsResponse {
  role_id: string;
  permissions: Permission[];
}

export interface RoleUserSummary {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface RoleUsersResponse {
  role_id: string;
  users: RoleUserSummary[];
}

export interface RolePolicyResponse {
  domain: string;
  role_id: string;
  role_name: string;
  permission_id: string;
  resource: string;
  action: string;
  description: string;
}

export interface CheckPermissionResponse {
  user_id: string;
  resource: string;
  action: string;
  allowed: boolean;
}

export interface CasbinRolesResponse {
  user_id: string;
  domain: string;
  roles: string[];
}

export interface CasbinPermissionsResponse {
  user_id: string;
  domain: string;
  permissions: string[][];
}
