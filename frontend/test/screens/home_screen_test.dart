import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/screens/home_screen.dart';

import '../helpers/provider_overrides.dart';

// Use a narrow viewport so AppScaffold shows the drawer (no wide nav bar),
// avoiding AppBar overflow from many nav items.
const _kTestSize = Size(700, 900);

Widget _buildSubject({
  HomePageNotifier? homeNotifier,
  AuthNotifier? authNotifier,
}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/join', builder: (_, __) => const SizedBox()),
      GoRoute(path: '/login', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      homePageNotifierProvider.overrideWith(
        () => homeNotifier ?? _FakeHomeNotifier(),
      ),
      authProvider.overrideWith(() => authNotifier ?? _GuestAuthNotifier()),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  setUp(() {
    // Ensure narrow viewport so AppScaffold uses drawer, not wide nav bar.
    // Wide nav bar overflows in test because there are many items.
  });

  testWidgets('shows loading indicator while fetching', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(homeNotifier: _LoadingHomeNotifier()),
    );
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('shows join CTA for unauthenticated user', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('request to join'), findsOneWidget);
  });

  testWidgets('does not show join CTA for authenticated user', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(authNotifier: _MemberAuthNotifier()));
    await tester.pumpAndSettle();

    expect(find.text('request to join'), findsNothing);
  });

  testWidgets('shows Donate button when donateUrl is set', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(homeNotifier: _HomeWithDonateNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Donate'), findsOneWidget);
  });

  testWidgets('hides Donate button when donateUrl is empty', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Donate'), findsNothing);
  });

  testWidgets('shows Edit buttons for user with edit_homepage permission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _HomepageEditorAuthNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsWidgets);
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _MemberAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async =>
      const User(id: 'u1', phoneNumber: '+12025551234', displayName: 'Alice');

  @override
  Future<void> logout() async {}
}

class _HomepageEditorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u2',
    phoneNumber: '+12025559999',
    displayName: 'Homepage Editor',
    roles: [
      Role(id: 'r1', name: 'homepage_editor', permissions: ['edit_homepage']),
    ],
  );

  @override
  Future<void> logout() async {}
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

class _HomeWithDonateNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async => HomePage(
    content: '',
    joinContent: '',
    donateUrl: 'https://example.com/donate',
    updatedAt: DateTime(2026),
  );
}

class _LoadingHomeNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async {
    // Never complete — keeps the provider in loading state without a pending timer.
    await Completer<void>().future;
    return HomePage(
      content: '',
      joinContent: '',
      donateUrl: '',
      updatedAt: DateTime(2026),
    );
  }
}
