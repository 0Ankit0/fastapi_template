'use client';

import { useIPAccessControls, useUpdateIPAccess } from '@/hooks/use-ip-access';
import type { IpAccessStatus } from '@/types';

const statusColors: Record<IpAccessStatus, string> = {
  whitelisted: 'bg-green-100 text-green-800',
  blacklisted: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
};

export default function IPAccessPage() {
  const ipQuery = useIPAccessControls();
  const updateIP = useUpdateIPAccess();

  const handleStatusChange = (ipId: string, status: IpAccessStatus) => {
    updateIP.mutate({ ipId, data: { status } });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">IP Access Control</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage which IP addresses are allowed or blocked from accessing your account.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Seen</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {ipQuery.isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-4 text-center text-gray-500">Loading…</td>
              </tr>
            )}
            {ipQuery.data?.items.map((ip) => (
              <tr key={ip.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-mono text-gray-900">{ip.ip_address}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[ip.status]}`}>
                    {ip.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{ip.reason || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {new Date(ip.last_seen).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  {ip.status !== 'whitelisted' && (
                    <button
                      onClick={() => handleStatusChange(ip.id, 'whitelisted')}
                      disabled={updateIP.isPending}
                      className="text-xs text-green-600 hover:underline disabled:opacity-50"
                    >
                      Whitelist
                    </button>
                  )}
                  {ip.status !== 'blacklisted' && (
                    <button
                      onClick={() => handleStatusChange(ip.id, 'blacklisted')}
                      disabled={updateIP.isPending}
                      className="text-xs text-red-600 hover:underline disabled:opacity-50"
                    >
                      Blacklist
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {ipQuery.data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-4 text-center text-gray-500">No IP records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
