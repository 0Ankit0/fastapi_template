import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/providers/dio_provider.dart';
import '../../data/models/notification_list.dart';
import '../../data/models/notification_preference.dart';
import '../../data/repositories/notification_repository.dart';

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return NotificationRepository(ref.watch(dioClientProvider));
});

final unreadCountProvider = FutureProvider<int>((ref) async {
  final repo = ref.watch(notificationRepositoryProvider);
  final result = await repo.getNotifications(unreadOnly: true, limit: 1);
  return result.unreadCount;
});

final notificationsProvider =
    FutureProvider.family<NotificationList, ({bool unreadOnly})>(
  (ref, params) => ref
      .watch(notificationRepositoryProvider)
      .getNotifications(unreadOnly: params.unreadOnly),
);

final notificationPrefsProvider = FutureProvider<NotificationPreference>((ref) {
  return ref.watch(notificationRepositoryProvider).getPreferences();
});
