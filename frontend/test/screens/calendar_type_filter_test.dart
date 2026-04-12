import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar_screen.dart';

import '../helpers/provider_overrides.dart';

const _kTestSize = Size(700, 900);

final _official = Event(
  id: 'evt-official',
  title: 'Official Meetup',
  description: '',
  location: '',
  startDatetime: DateTime.now().add(const Duration(days: 3)),
  eventType: EventType.official,
);

final _community = Event(
  id: 'evt-community',
  title: 'Community Potluck',
  description: '',
  location: '',
  startDatetime: DateTime.now().add(const Duration(days: 5)),
  eventType: EventType.community,
);

Widget _buildSubject({List<Event> events = const []}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const CalendarScreen()),
      GoRoute(path: '/events/:id', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      eventsProvider.overrideWith((_) => Future.value(events)),
      authProvider.overrideWith(() => _GuestAuth()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('type filter visible in month view (default view)', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(events: [_official, _community]));
    await tester.pumpAndSettle();

    // Type filter should be visible in month view
    expect(
      find.descendant(
        of: find.byType(SegmentedButton<String?>),
        matching: find.text('official'),
      ),
      findsOneWidget,
    );
  });
}

class _GuestAuth extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}
