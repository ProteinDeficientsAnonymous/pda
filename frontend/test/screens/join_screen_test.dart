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
import 'package:pda/services/api_error.dart';

const _kTestSize = Size(700, 1200);

const _testQuestions = [
  JoinFormQuestion(
    id: 'q1',
    label: 'Why do you want to join?',
    fieldType: 'text',
    required: true,
    displayOrder: 0,
  ),
];

Widget _buildSubject({JoinRequestNotifier? notifier}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const JoinScreen()),
      GoRoute(path: '/join', builder: (_, __) => const JoinScreen()),
      GoRoute(path: '/join/success', builder: (_, __) => const _SuccessPage()),
    ],
  );
  return ProviderScope(
    overrides: [
      joinRequestProvider.overrideWith(
        () => notifier ?? _FakeJoinRequestNotifier(),
      ),
      joinFormProvider.overrideWith((ref) async => _testQuestions),
      authProvider.overrideWith(() => _GuestAuthNotifier()),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('renders form fields', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('request to join PDA'), findsOneWidget);
    expect(find.byType(TextFormField), findsWidgets);
    expect(find.text('submit request'), findsOneWidget);
  });

  testWidgets('shows validation error when required fields are empty', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    await tester.tap(find.text('submit request'));
    await tester.pump();

    expect(find.textContaining('Required'), findsWidgets);
  });

  testWidgets('shows error message on submission failure', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(notifier: _ErrorJoinNotifier()));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'display name *'),
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
    await tester.pump();

    expect(find.textContaining('Could not connect'), findsOneWidget);
  });

  testWidgets('navigates to /join/success on successful submission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    bool landedOnSuccess = false;
    final router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (_, __) => const JoinScreen()),
        GoRoute(path: '/join', builder: (_, __) => const JoinScreen()),
        GoRoute(
          path: '/join/success',
          builder: (_, __) {
            landedOnSuccess = true;
            return const _SuccessPage();
          },
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          joinRequestProvider.overrideWith(() => _FakeJoinRequestNotifier()),
          joinFormProvider.overrideWith((ref) async => _testQuestions),
          authProvider.overrideWith(() => _GuestAuthNotifier()),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'display name *'),
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

    expect(landedOnSuccess, isTrue);
  });
}

class _GuestAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

class _FakeJoinRequestNotifier extends JoinRequestNotifier {
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

class _ErrorJoinNotifier extends JoinRequestNotifier {
  @override
  Future<void> build() async {}

  @override
  Future<void> submit({
    required String displayName,
    required String phoneNumber,
    required Map<String, String> answers,
  }) async {
    state = AsyncError(const NetworkError(), StackTrace.current);
  }
}

class _SuccessPage extends StatelessWidget {
  const _SuccessPage();

  @override
  Widget build(BuildContext context) => const Text('Success!');
}
