'use client';

import { useState } from 'react';
import {
  useRoles,
  usePermissions,
  useCreateRole,
  useCreatePermission,
  useAssignPermission,
  useRemovePermission,
  useRolePermissions,
  useUserRoles,
  useAssignRole,
  useRemoveRole,
} from '@/hooks/use-rbac';
import { Card, CardContent } from '@/components/ui/card';
import { Button, Skeleton } from '@/components/ui';
import { ShieldCheck, Key, Users, Plus, X, ChevronDown, ChevronRight, Trash2 } from 'lucide-react';
import type { Role, Permission } from '@/types';

type Tab = 'roles' | 'permissions' | 'user-roles';

// ── Role row with expandable permissions ─────────────────────────────────────
function RoleRow({ role }: { role: Role }) {
  const [expanded, setExpanded] = useState(false);
  const [permId, setPermId] = useState('');
  const { data: permData, isLoading } = useRolePermissions(expanded ? role.id : '');
  const assignPerm = useAssignPermission();
  const removePerm = useRemovePermission();

  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50">
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-gray-400 hover:text-gray-700"
            >
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
            <span className="text-sm font-medium text-gray-900">{role.name}</span>
          </div>
        </td>
        <td className="px-4 py-3 text-sm text-gray-500">{role.description || '—'}</td>
        <td className="px-4 py-3 text-sm text-gray-400">
          {new Date(role.created_at).toLocaleDateString()}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-blue-50/40">
          <td colSpan={3} className="px-8 py-3">
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Permissions</p>
            {isLoading && <Skeleton className="h-6 w-48" />}
            <div className="flex flex-wrap gap-2 mb-2">
              {(permData?.permissions ?? []).map((perm) => (
                <span
                  key={perm.id}
                  className="inline-flex items-center gap-1 rounded-full bg-blue-100 text-blue-700 text-xs px-2 py-0.5"
                >
                  {perm.resource}:{perm.action}
                  <button
                    onClick={() => removePerm.mutate({ role_id: role.id, permission_id: perm.id })}
                    className="ml-0.5 hover:text-red-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              {!isLoading && permData?.permissions.length === 0 && (
                <span className="text-xs text-gray-400">No permissions assigned.</span>
              )}
            </div>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                placeholder="Permission ID"
                value={permId}
                onChange={(e) => setPermId(e.target.value)}
                className="rounded border border-gray-300 px-2 py-1 text-xs w-40"
              />
              <Button
                size="sm"
                onClick={() => {
                  if (!permId.trim()) return;
                  assignPerm.mutate(
                    { role_id: role.id, permission_id: permId.trim() },
                    { onSuccess: () => setPermId('') }
                  );
                }}
                disabled={assignPerm.isPending}
              >
                <Plus className="h-3 w-3 mr-1" /> Assign
              </Button>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── User Roles tab ────────────────────────────────────────────────────────────
function UserRolesTab() {
  const [userId, setUserId] = useState('');
  const [activeUserId, setActiveUserId] = useState('');
  const [roleId, setRoleId] = useState('');
  const { data, isLoading } = useUserRoles(activeUserId);
  const assignRole = useAssignRole();
  const removeRole = useRemoveRole();

  const roles = data?.roles ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Look up a user's roles</p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="User ID (hashid)"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <Button onClick={() => setActiveUserId(userId.trim())} disabled={!userId.trim()}>
              Look up
            </Button>
          </div>
        </CardContent>
      </Card>

      {activeUserId && (
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-gray-500 mb-2">User: <code className="bg-gray-100 px-1 rounded">{activeUserId}</code></p>
            {isLoading && <Skeleton className="h-8 w-full" />}
            <div className="flex flex-wrap gap-2 mb-3">
              {roles.map((role: Role) => (
                <span
                  key={role.id}
                  className="inline-flex items-center gap-1 rounded-full bg-purple-100 text-purple-700 text-sm px-3 py-1"
                >
                  {role.name}
                  <button
                    onClick={() => removeRole.mutate({ user_id: activeUserId, role_id: role.id })}
                    className="ml-0.5 hover:text-red-600"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </span>
              ))}
              {!isLoading && roles.length === 0 && (
                <p className="text-sm text-gray-400">No roles assigned to this user.</p>
              )}
            </div>
            <div className="flex gap-2 items-center border-t border-gray-100 pt-3">
              <input
                type="text"
                placeholder="Role ID to assign"
                value={roleId}
                onChange={(e) => setRoleId(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-48"
              />
              <Button
                size="sm"
                onClick={() => {
                  if (!roleId.trim()) return;
                  assignRole.mutate(
                    { user_id: activeUserId, role_id: roleId.trim() },
                    { onSuccess: () => setRoleId('') }
                  );
                }}
                disabled={assignRole.isPending}
              >
                <Plus className="h-3.5 w-3.5 mr-1" /> Assign Role
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function RBACPage() {
  const [activeTab, setActiveTab] = useState<Tab>('roles');

  const rolesQuery = useRoles();
  const permissionsQuery = usePermissions();
  const createRole = useCreateRole();
  const createPermission = useCreatePermission();

  const [showRoleForm, setShowRoleForm] = useState(false);
  const [roleName, setRoleName] = useState('');
  const [roleDesc, setRoleDesc] = useState('');

  const [showPermForm, setShowPermForm] = useState(false);
  const [permResource, setPermResource] = useState('');
  const [permAction, setPermAction] = useState('');
  const [permDesc, setPermDesc] = useState('');

  const handleCreateRole = (e: React.FormEvent) => {
    e.preventDefault();
    createRole.mutate(
      { name: roleName, description: roleDesc },
      { onSuccess: () => { setRoleName(''); setRoleDesc(''); setShowRoleForm(false); } }
    );
  };

  const handleCreatePermission = (e: React.FormEvent) => {
    e.preventDefault();
    createPermission.mutate(
      { resource: permResource, action: permAction, description: permDesc },
      { onSuccess: () => { setPermResource(''); setPermAction(''); setPermDesc(''); setShowPermForm(false); } }
    );
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'roles', label: 'Roles', icon: <ShieldCheck className="h-4 w-4" /> },
    { id: 'permissions', label: 'Permissions', icon: <Key className="h-4 w-4" /> },
    { id: 'user-roles', label: 'User Roles', icon: <Users className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Roles & Permissions</h1>
        <p className="text-gray-500">Manage access control for your application</p>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'roles' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowRoleForm(!showRoleForm)}>
              <Plus className="h-4 w-4 mr-2" /> New Role
            </Button>
          </div>

          {showRoleForm && (
            <Card>
              <CardContent className="pt-4">
                <form onSubmit={handleCreateRole} className="space-y-3">
                  <h3 className="font-semibold text-gray-900">Create Role</h3>
                  <input
                    type="text"
                    placeholder="Role name"
                    value={roleName}
                    onChange={(e) => setRoleName(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Description (optional)"
                    value={roleDesc}
                    onChange={(e) => setRoleDesc(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                  <div className="flex gap-2">
                    <Button type="submit" disabled={createRole.isPending}>
                      {createRole.isPending ? 'Creating…' : 'Create'}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => setShowRoleForm(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                </tr>
              </thead>
              <tbody>
                {rolesQuery.isLoading && (
                  <tr><td colSpan={3} className="px-4 py-4 text-center text-gray-500">Loading…</td></tr>
                )}
                {(rolesQuery.data?.items ?? []).map((role) => (
                  <RoleRow key={role.id} role={role} />
                ))}
                {!rolesQuery.isLoading && rolesQuery.data?.items.length === 0 && (
                  <tr><td colSpan={3} className="px-4 py-6 text-center text-gray-500">No roles found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'permissions' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowPermForm(!showPermForm)}>
              <Plus className="h-4 w-4 mr-2" /> New Permission
            </Button>
          </div>

          {showPermForm && (
            <Card>
              <CardContent className="pt-4">
                <form onSubmit={handleCreatePermission} className="space-y-3">
                  <h3 className="font-semibold text-gray-900">Create Permission</h3>
                  <input
                    type="text"
                    placeholder="Resource (e.g. users)"
                    value={permResource}
                    onChange={(e) => setPermResource(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Action (e.g. read)"
                    value={permAction}
                    onChange={(e) => setPermAction(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Description (optional)"
                    value={permDesc}
                    onChange={(e) => setPermDesc(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                  <div className="flex gap-2">
                    <Button type="submit" disabled={createPermission.isPending}>
                      {createPermission.isPending ? 'Creating…' : 'Create'}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => setShowPermForm(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {permissionsQuery.isLoading && (
                  <tr><td colSpan={3} className="px-4 py-4 text-center text-gray-500">Loading…</td></tr>
                )}
                {(permissionsQuery.data?.items ?? []).map((perm) => (
                  <tr key={perm.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{perm.resource}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{perm.action}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{perm.description || '—'}</td>
                  </tr>
                ))}
                {!permissionsQuery.isLoading && permissionsQuery.data?.items.length === 0 && (
                  <tr><td colSpan={3} className="px-4 py-6 text-center text-gray-500">No permissions found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'user-roles' && <UserRolesTab />}
    </div>
  );
}
