import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/auth/login_screen.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/api_error.dart';

import '../helpers/provider_overrides.dart';

// A fake ApiClient that responds to check-phone with {"status": "member"}.
class _CheckPhoneMemberApiClient extends Fake implements ApiClient {
  @override
  Future<Response> post(String path, {dynamic data}) async {
    if (path == '/api/community/check-phone/') {
      return Response(
        requestOptions: RequestOptions(path: path),
        statusCode: 200,
        data: {'status': 'member'},
      );
    }
    throw UnimplementedError('Unexpected POST to $path');
  }
}

const _fakeUser = User(id: 'u1', phoneNumber: '+12025551234');

Widget _buildSubject({AuthNotifier? notifier, ApiClient? apiClient}) {
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
      apiClientProvider.overrideWithValue(
        apiClient ?? _CheckPhoneMemberApiClient(),
      ),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

/// Step 1: enter phone and advance to the password step.
Future<void> _advanceToPasswordStep(WidgetTester tester) async {
  await tester.enterText(find.byType(TextFormField).first, '2025551234');
  await tester.pump();
  await tester.tap(find.byType(FilledButton));
  await tester.pumpAndSettle();
}

/// Full two-step form fill: phone step → password step → enter password.
Future<void> _fillForm(WidgetTester tester) async {
  await _advanceToPasswordStep(tester);
  await tester.enterText(find.byType(TextFormField).first, 'password123');
  await tester.pump();
}

void main() {
  testWidgets('login form has autofill hints for password manager support', (
    tester,
  ) async {
    await tester.pumpWidget(_buildSubject());
    await tester.pump();

    await _advanceToPasswordStep(tester);

    final textFields = find.byType(TextField);
    final passwordField = tester.widget<TextField>(textFields.first);
    expect(passwordField.autofillHints, contains(AutofillHints.password));
    expect(find.byType(AutofillGroup), findsOneWidget);
  });

  testWidgets('password visibility toggle has accessible tooltip', (
    tester,
  ) async {
    await tester.pumpWidget(_buildSubject());
    await tester.pump();

    await _advanceToPasswordStep(tester);

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
        overrides: [
          authProvider.overrideWith(() => _FakeAuthNotifier()),
          apiClientProvider.overrideWithValue(_CheckPhoneMemberApiClient()),
          silentNotificationsOverride,
        ],
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
    // One pump to trigger loading state — notifier never completes
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
    state = const AsyncData(_fakeUser);
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
