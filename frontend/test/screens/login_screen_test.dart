import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/auth/login_screen.dart';
import 'package:pda/services/api_error.dart';

Widget _buildSubject({AuthNotifier? notifier}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/calendar', builder: (_, __) => const SizedBox()),
      GoRoute(path: '/login', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => notifier ?? _FakeAuthNotifier()),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

/// Fills the phone and password fields so the form passes validation.
Future<void> _fillForm(WidgetTester tester) async {
  // Phone field is the first TextFormField (PhoneFormField widget)
  await tester.enterText(find.byType(TextFormField).first, '2025551234');
  // Password field is the last TextFormField
  await tester.enterText(find.byType(TextFormField).last, 'password123');
  await tester.pump();
}

void main() {
  testWidgets('login form has autofill hints for password manager support', (
    tester,
  ) async {
    await tester.pumpWidget(_buildSubject());
    await tester.pump();

    final textFields = find.byType(TextField);
    final phoneField = tester.widget<TextField>(textFields.first);
    final passwordField = tester.widget<TextField>(textFields.last);
    expect(phoneField.autofillHints, contains(AutofillHints.telephoneNumber));
    expect(passwordField.autofillHints, contains(AutofillHints.password));
    expect(find.byType(AutofillGroup), findsOneWidget);
  });

  testWidgets('password visibility toggle has accessible tooltip', (
    tester,
  ) async {
    await tester.pumpWidget(_buildSubject());
    await tester.pump();

    final iconButtons = find.byType(IconButton);
    final visibilityToggle = tester.widget<IconButton>(iconButtons.last);
    expect(visibilityToggle.tooltip, isNotNull);
    expect(visibilityToggle.tooltip, contains('password'));
  });

  testWidgets('phone field shows error when empty', (tester) async {
    await tester.pumpWidget(_buildSubject());
    await tester.pump();

    await tester.tap(find.byType(FilledButton));
    await tester.pump();

    expect(find.text('Required'), findsWidgets);
  });

  testWidgets('successful login navigates to /calendar', (tester) async {
    String? landedAt;
    final router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
        GoRoute(
          path: '/calendar',
          builder: (_, __) {
            landedAt = '/calendar';
            return const SizedBox();
          },
        ),
        GoRoute(path: '/login', builder: (_, __) => const SizedBox()),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authProvider.overrideWith(() => _FakeAuthNotifier())],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump();

    await _fillForm(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    expect(landedAt, '/calendar');
  });

  testWidgets('failed login shows error message', (tester) async {
    await tester.pumpWidget(_buildSubject(notifier: _ErrorAuthNotifier()));
    await tester.pump();

    await _fillForm(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pump();

    expect(find.textContaining('Invalid email or password'), findsOneWidget);
  });

  testWidgets('button is disabled while loading', (tester) async {
    await tester.pumpWidget(_buildSubject(notifier: _LoadingAuthNotifier()));
    await tester.pump();

    await _fillForm(tester);
    await tester.tap(find.byType(FilledButton));
    // One pump to trigger loading state
    await tester.pump();

    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull);
  });
}

class _FakeAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> login(String phoneNumber, String password) async {
    // Simulate success — no state change needed; the screen just navigates
    // because state.hasError is false after login.
  }

  @override
  Future<void> logout() async {}
}

class _ErrorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> login(String phoneNumber, String password) async {
    state = AsyncError(const InvalidCredentials(), StackTrace.current);
  }

  @override
  Future<void> logout() async {}
}

class _LoadingAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> login(String phoneNumber, String password) async {
    state = const AsyncLoading();
    // Never completes — no pending timer.
    await Completer<void>().future;
  }

  @override
  Future<void> logout() async {}
}
