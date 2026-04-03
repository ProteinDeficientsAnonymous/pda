import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/faq_provider.dart';
import 'package:pda/screens/faq_screen.dart';

import '../helpers/provider_overrides.dart';

const _kTestSize = Size(700, 900);

Widget _buildSubject({FaqNotifier? faqNotifier, AuthNotifier? authNotifier}) {
  final router = GoRouter(
    routes: [GoRoute(path: '/', builder: (_, __) => const FAQScreen())],
  );
  return ProviderScope(
    overrides: [
      faqNotifierProvider.overrideWith(() => faqNotifier ?? _FakeFaqNotifier()),
      authProvider.overrideWith(() => authNotifier ?? _MemberAuthNotifier()),
      silentNotificationsOverride,
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

    await tester.pumpWidget(_buildSubject(faqNotifier: _LoadingFaqNotifier()));
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('hides Edit button for member without edit_faq', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Edit'), findsNothing);
  });

  testWidgets('shows Edit button for user with edit_faq permission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _FaqEditorAuthNotifier()),
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

class _FaqEditorAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u2',
    phoneNumber: '+12025559002',
    displayName: 'FAQ Editor',
    roles: [
      Role(id: 'r1', name: 'faq_editor', permissions: ['edit_faq']),
    ],
  );

  @override
  Future<void> logout() async {}
}

class _FakeFaqNotifier extends FaqNotifier {
  @override
  Future<FAQ> build() async => FAQ(content: '', updatedAt: DateTime(2026));
}

class _LoadingFaqNotifier extends FaqNotifier {
  @override
  Future<FAQ> build() async {
    await Completer<void>().future;
    return FAQ(content: '', updatedAt: DateTime(2026));
  }
}
