import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/notification.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/notification_provider.dart';
import 'package:pda/widgets/notification_bell.dart';

class _AuthedNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'user-1',
    displayName: 'Test User',
    phoneNumber: '+1234567890',
  );

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}

final _testNotification = AppNotification(
  id: 'notif-1',
  notificationType: 'event_invite',
  eventId: 'evt-1',
  message: 'Alice invited you to Party',
  isRead: false,
  createdAt: DateTime(2026, 4, 1),
);

Widget _buildBell({
  int unreadCount = 0,
  List<AppNotification> notifications = const [],
}) {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        name: 'home',
        builder: (_, __) =>
            const Scaffold(body: Center(child: NotificationBell())),
      ),
      GoRoute(
        path: '/events/:id',
        name: 'event-detail',
        builder: (_, __) => const Scaffold(body: Text('event detail')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => _AuthedNotifier()),
      unreadCountProvider.overrideWith((ref) => Stream.value(unreadCount)),
      notificationsProvider.overrideWith((ref) async => notifications),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('shows badge when unread count > 0', (tester) async {
    await tester.pumpWidget(_buildBell(unreadCount: 3));
    await tester.pumpAndSettle();

    expect(find.byType(Badge), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
  });

  testWidgets('badge is not visible when unread count is 0', (tester) async {
    await tester.pumpWidget(_buildBell(unreadCount: 0));
    await tester.pumpAndSettle();

    // Badge widget exists but isLabelVisible=false means label text is hidden
    expect(find.text('0'), findsNothing);
  });

  testWidgets('tapping bell opens notifications bottom sheet', (tester) async {
    await tester.pumpWidget(_buildBell(notifications: [_testNotification]));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.notifications_outlined));
    await tester.pumpAndSettle();

    expect(find.text('notifications'), findsOneWidget);
    expect(find.text('Alice invited you to Party'), findsOneWidget);
  });

  testWidgets('shows empty state when no notifications', (tester) async {
    await tester.pumpWidget(_buildBell());
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.notifications_outlined));
    await tester.pumpAndSettle();

    expect(find.text('no notifications yet 🌿'), findsOneWidget);
  });

  testWidgets('shows mark all as read button in sheet', (tester) async {
    await tester.pumpWidget(_buildBell(notifications: [_testNotification]));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.notifications_outlined));
    await tester.pumpAndSettle();

    expect(find.text('mark all as read'), findsOneWidget);
  });
}
