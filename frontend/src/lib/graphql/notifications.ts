import { graphqlRequest } from '@/lib/graphql-client';
import type {
  Notification,
  NotificationList,
  NotificationPreference,
  NotificationPreferenceUpdate,
} from '@/types';

export async function notifications(params?: {
  unread_only?: boolean;
  skip?: number;
  limit?: number;
}): Promise<NotificationList> {
  const data = await graphqlRequest<
    { notifications: NotificationList },
    { input?: { unread_only?: boolean; skip?: number; limit?: number } }
  >(
    `query Notifications($input: NotificationsFilterInput) {
      notifications(input: $input) {
        items {
          id
          user_id
          title
          body
          type
          is_read
          extra_data
          created_at
        }
        total
        unread_count
      }
    }`,
    { input: params }
  );
  return data.notifications;
}

export async function notification(id: number): Promise<Notification> {
  const data = await graphqlRequest<{ notification: Notification }, { id: number }>(
    `query Notification($id: Int!) {
      notification(id: $id) {
        id
        user_id
        title
        body
        type
        is_read
        extra_data
        created_at
      }
    }`,
    { id }
  );
  return data.notification;
}

export async function markNotificationRead(id: number): Promise<Notification> {
  const data = await graphqlRequest<{ markNotificationRead: Notification }, { id: number }>(
    `mutation MarkNotificationRead($id: Int!) {
      markNotificationRead(id: $id) {
        id
        user_id
        title
        body
        type
        is_read
        extra_data
        created_at
      }
    }`,
    { id }
  );
  return data.markNotificationRead;
}

export async function markAllNotificationsRead(): Promise<boolean> {
  const data = await graphqlRequest<{ markAllNotificationsRead: boolean }>(
    `mutation MarkAllNotificationsRead {
      markAllNotificationsRead
    }`
  );
  return data.markAllNotificationsRead;
}

export async function deleteNotification(id: number): Promise<boolean> {
  const data = await graphqlRequest<{ deleteNotification: boolean }, { id: number }>(
    `mutation DeleteNotification($id: Int!) {
      deleteNotification(id: $id)
    }`,
    { id }
  );
  return data.deleteNotification;
}

export async function createNotification(input: {
  user_id: number;
  title: string;
  body: string;
  type?: string;
}): Promise<Notification> {
  const data = await graphqlRequest<{ createNotification: Notification }, { input: typeof input }>(
    `mutation CreateNotification($input: CreateNotificationInput!) {
      createNotification(input: $input) {
        id
        user_id
        title
        body
        type
        is_read
        extra_data
        created_at
      }
    }`,
    { input }
  );
  return data.createNotification;
}

export async function notificationPreferences(): Promise<NotificationPreference> {
  const data = await graphqlRequest<{ notificationPreferences: NotificationPreference }>(
    `query NotificationPreferences {
      notificationPreferences {
        id
        user_id
        websocket_enabled
        email_enabled
        push_enabled
        sms_enabled
        push_endpoint
      }
    }`
  );
  return data.notificationPreferences;
}

export async function updateNotificationPreferences(
  input: NotificationPreferenceUpdate
): Promise<NotificationPreference> {
  const data = await graphqlRequest<
    { updateNotificationPreferences: NotificationPreference },
    { input: NotificationPreferenceUpdate }
  >(
    `mutation UpdateNotificationPreferences($input: NotificationPreferenceUpdateInput!) {
      updateNotificationPreferences(input: $input) {
        id
        user_id
        websocket_enabled
        email_enabled
        push_enabled
        sms_enabled
        push_endpoint
      }
    }`,
    { input }
  );
  return data.updateNotificationPreferences;
}

export async function registerPushSubscription(input: {
  endpoint: string;
  p256dh: string;
  auth: string;
}): Promise<NotificationPreference> {
  const data = await graphqlRequest<
    { registerPushSubscription: NotificationPreference },
    { input: typeof input }
  >(
    `mutation RegisterPushSubscription($input: PushSubscriptionInput!) {
      registerPushSubscription(input: $input) {
        id
        user_id
        websocket_enabled
        email_enabled
        push_enabled
        sms_enabled
        push_endpoint
      }
    }`,
    { input }
  );
  return data.registerPushSubscription;
}

export async function removePushSubscription(): Promise<boolean> {
  const data = await graphqlRequest<{ removePushSubscription: boolean }>(
    `mutation RemovePushSubscription {
      removePushSubscription
    }`
  );
  return data.removePushSubscription;
}
