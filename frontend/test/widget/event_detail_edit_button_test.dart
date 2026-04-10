import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

import '../helpers/provider_overrides.dart';

const _kTestSize = Size(700, 900);

final _testEvent = Event(
  id: 'evt-1',
  title: 'Movie Night',
  description: 'Watch a great film.',
  startDatetime: DateTime(2026, 4, 1, 19),
  location: '',
  createdById: 'u-host',
  createdByName: 'Alice',
  coHostIds: ['u-cohost'],
  coHostNames: ['Bob'],
);

Widget _buildSubject({AuthNotifier? authNotifier}) {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) =>
            Scaffold(body: EventDetailContent(event: _testEvent)),
      ),
      GoRoute(path: '/events/:id', builder: (_, __) => const SizedBox()),
      GoRoute(path: '/join', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      eventsProvider.overrideWith((_) async => [_testEvent]),
      eventDetailProvider.overrideWith((ref, id) async => _testEvent),
      authProvider.overrideWith(() => authNotifier ?? _GuestAuthNotifier()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  group('event detail admin actions visibility', () {
    testWidgets('co-host sees edit and cancel buttons', (tester) async {
      tester.view.physicalSize = _kTestSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        _buildSubject(authNotifier: _UserAuthNotifier(userId: 'u-cohost')),
      );
      await tester.pumpAndSettle();

      expect(find.text('edit'), findsOneWidget);
      expect(find.text('cancel event'), findsOneWidget);
    });

    testWidgets('regular member does NOT see edit or delete', (tester) async {
      tester.view.physicalSize = _kTestSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        _buildSubject(authNotifier: _UserAuthNotifier(userId: 'u-nobody')),
      );
      await tester.pumpAndSettle();

      expect(find.text('edit'), findsNothing);
      expect(find.text('cancel event'), findsNothing);
    });

    testWidgets('unauthenticated user does NOT see edit or delete', (
      tester,
    ) async {
      tester.view.physicalSize = _kTestSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('edit'), findsNothing);
      expect(find.text('cancel event'), findsNothing);
    });
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _UserAuthNotifier extends AuthNotifier {
  final String userId;
  final List<String> permissions;

  _UserAuthNotifier({required this.userId, this.permissions = const []});

  @override
  Future<User?> build() async => User(
    id: userId,
    phoneNumber: '+12025551234',
    displayName: 'Test User',
    roles: [
      if (permissions.isNotEmpty)
        Role(id: 'r-1', name: 'custom', permissions: permissions),
    ],
  );

  @override
  Future<void> logout() async {}
}
