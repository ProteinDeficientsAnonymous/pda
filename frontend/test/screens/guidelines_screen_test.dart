import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/guidelines_provider.dart';
import 'package:pda/screens/guidelines_screen.dart';

const _kTestSize = Size(700, 900);

Widget _buildSubject({
  GuidelinesNotifier? guidelinesNotifier,
  AuthNotifier? authNotifier,
}) {
  final router = GoRouter(
    routes: [GoRoute(path: '/', builder: (_, __) => const GuidelinesScreen())],
  );
  return ProviderScope(
    overrides: [
      guidelinesNotifierProvider.overrideWith(
        () => guidelinesNotifier ?? _FakeGuidelinesNotifier(),
      ),
      authProvider.overrideWith(() => authNotifier ?? _MemberAuthNotifier()),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('shows loading indicator while fetching', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(guidelinesNotifier: _LoadingGuidelinesNotifier()),
    );
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('hides Edit button for member without manage_guidelines', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsNothing);
  });

  testWidgets('shows Edit button for user with manage_guidelines permission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _GuidelinesEditorAuthNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsOneWidget);
  });
}

class _MemberAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async =>
      const User(id: 'u1', phoneNumber: '+12025551234', displayName: 'Alice');

  @override
  Future<void> logout() async {}
}

class _GuidelinesEditorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u2',
    phoneNumber: '+12025559001',
    displayName: 'Guidelines Editor',
    roles: [
      Role(
        id: 'r1',
        name: 'guidelines_editor',
        permissions: ['edit_guidelines'],
      ),
    ],
  );

  @override
  Future<void> logout() async {}
}

class _FakeGuidelinesNotifier extends GuidelinesNotifier {
  @override
  Future<Guidelines> build() async =>
      Guidelines(content: '', updatedAt: DateTime(2026));
}

class _LoadingGuidelinesNotifier extends GuidelinesNotifier {
  @override
  Future<Guidelines> build() async {
    await Completer<void>().future;
    return Guidelines(content: '', updatedAt: DateTime(2026));
  }
}
