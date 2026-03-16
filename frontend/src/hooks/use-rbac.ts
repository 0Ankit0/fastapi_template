'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as rbacApi from '@/lib/graphql/rbac';
import type { RoleCreate, PermissionCreate, RoleAssignment, PermissionAssignment } from '@/types';

export function useRoles(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['rbac', 'roles', params],
    queryFn: async () => rbacApi.roles(params),
  });
}

export function useRole(roleId: string) {
  return useQuery({
    queryKey: ['rbac', 'roles', roleId],
    queryFn: async () => rbacApi.role(roleId),
    enabled: !!roleId,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: RoleCreate) => rbacApi.createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'roles'] });
    },
  });
}

export function usePermissions(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['rbac', 'permissions', params],
    queryFn: async () => rbacApi.permissions(params),
  });
}

export function useCreatePermission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PermissionCreate) => rbacApi.createPermission(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'permissions'] });
    },
  });
}

export function useUserRoles(userId: string) {
  return useQuery({
    queryKey: ['rbac', 'user-roles', userId],
    queryFn: async () => rbacApi.userRoles(userId),
    enabled: !!userId,
  });
}

export function useAssignRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: RoleAssignment) => rbacApi.assignRole(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'user-roles', variables.user_id] });
    },
  });
}

export function useRemoveRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: RoleAssignment) => rbacApi.removeRole(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'user-roles', variables.user_id] });
    },
  });
}

export function useRolePermissions(roleId: string) {
  return useQuery({
    queryKey: ['rbac', 'role-permissions', roleId],
    queryFn: async () => rbacApi.rolePermissions(roleId),
    enabled: !!roleId,
  });
}

export function useAssignPermission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PermissionAssignment) => rbacApi.assignPermission(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'role-permissions', variables.role_id] });
    },
  });
}

export function useRemovePermission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PermissionAssignment) => rbacApi.removePermission(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rbac', 'role-permissions', variables.role_id] });
    },
  });
}

export function useCheckPermission(
  userId: string,
  resource: string,
  action: string,
  domain = 'global'
) {
  return useQuery({
    queryKey: ['rbac', 'check-permission', userId, domain, resource, action],
    queryFn: async () => rbacApi.checkPermission(userId, resource, action, domain),
    enabled: !!userId && !!resource && !!action,
  });
}

export function useCasbinRoles(userId: string, domain = 'global') {
  return useQuery({
    queryKey: ['rbac', 'casbin-roles', userId, domain],
    queryFn: async () => rbacApi.casbinRoles(userId, domain),
    enabled: !!userId,
  });
}

export function useCasbinPermissions(userId: string, domain = 'global') {
  return useQuery({
    queryKey: ['rbac', 'casbin-permissions', userId, domain],
    queryFn: async () => rbacApi.casbinPermissions(userId, domain),
    enabled: !!userId,
  });
}
