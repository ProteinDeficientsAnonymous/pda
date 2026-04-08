import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/notification.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/notification_sse.dart';
import 'package:pda/utils/tab_visibility.dart';

final _log = Logger('NotificationProvider');

/// Fetches unread notification count. SSE provides real-time pushes;
/// polling acts as a fallback (60s normally, 5min when SSE is connected).
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

  // Merge SSE events and timer ticks into a single trigger stream.
  final trigger = StreamController<void>();
  NotificationSseClient? sseClient;
  Timer? pollTimer;

  void schedulePoll() {
    final interval = (sseClient?.isConnected ?? false)
        ? const Duration(minutes: 5)
        : const Duration(seconds: 60);
    pollTimer = Timer(interval, () {
      if (!trigger.isClosed && !isTabHidden()) trigger.add(null);
      schedulePoll();
    });
  }

  // Attempt to connect SSE with the stored access token.
  final storage = ref.read(secureStorageProvider);
  final token = await storage.getAccessToken();
  if (token != null) {
    sseClient = NotificationSseClient(
      token: token,
      onNotification: () {
        if (!trigger.isClosed) trigger.add(null);
      },
    );
  }

  ref.onDispose(() {
    sseClient?.close();
    pollTimer?.cancel();
    trigger.close();
  });

  schedulePoll();

  // Initial fetch before entering the event loop.
  yield await fetchCount();

  await for (final _ in trigger.stream) {
    yield await fetchCount();
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
