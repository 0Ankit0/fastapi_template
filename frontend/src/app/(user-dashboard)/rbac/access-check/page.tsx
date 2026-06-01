'use client';

import { useMemo, useState } from 'react';
import { Link } from '@/lib/router';
import { useListUsers } from '@/hooks/use-users';
import { useCasbinPermissions, useCasbinRoles, useCheckPermission } from '@/hooks/use-rbac';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, SearchCheck } from 'lucide-react';

export default function RbacAccessCheckPage() {
  const [userId, setUserId] = useState('');
  const [resource, setResource] = useState('rbac');
  const [action, setAction] = useState('manage');
  const { data: usersData } = useListUsers({ limit: 200 });
  const checkQuery = useCheckPermission(userId, resource, action);
  const rolesQuery = useCasbinRoles(userId);
  const permissionsQuery = useCasbinPermissions(userId);

  const selectedUser = useMemo(
    () => (usersData?.items ?? []).find((user) => user.id === userId),
    [userId, usersData?.items]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Link
          href="/admin/rbac"
          className="mt-1 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Access Check</h1>
          <p className="text-gray-500">Verify whether a role assignment grants access to a resource and action.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <SearchCheck className="h-4 w-4 text-blue-600" />
            Authorization Simulator
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
          <label className="space-y-2">
            <span className="text-sm font-medium text-gray-700">User</span>
            <select
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select a user</option>
              {(usersData?.items ?? []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-gray-700">Resource</span>
            <input
              value={resource}
              onChange={(event) => setResource(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="rbac"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-gray-700">Action</span>
            <input
              value={action}
              onChange={(event) => setAction(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="manage"
            />
          </label>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Result</CardTitle>
          </CardHeader>
          <CardContent>
            {!userId ? (
              <p className="text-sm text-gray-400">Pick a user to start a check.</p>
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{selectedUser?.username ?? 'Unknown user'}</p>
                  <p className="text-xs text-gray-500">{selectedUser?.email ?? '—'}</p>
                </div>
                <div className={`rounded-xl px-4 py-3 text-sm font-medium ${checkQuery.data?.allowed ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  {checkQuery.isLoading ? 'Checking access…' : checkQuery.data?.allowed ? 'Allowed' : 'Denied'}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resolved Roles</CardTitle>
            </CardHeader>
            <CardContent>
              {!rolesQuery.data?.roles.length ? (
                <p className="text-sm text-gray-400">No Casbin roles resolved for this user.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {rolesQuery.data.roles.map((role) => (
                    <span key={role} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                      {role}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Effective Permissions</CardTitle>
            </CardHeader>
            <CardContent>
              {!permissionsQuery.data?.permissions.length ? (
                <p className="text-sm text-gray-400">No effective permissions were returned.</p>
              ) : (
                <div className="space-y-2">
                  {permissionsQuery.data.permissions.map((permission) => (
                    <div key={permission.join(':')} className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700">
                      {permission.join(' • ')}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}