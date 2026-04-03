import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/notification.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/tab_visibility.dart';

final _log = Logger('NotificationProvider');

/// Polls /api/notifications/unread-count/ every 60s.
/// Yields 0 when unauthenticated. Skips fetching when tab is hidden.
final unreadCountProvider = StreamProvider<int>((ref) async* {
  final user = ref.watch(authProvider).value;
  if (user == null) {
    yield 0;
    return;
  }

  final api = ref.watch(apiClientProvider);

  Future<int> fetchCount() async {
    try {
      final response = await api.get('/api/notifications/unread-count/');
      final data = response.data as Map<String, dynamic>;
      return data['count'] as int;
    } catch (e) {
      _log.warning('Failed to fetch unread count', e);
      return 0;
    }
  }

  // Initial fetch
  yield await fetchCount();

  // Poll every 60 seconds; skip tick if tab is hidden
  while (true) {
    await Future<void>.delayed(const Duration(seconds: 60));
    if (!isTabHidden()) {
      yield await fetchCount();
    }
  }
});

/// Fetches the full notification list on demand.
final notificationsProvider = FutureProvider<List<AppNotification>>((
  ref,
) async {
  final user = ref.watch(authProvider).value;
  if (user == null) return [];

  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/notifications/');
    final list = response.data as List<dynamic>;
    return list
        .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
        .toList();
  } catch (e) {
    _log.warning('Failed to load notifications', e);
    rethrow;
  }
});

Future<void> markNotificationRead(WidgetRef ref, String notificationId) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.post('/api/notifications/$notificationId/read/');
    ref.invalidate(unreadCountProvider);
    ref.invalidate(notificationsProvider);
  } catch (e) {
    _log.warning('Failed to mark notification $notificationId as read', e);
  }
}

Future<void> markAllNotificationsRead(WidgetRef ref) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.post('/api/notifications/read-all/');
    ref.invalidate(unreadCountProvider);
    ref.invalidate(notificationsProvider);
  } catch (e) {
    _log.warning('Failed to mark all notifications as read', e);
  }
}
