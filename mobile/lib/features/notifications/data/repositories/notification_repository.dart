import '../../../../core/error/error_handler.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/network/graphql_client.dart';
import '../models/notification_list.dart';
import '../models/notification_preference.dart';

class NotificationRepository {
  final GraphQLClient _graphql;

  NotificationRepository(DioClient dioClient) : _graphql = GraphQLClient(dioClient.dio);

  Future<NotificationList> getNotifications({
    bool unreadOnly = false,
    int skip = 0,
    int limit = 20,
  }) async {
    try {
      final data = await _graphql.query(
        r'''
        query Notifications($input: NotificationsFilterInput) {
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
        }
        ''',
        variables: {
          'input': {'unread_only': unreadOnly, 'skip': skip, 'limit': limit}
        },
      );
      return NotificationList.fromJson(data['notifications'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> markRead(String id) async {
    try {
      await _graphql.mutation(
        r'''
        mutation MarkNotificationRead($id: Int!) {
          markNotificationRead(id: $id) { id }
        }
        ''',
        variables: {'id': int.tryParse(id)},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> markAllRead() async {
    try {
      await _graphql.mutation(r'''mutation MarkAllRead { markAllNotificationsRead }''');
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> deleteNotification(String id) async {
    try {
      await _graphql.mutation(
        r'''
        mutation DeleteNotification($id: Int!) {
          deleteNotification(id: $id)
        }
        ''',
        variables: {'id': int.tryParse(id)},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<NotificationPreference> getPreferences() async {
    try {
      final data = await _graphql.query(r'''
        query NotificationPreferences {
          notificationPreferences {
            id
            user_id
            email_enabled
            push_enabled
            sms_enabled
            websocket_enabled
            push_endpoint
          }
        }
      ''');
      return NotificationPreference.fromJson(
        data['notificationPreferences'] as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<NotificationPreference> updatePreferences(Map<String, bool> updates) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation UpdateNotificationPreferences($input: NotificationPreferenceUpdateInput!) {
          updateNotificationPreferences(input: $input) {
            id
            user_id
            email_enabled
            push_enabled
            sms_enabled
            websocket_enabled
            push_endpoint
          }
        }
        ''',
        variables: {'input': updates},
      );
      return NotificationPreference.fromJson(
        data['updateNotificationPreferences'] as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
