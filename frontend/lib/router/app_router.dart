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

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final isAuthenticated = authState.valueOrNull != null;
      final isLoading = authState.isLoading;

      if (isLoading) return null;

      final protectedRoutes = [
        '/calendar',
        '/members',
        '/join-requests',
        '/events/manage',
      ];
      final isProtected = protectedRoutes.contains(state.matchedLocation);

      if (isProtected && !isAuthenticated) {
        return '/login?redirect=${state.matchedLocation}';
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
        path: '/events/manage',
        builder: (_, __) => const EventManagementScreen(),
      ),
    ],
  );
});
