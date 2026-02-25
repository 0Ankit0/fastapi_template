// IP Access Control module types

export type IpAccessStatus = 'whitelisted' | 'blacklisted' | 'pending';

export interface IPAccessControl {
  id: string;
  user_id: string;
  ip_address: string;
  status: IpAccessStatus;
  reason: string;
  last_seen: string;
  created_at: string;
}

export interface IPAccessControlUpdate {
  status: IpAccessStatus;
  reason?: string;
}
