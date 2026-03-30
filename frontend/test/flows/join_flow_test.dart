import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_form_provider.dart';
import 'package:pda/providers/join_request_provider.dart';
import 'package:pda/screens/join_screen.dart';
import 'package:pda/screens/join_success_screen.dart';

const _testQuestions = [
  JoinFormQuestion(
    id: 'q1',
    label: 'Why do you want to join?',
    fieldType: 'text',
    required: true,
    displayOrder: 0,
  ),
];

Widget _buildApp() {
  final router = GoRouter(
    initialLocation: '/join',
    routes: [
      GoRoute(path: '/', builder: (_, __) => const Text('Home')),
      GoRoute(path: '/join', builder: (_, __) => const JoinScreen()),
      GoRoute(
        path: '/join/success',
        builder: (_, __) => const JoinSuccessScreen(),
      ),
    ],
  );
  return ProviderScope(
    overrides: [
      joinRequestProvider.overrideWith(() => _InstantSuccessJoinNotifier()),
      joinFormProvider.overrideWith((ref) async => _testQuestions),
      authProvider.overrideWith(() => _GuestAuthNotifier()),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('filling form and submitting navigates to /join/success', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(700, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildApp());
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Display name *'),
      'Alex R',
    );
    final phoneField = find.byType(TextFormField).at(1);
    await tester.enterText(phoneField, '2025551234');
    await tester.pump();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Why do you want to join? *'),
      'I really love animals and want to be part of this community.',
    );

    await tester.tap(find.text('submit request'));
    await tester.pumpAndSettle();

    expect(find.byType(JoinSuccessScreen), findsOneWidget);
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _InstantSuccessJoinNotifier extends JoinRequestNotifier {
  @override
  Future<void> build() async {}

  @override
  Future<void> submit({
    required String displayName,
    required String phoneNumber,
    required Map<String, String> answers,
  }) async {
    state = const AsyncData(null);
  }
}
