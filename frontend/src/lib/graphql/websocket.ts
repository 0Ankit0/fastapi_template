import { graphqlRequest } from '@/lib/graphql-client';
import type { WebSocketStats } from '@/types';

export async function wsStats(): Promise<WebSocketStats> {
  const data = await graphqlRequest<{ wsStats: WebSocketStats }>(
    `query WsStats {
      wsStats {
        total_connections
        active_rooms
        online_users
      }
    }`
  );
  return data.wsStats;
}

export async function wsIsOnline(userId: number): Promise<{ user_id: number; online: boolean }> {
  const data = await graphqlRequest<
    { wsIsOnline: { user_id: number; online: boolean } },
    { userId: number }
  >(
    `query WsIsOnline($userId: Int!) {
      wsIsOnline(userId: $userId) {
        user_id
        online
      }
    }`,
    { userId }
  );
  return data.wsIsOnline;
}
