import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/auth/login_screen.dart';
import 'package:pda/screens/calendar_screen.dart';
import 'package:pda/screens/event_management_screen.dart';
import 'package:pda/screens/home_screen.dart';
import 'package:pda/screens/join_requests_screen.dart';
import 'package:pda/screens/join_screen.dart';
import 'package:pda/screens/join_success_screen.dart';
import 'package:pda/screens/members_screen.dart';
import 'package:pda/screens/guidelines_screen.dart';
import 'package:pda/screens/settings_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  // Use ref.listen (not ref.watch) so auth state changes trigger redirect
  // re-evaluation without recreating the entire GoRouter instance.
  final refreshNotifier = ValueNotifier<int>(0);
  ref.listen(authProvider, (_, __) {
    refreshNotifier.value++;
  });
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final user = authState.valueOrNull;
      final isAuthenticated = user != null;
      final isLoading = authState.isLoading;

      if (isLoading) return null;

      final authRequiredRoutes = [
        '/calendar',
        '/guidelines',
        '/members',
        '/join-requests',
        '/events/manage',
        '/events/mine',
        '/settings',
      ];
      final isProtected = authRequiredRoutes.contains(state.matchedLocation);

      if (isProtected && !isAuthenticated) {
        return '/login?redirect=${state.matchedLocation}';
      }

      if (isAuthenticated) {
        final loc = state.matchedLocation;
        if (loc == '/members' && !user.hasPermission('manage_users')) {
          return '/calendar';
        }
        if (loc == '/join-requests' &&
            !user.hasPermission('approve_join_requests')) {
          return '/calendar';
        }
        if (loc == '/events/manage' && !user.hasPermission('manage_events')) {
          return '/calendar';
        }
      }

      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/join', builder: (_, __) => const JoinScreen()),
      GoRoute(
        path: '/join/success',
        builder: (_, __) => const JoinSuccessScreen(),
      ),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/calendar', builder: (_, __) => const CalendarScreen()),
      GoRoute(path: '/members', builder: (_, __) => const MembersScreen()),
      GoRoute(
        path: '/join-requests',
        builder: (_, __) => const JoinRequestsScreen(),
      ),
      GoRoute(
        path: '/events/mine',
        builder: (_, __) => const EventManagementScreen(myEventsOnly: true),
      ),
      GoRoute(
        path: '/events/manage',
        builder: (_, __) => const EventManagementScreen(),
      ),
      GoRoute(
        path: '/guidelines',
        builder: (_, __) => const GuidelinesScreen(),
      ),
      GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
    ],
  );
});
