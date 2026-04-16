import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

import '../helpers/provider_overrides.dart';

const _kTestSize = Size(700, 900);

/// Upcoming event with attendees — shows cancel flow.
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
  attendingCount: 1, // has attendees → shows cancel (not delete)
);

/// Upcoming event with no attendees — shows delete directly.
final _testEventNoAttendees = Event(
  id: 'evt-2',
  title: 'Quiet Gathering',
  description: 'Just us.',
  startDatetime: DateTime(2026, 4, 1, 19),
  location: '',
  createdById: 'u-host',
  createdByName: 'Alice',
);

/// Past event — shows delete (no cancel).
final _testPastEvent = Event(
  id: 'evt-3',
  title: 'Old Event',
  description: 'Already happened.',
  startDatetime: DateTime(2020, 1, 1, 19),
  location: '',
  createdById: 'u-host',
  createdByName: 'Alice',
  isPast: true,
);

Widget _buildSubject({AuthNotifier? authNotifier, Event? event}) {
  final e = event ?? _testEvent;
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => Scaffold(body: EventDetailContent(event: e)),
      ),
      GoRoute(path: '/events/:id', builder: (_, __) => const SizedBox()),
      GoRoute(path: '/join', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      eventsProvider.overrideWith((_) async => [e]),
      eventDetailProvider.overrideWith((ref, id) async => e),
      authProvider.overrideWith(() => authNotifier ?? _GuestAuthNotifier()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  group('event detail admin actions visibility', () {
    testWidgets(
      'co-host sees edit and cancel buttons for upcoming event with attendees',
      (tester) async {
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
        expect(find.text('delete'), findsNothing);
      },
    );

    testWidgets(
      'creator sees edit and delete for upcoming event with no attendees',
      (tester) async {
        tester.view.physicalSize = _kTestSize;
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await tester.pumpWidget(
          _buildSubject(
            event: _testEventNoAttendees,
            authNotifier: _UserAuthNotifier(userId: 'u-host'),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('edit'), findsOneWidget);
        expect(find.text('delete'), findsOneWidget);
        expect(find.text('cancel event'), findsNothing);
      },
    );

    testWidgets('creator sees delete (no edit) for past event', (tester) async {
      tester.view.physicalSize = _kTestSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        _buildSubject(
          event: _testPastEvent,
          authNotifier: _UserAuthNotifier(userId: 'u-host'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('delete'), findsOneWidget);
      expect(find.text('edit'), findsNothing);
      expect(find.text('cancel event'), findsNothing);
    });

    testWidgets('regular member does NOT see edit or cancel', (tester) async {
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
      expect(find.text('delete'), findsNothing);
    });

    testWidgets('unauthenticated user does NOT see admin actions', (
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
      expect(find.text('delete'), findsNothing);
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

  _UserAuthNotifier({required this.userId});

  @override
  Future<User?> build() async =>
      User(id: userId, phoneNumber: '+12025551234', displayName: 'Test User');

  @override
  Future<void> logout() async {}
}
