import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/router/app_router.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/providers/home_provider.dart';

// Integration tests that verify auth-driven routing using the real routerProvider.

Widget _buildApp(AuthNotifier authNotifier) {
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => authNotifier),
      eventsProvider.overrideWith((_) async => const []),
      homePageNotifierProvider.overrideWith(() => _FakeHomeNotifier()),
    ],
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(routerConfig: router);
      },
    ),
  );
}

void main() {
  testWidgets('unauthenticated user can access /calendar', (tester) async {
    final notifier = _GuestAuthNotifier();

    await tester.pumpWidget(_buildApp(notifier));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(Consumer)),
    );
    final goRouter = container.read(routerProvider);
    goRouter.go('/calendar');
    await tester.pumpAndSettle();

    expect(goRouter.routerDelegate.currentConfiguration.uri.path, '/calendar');
  });

  testWidgets('authenticated user can access /calendar', (tester) async {
    // Use a viewport < 720px wide (drawer nav) but wide enough for CalendarToolbar.
    tester.view.physicalSize = const Size(700, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final notifier = _MemberAuthNotifier();

    await tester.pumpWidget(_buildApp(notifier));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(Consumer)),
    );
    final goRouter = container.read(routerProvider);
    goRouter.go('/calendar');
    await tester.pumpAndSettle();

    // Stays on /calendar — no redirect.
    expect(goRouter.routerDelegate.currentConfiguration.uri.path, '/calendar');
  });

  test('logout clears auth state to null', () async {
    final container = ProviderContainer(
      overrides: [authProvider.overrideWith(() => _MemberAuthNotifier())],
    );
    addTearDown(container.dispose);

    await container.read(authProvider.future);
    expect(container.read(authProvider).value?.displayName, 'Alice');

    await container.read(authProvider.notifier).logout();

    expect(container.read(authProvider).value, isNull);
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

class _FakeHomeNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async => HomePage(
    content: '',
    joinContent: '',
    donateUrl: '',
    updatedAt: DateTime(2026),
  );
}
