import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

void main() {
  group('narrow layout (drawer)', () {
    setUp(() {});

    testWidgets('drawer contains login item for guest', (tester) async {
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            name: 'home',
            builder: (_, __) => const AppScaffold(child: Placeholder()),
          ),
          GoRoute(
            path: '/login',
            name: 'login',
            builder: (_, __) => const SizedBox(),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [authProvider.overrideWith(() => _GuestAuthNotifier())],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      expect(find.text('log in'), findsOneWidget);
      expect(find.text('log out'), findsNothing);
    });

    testWidgets('drawer contains logout item for authenticated user', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            name: 'home',
            builder: (_, __) => const AppScaffold(child: Placeholder()),
          ),
          GoRoute(
            path: '/calendar',
            name: 'calendar',
            builder: (_, __) => const SizedBox(),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [authProvider.overrideWith(() => _MemberAuthNotifier())],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      expect(find.text('log out'), findsOneWidget);
      expect(find.text('log in'), findsNothing);
    });
  });

  group('wide layout (app bar nav)', () {
    testWidgets('shows Member login button for guest', (tester) async {
      tester.view.physicalSize = const Size(1200, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            name: 'home',
            builder: (_, __) => const AppScaffold(child: Placeholder()),
          ),
          GoRoute(
            path: '/login',
            name: 'login',
            builder: (_, __) => const SizedBox(),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [authProvider.overrideWith(() => _GuestAuthNotifier())],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('log in'), findsOneWidget);
      expect(find.text('log out'), findsNothing);
    });

    testWidgets('shows Logout button for authenticated user', (tester) async {
      tester.view.physicalSize = const Size(1200, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            name: 'home',
            builder: (_, __) => const AppScaffold(child: Placeholder()),
          ),
          GoRoute(
            path: '/calendar',
            name: 'calendar',
            builder: (_, __) => const SizedBox(),
          ),
          GoRoute(
            path: '/events/mine',
            name: 'my-events',
            builder: (_, __) => const SizedBox(),
          ),
          GoRoute(
            path: '/donate',
            name: 'donate',
            builder: (_, __) => const SizedBox(),
          ),
          GoRoute(
            path: '/volunteer',
            name: 'volunteer',
            builder: (_, __) => const SizedBox(),
          ),
          GoRoute(
            path: '/guidelines',
            name: 'guidelines',
            builder: (_, __) => const SizedBox(),
          ),
          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (_, __) => const SizedBox(),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [authProvider.overrideWith(() => _MemberAuthNotifier())],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('log out'), findsOneWidget);
      expect(find.text('log in'), findsNothing);
    });
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}

class _MemberAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async =>
      const User(id: 'u1', phoneNumber: '+12025551234', displayName: 'Alice');

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}
