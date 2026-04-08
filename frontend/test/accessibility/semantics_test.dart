import 'package:dio/dio.dart';
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
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class _CheckPhoneMemberApiClient extends Fake implements ApiClient {
  @override
  Future<Response> post(String path, {dynamic data}) async {
    return Response(
      requestOptions: RequestOptions(path: path),
      statusCode: 200,
      data: {'status': 'member'},
    );
  }
}

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
      contentHtml: '',
      joinContent: 'Test join content',
      joinContentHtml: '',
      donateUrl: '',
      updatedAt: DateTime(2026),
    );
  }
}

void main() {
  group('Semantics smoke tests', () {
    testWidgets('join screen exposes Submit request button in semantics tree', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();

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

      // The submit button should be findable by its text semantics
      expect(find.text('submit request'), findsOneWidget);

      // Form fields should have labels in the semantics tree
      expect(find.text('display name *'), findsOneWidget);
      expect(find.text('Why do you want to join? *'), findsOneWidget);

      handle.dispose();
    });

    testWidgets('login screen exposes Login button in semantics tree', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();

      final router = GoRouter(
        routes: [
          GoRoute(path: '/', builder: (_, __) => const LoginScreen()),
          GoRoute(path: '/calendar', builder: (_, __) => const SizedBox()),
          GoRoute(path: '/login', builder: (_, __) => const SizedBox()),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(() => _FakeAuthNotifier()),
            apiClientProvider.overrideWithValue(_CheckPhoneMemberApiClient()),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();

      // Phone step is shown initially — the continue button must be in the tree
      expect(find.text('continue'), findsOneWidget);

      // Phone number field should be in the semantics tree
      expect(find.text('Phone number'), findsOneWidget);

      handle.dispose();
    });
  });
}
