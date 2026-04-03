import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar_screen.dart';

import '../helpers/provider_overrides.dart';

// Use a narrow viewport so AppScaffold uses drawer nav (avoids AppBar overflow
// when authenticated user has many nav items).
const _kTestSize = Size(700, 900);

Widget _buildSubject({
  Future<List<Event>> Function()? eventsBuilder,
  AuthNotifier? authNotifier,
}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const CalendarScreen()),
      GoRoute(path: '/events/:id', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      eventsProvider.overrideWith(
        (_) => eventsBuilder != null ? eventsBuilder() : Future.value([]),
      ),
      authProvider.overrideWith(() => authNotifier ?? _GuestAuthNotifier()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('renders month/week/day/list view toggle', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('month'), findsOneWidget);
    expect(find.text('week'), findsOneWidget);
    expect(find.text('day'), findsOneWidget);
    expect(find.text('list'), findsOneWidget);
  });

  testWidgets('renders Today button', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    // Toolbar has a visible 'today' button + an invisible spacer with same text
    expect(find.text('today'), findsAtLeastNWidgets(1));
  });

  testWidgets('shows loading indicator while events are loading', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        // Completer that never resolves → keeps provider in loading state
        // without leaving a pending fake timer.
        eventsBuilder: () => Completer<List<Event>>().future,
      ),
    );
    // Single pump — don't settle; the provider is still loading.
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('can switch from month to week view', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    await tester.tap(find.text('week'));
    await tester.pumpAndSettle();

    expect(find.text('week'), findsOneWidget);
  });

  testWidgets('FAB shown for user with create_events permission', (
    tester,
  ) async {
    // Use narrow viewport to avoid wide nav bar overflow.
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        eventsBuilder: () async => [],
        authNotifier: _EventCreatorAuthNotifier(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('add event'), findsOneWidget);
  });

  testWidgets('FAB shown for guest', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    // FAB is always visible — tapping it opens the guest login dialog.
    expect(find.text('add event'), findsOneWidget);
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _EventCreatorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u1',
    phoneNumber: '+12025551234',
    displayName: 'Alice',
    roles: [
      Role(id: 'r1', name: 'organizer', permissions: ['create_events']),
    ],
  );

  @override
  Future<void> logout() async {}
}
