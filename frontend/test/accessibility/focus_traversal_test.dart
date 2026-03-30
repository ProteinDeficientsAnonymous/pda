import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/providers/join_form_provider.dart';
import 'package:pda/screens/auth/login_screen.dart';
import 'package:pda/screens/join_screen.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class _FakeAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> login(String phoneNumber, String password) async {}

  @override
  Future<void> logout() async {}
}

class _FakeHomeNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async {
    return HomePage(
      content: 'Test content',
      joinContent: 'Test join content',
      donateUrl: '',
      updatedAt: DateTime(2026),
    );
  }
}

void main() {
  group('Focus traversal', () {
    testWidgets('join screen has FocusTraversalGroup for form', (tester) async {
      final router = GoRouter(
        routes: [
          GoRoute(path: '/', builder: (_, __) => const JoinScreen()),
          GoRoute(path: '/join/success', builder: (_, __) => const SizedBox()),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(() => _FakeAuthNotifier()),
            secureStorageProvider.overrideWithValue(
              SecureStorageService.withStorage(FakeSecureStorage()),
            ),
            homePageNotifierProvider.overrideWith(() => _FakeHomeNotifier()),
            joinFormProvider.overrideWith(
              (ref) async => const [
                JoinFormQuestion(
                  id: 'q1',
                  label: 'Why do you want to join?',
                  fieldType: 'text',
                  required: true,
                  displayOrder: 0,
                ),
              ],
            ),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      // Form should be wrapped in a FocusTraversalGroup with ordered policy
      final groups = find.byWidgetPredicate(
        (w) => w is FocusTraversalGroup && w.policy is OrderedTraversalPolicy,
      );
      expect(groups, findsOneWidget);
    });

    testWidgets('login screen has FocusTraversalGroup for form', (
      tester,
    ) async {
      final router = GoRouter(
        routes: [
          GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
          GoRoute(path: '/calendar', builder: (_, __) => const SizedBox()),
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

      final groups = find.byWidgetPredicate(
        (w) => w is FocusTraversalGroup && w.policy is OrderedTraversalPolicy,
      );
      expect(groups, findsOneWidget);
    });
  });
}
