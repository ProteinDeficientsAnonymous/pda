import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

void main() {
  testWidgets('shows bottom navigation bar with 3 destinations', (
    tester,
  ) async {
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
          path: '/profile',
          name: 'profile',
          builder: (_, __) => const SizedBox(),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _GuestAuthNotifier())],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationDestination), findsNWidgets(3));
  });

  testWidgets('navigates to calendar on icon tap', (tester) async {
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
          builder: (_, __) => const AppScaffold(child: Text('calendar screen')),
        ),
        GoRoute(
          path: '/profile',
          name: 'profile',
          builder: (_, __) => const SizedBox(),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _GuestAuthNotifier())],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.calendar_month_outlined));
    await tester.pumpAndSettle();

    expect(find.text('calendar screen'), findsOneWidget);
  });

  testWidgets('bottom nav is shown at all widths', (tester) async {
    tester.view.physicalSize = const Size(1920, 1080);
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
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _GuestAuthNotifier())],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
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
