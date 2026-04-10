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

// Narrow viewport → drawer nav, avoiding AppBar overflow for authenticated users.
const _kTestSize = Size(700, 900);

final _baseEvent = Event(
  id: 'evt-1',
  title: 'Movie Night',
  description: 'Watch a great film.',
  startDatetime: DateTime(2026, 4, 1, 19),
  endDatetime: DateTime(2026, 4, 1, 21),
  location: 'The usual spot',
  createdById: 'u-creator',
  createdByName: 'Alice',
  whatsappLink: 'https://chat.whatsapp.com/abc',
  rsvpEnabled: true,
);

Widget _buildSubject(Event event, {AuthNotifier? authNotifier}) {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => Scaffold(body: EventDetailContent(event: event)),
      ),
      GoRoute(path: '/events/:id', builder: (_, __) => const SizedBox()),
      GoRoute(path: '/join', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      eventsProvider.overrideWith((_) async => [event]),
      eventDetailProvider.overrideWith((ref, id) async => event),
      authProvider.overrideWith(() => authNotifier ?? _GuestAuthNotifier()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('renders event title', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(_baseEvent));
    await tester.pumpAndSettle();

    expect(find.text('Movie Night'), findsOneWidget);
  });

  testWidgets('renders event location for authenticated member', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        _baseEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-member'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('The usual spot'), findsOneWidget);
  });

  testWidgets('location hidden for guest', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(_baseEvent));
    await tester.pumpAndSettle();

    expect(find.text('The usual spot'), findsNothing);
  });

  testWidgets('renders description', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(_baseEvent));
    await tester.pumpAndSettle();

    expect(find.textContaining('Watch a great film'), findsOneWidget);
  });

  testWidgets('WhatsApp link shown for authenticated member', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        _baseEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-member'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('WhatsApp group'), findsOneWidget);
  });

  testWidgets('WhatsApp link hidden for guest', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(_baseEvent));
    await tester.pumpAndSettle();

    expect(find.text('WhatsApp group'), findsNothing);
  });

  testWidgets('login prompt shown for guest', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(_baseEvent));
    await tester.pumpAndSettle();

    expect(find.textContaining('log in'), findsOneWidget);
  });

  testWidgets('admin actions shown for event creator', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        _baseEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-creator'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('edit'), findsOneWidget);
    expect(find.text('cancel event'), findsOneWidget);
  });

  testWidgets('RSVP hidden on past event for authenticated member', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final pastEvent = _baseEvent.copyWith(
      startDatetime: DateTime.now().subtract(const Duration(days: 7)),
      endDatetime: DateTime.now()
          .subtract(const Duration(days: 7))
          .add(const Duration(hours: 2)),
    );

    await tester.pumpWidget(
      _buildSubject(
        pastEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-member'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("i'm going"), findsNothing);
    expect(find.text('maybe'), findsNothing);
    expect(find.text("can't make it"), findsNothing);
  });

  testWidgets('invite friends hidden on past event', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final pastEvent = _baseEvent.copyWith(
      startDatetime: DateTime.now().subtract(const Duration(days: 7)),
      endDatetime: DateTime.now()
          .subtract(const Duration(days: 7))
          .add(const Duration(hours: 2)),
    );

    await tester.pumpWidget(
      _buildSubject(
        pastEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-creator'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('invite friends'), findsNothing);
  });

  testWidgets('calendar menu hidden on past event', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final pastEvent = _baseEvent.copyWith(
      startDatetime: DateTime.now().subtract(const Duration(days: 7)),
      endDatetime: DateTime.now()
          .subtract(const Duration(days: 7))
          .add(const Duration(hours: 2)),
    );

    await tester.pumpWidget(
      _buildSubject(
        pastEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-member'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byTooltip('add to calendar'), findsNothing);
  });

  testWidgets('admin actions hidden for non-creator member', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(
        _baseEvent,
        authNotifier: _MemberAuthNotifier(userId: 'u-other'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('edit'), findsNothing);
    expect(find.text('cancel event'), findsNothing);
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _MemberAuthNotifier extends AuthNotifier {
  final String userId;
  _MemberAuthNotifier({required this.userId});

  @override
  Future<User?> build() async =>
      User(id: userId, phoneNumber: '+12025551234', displayName: 'Member');

  @override
  Future<void> logout() async {}
}
