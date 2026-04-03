import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/screens/members_screen.dart';

import '../helpers/provider_overrides.dart';

// Narrow viewport → drawer nav, avoiding wide AppBar overflow.
const _kTestSize = Size(700, 900);

Widget _buildSubject({AuthNotifier? authNotifier, List<User>? users}) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const MembersScreen()),
      GoRoute(path: '/calendar', builder: (_, __) => const SizedBox()),
    ],
  );
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(
        () => authNotifier ?? _ManageUsersAuthNotifier(),
      ),
      usersProvider.overrideWith((_) async => users ?? _defaultUsers),
      rolesProvider.overrideWith((_) async => const []),
      silentNotificationsOverride,
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

const _defaultUsers = [
  User(
    id: 'u1',
    phoneNumber: '+12025551111',
    displayName: 'Alice',
    email: 'alice@example.com',
  ),
  User(
    id: 'u2',
    phoneNumber: '+12025552222',
    displayName: 'Bob',
    email: 'bob@example.com',
  ),
];

void main() {
  testWidgets('renders Members and Roles tabs', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Members'), findsOneWidget);
    expect(find.text('Roles'), findsOneWidget);
  });

  testWidgets('member names are displayed', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject());
    await tester.pumpAndSettle();

    expect(find.text('Alice'), findsOneWidget);
    expect(find.text('Bob'), findsOneWidget);
  });

  testWidgets('add member button shown for user with manage_users permission', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _ManageUsersAuthNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('add member'), findsOneWidget);
  });

  testWidgets('add member button hidden for user without manage_users', (
    tester,
  ) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildSubject(authNotifier: _ReadOnlyAuthNotifier()),
    );
    await tester.pumpAndSettle();

    expect(find.text('add member'), findsNothing);
  });

  testWidgets('shows empty state when no members exist', (tester) async {
    tester.view.physicalSize = _kTestSize;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildSubject(users: []));
    await tester.pumpAndSettle();

    expect(find.text('no members found'), findsOneWidget);
  });
}

class _ManageUsersAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'admin',
    phoneNumber: '+12025559999',
    displayName: 'Admin',
    roles: [
      Role(
        id: 'r1',
        name: 'admin',
        permissions: ['manage_users', 'manage_roles'],
      ),
    ],
  );

  @override
  Future<void> logout() async {}
}

class _ReadOnlyAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'u99',
    phoneNumber: '+12025550001',
    displayName: 'Regular',
  );

  @override
  Future<void> logout() async {}
}
