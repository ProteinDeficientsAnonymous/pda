import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/editable_page_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/router/app_router.dart';

// Tests that verify which routes are accessible without authentication.

final _fakeEvent = Event(
  id: 'event-abc',
  title: 'Test Event',
  description: 'A test event',
  startDatetime: DateTime(2026, 5, 1, 18),
  endDatetime: DateTime(2026, 5, 1, 21),
  location: '123 Main St',
);

Widget _buildApp(AuthNotifier authNotifier) {
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => authNotifier),
      eventsProvider.overrideWith((_) async => <Event>[_fakeEvent]),
      eventDetailProvider.overrideWith(
        (ref, id) async =>
            id == _fakeEvent.id ? _fakeEvent : (throw Exception('not found')),
      ),
      homePageNotifierProvider.overrideWith(() => _FakeHomeNotifier()),
      editablePageProvider.overrideWith2(
        (arg) => _FakeEditablePageNotifier(arg),
      ),
    ],
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(routerConfig: router);
      },
    ),
  );
}

GoRouter _routerFrom(WidgetTester tester) {
  final container = ProviderScope.containerOf(
    tester.element(find.byType(Consumer)),
  );
  return container.read(routerProvider);
}

String _currentPath(GoRouter router) =>
    router.routerDelegate.currentConfiguration.uri.path;

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async => state = const AsyncData(null);
}

class _FakeHomeNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async => HomePage(
    content: '',
    joinContent: '',
    donateUrl: '',
    updatedAt: DateTime(2026),
  );
}

class _FakeEditablePageNotifier extends EditablePageNotifier {
  // ignore: use_super_parameters
  _FakeEditablePageNotifier(String slug) : _fakeSlug = slug, super(slug);
  final String _fakeSlug;

  @override
  Future<EditablePage> build() async => EditablePage(
    slug: _fakeSlug,
    content: '',
    visibility: 'public',
    updatedAt: DateTime(2026),
  );
}

void main() {
  group('Unauthenticated access', () {
    late _GuestAuthNotifier guest;

    setUp(() => guest = _GuestAuthNotifier());

    Future<GoRouter> navigate(WidgetTester tester, String path) async {
      await tester.pumpWidget(_buildApp(guest));
      await tester.pumpAndSettle();
      final router = _routerFrom(tester);
      router.go(path);
      await tester.pumpAndSettle();
      return router;
    }

    void useDesktopViewport(WidgetTester tester) {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
    }

    testWidgets('can access home page (/)', (tester) async {
      useDesktopViewport(tester);
      final router = await navigate(tester, '/');
      expect(_currentPath(router), '/');
    });

    testWidgets('can access login page (/login)', (tester) async {
      final router = await navigate(tester, '/login');
      expect(_currentPath(router), '/login');
    });

    testWidgets('can access donate page (/donate)', (tester) async {
      useDesktopViewport(tester);
      final router = await navigate(tester, '/donate');
      expect(_currentPath(router), '/donate');
    });

    testWidgets('can access event detail page (/events/:id)', (tester) async {
      useDesktopViewport(tester);
      final router = await navigate(tester, '/events/event-abc');
      expect(_currentPath(router), '/events/event-abc');
    });

    testWidgets(
      'event detail page shows "members only" gate when unauthenticated',
      (tester) async {
        useDesktopViewport(tester);
        await navigate(tester, '/events/event-abc');
        expect(find.textContaining('members only'), findsOneWidget);
      },
    );

    testWidgets('can access calendar page (/calendar)', (tester) async {
      final router = await navigate(tester, '/calendar');
      expect(_currentPath(router), '/calendar');
    });

    testWidgets('is redirected to /login when visiting /guidelines', (
      tester,
    ) async {
      final router = await navigate(tester, '/guidelines');
      expect(_currentPath(router), '/login');
    });

    testWidgets('is redirected to /login when visiting /members', (
      tester,
    ) async {
      final router = await navigate(tester, '/members');
      expect(_currentPath(router), '/login');
    });

    testWidgets('is redirected to /login when visiting /settings', (
      tester,
    ) async {
      final router = await navigate(tester, '/settings');
      expect(_currentPath(router), '/login');
    });
  });

  group('Case-insensitive URL matching', () {
    late _GuestAuthNotifier guest;

    setUp(() => guest = _GuestAuthNotifier());

    Future<GoRouter> navigate(WidgetTester tester, String path) async {
      await tester.pumpWidget(_buildApp(guest));
      await tester.pumpAndSettle();
      final router = _routerFrom(tester);
      router.go(path);
      await tester.pumpAndSettle();
      return router;
    }

    testWidgets('mixed-case /Calendar is routed (not a 404)', (tester) async {
      final router = await navigate(tester, '/Calendar');
      // caseSensitive: false matches the route; path casing is preserved as-typed
      expect(_currentPath(router), '/Calendar');
    });

    testWidgets('all-caps /LOGIN is routed (not a 404)', (tester) async {
      final router = await navigate(tester, '/LOGIN');
      expect(_currentPath(router), '/LOGIN');
    });

    testWidgets(
      'mixed-case protected /Guidelines redirects unauthenticated to /login',
      (tester) async {
        final router = await navigate(tester, '/Guidelines');
        // redirect logic normalizes to lowercase before checking protected routes
        expect(_currentPath(router), '/login');
      },
    );
  });
}
