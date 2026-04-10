import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/models/notification.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/notification_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/widgets/notification_bell.dart';

class _MockApiClient extends Mock implements ApiClient {}

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

final _magicLinkNotification = AppNotification(
  id: 'notif-2',
  notificationType: 'magic_link_request',
  relatedUserId: 'user-99',
  message: 'Alex requested a new login link',
  isRead: false,
  createdAt: DateTime(2026, 4, 1),
);

Widget _buildBell({
  int unreadCount = 0,
  List<AppNotification> notifications = const [],
  ApiClient? apiClient,
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
      GoRoute(
        path: '/members/:id',
        name: 'member-profile',
        builder: (_, __) => const Scaffold(body: Text('member profile')),
      ),
      GoRoute(
        path: '/members',
        name: 'members',
        builder: (_, __) => const Scaffold(body: Text('members')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => _AuthedNotifier()),
      unreadCountProvider.overrideWith((ref) => Stream.value(unreadCount)),
      notificationsProvider.overrideWith((ref) async => notifications),
      if (apiClient != null) apiClientProvider.overrideWithValue(apiClient),
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

  testWidgets(
    'tapping magic link request notification navigates to member profile',
    (tester) async {
      final mockApi = _MockApiClient();
      when(() => mockApi.post(any())).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(),
          statusCode: 200,
          data: {'detail': 'ok'},
        ),
      );

      await tester.pumpWidget(
        _buildBell(notifications: [_magicLinkNotification], apiClient: mockApi),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.notifications_outlined));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Alex requested a new login link'));
      await tester.pumpAndSettle();

      expect(find.text('member profile'), findsOneWidget);
    },
  );
}
