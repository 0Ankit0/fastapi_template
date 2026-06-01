'use client';

import { Link } from '@/lib/router';
import { usePolicies } from '@/hooks/use-rbac';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui';
import { ArrowLeft, ShieldCheck, Waypoints } from 'lucide-react';

export default function RbacPoliciesPage() {
  const { data: policies, isLoading } = usePolicies();

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
          <h1 className="text-2xl font-bold text-gray-900">Policy Explorer</h1>
          <p className="text-gray-500">Browse the effective role-to-policy bindings mirrored into Casbin.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Waypoints className="h-4 w-4 text-blue-600" />
            Effective Policies
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : !policies?.length ? (
            <p className="py-10 text-center text-sm text-gray-400">No policies are currently assigned.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Role</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Resource</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Domain</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {policies.map((policy) => (
                    <tr key={`${policy.role_id}:${policy.permission_id}`} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        <Link href={`/admin/rbac/${policy.role_id}`} className="hover:text-blue-600 hover:underline">
                          {policy.role_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{policy.resource}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">{policy.action}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{policy.domain}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{policy.description || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 text-blue-600" />
            <p className="text-sm text-gray-600">
              Role membership is managed from the user editor, and policy assignment is managed from each role detail page.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}