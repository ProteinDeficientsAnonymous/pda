import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/auth/login_screen.dart';
import 'package:pda/screens/auth/magic_login_screen.dart';
import 'package:pda/screens/auth/onboarding_screen.dart';
import 'package:pda/screens/auth/new_password_screen.dart';
import 'package:pda/screens/calendar_screen.dart';
import 'package:pda/screens/event_management_screen.dart';
import 'package:pda/screens/home_screen.dart';
import 'package:pda/screens/join_requests_screen.dart';
import 'package:pda/screens/join_screen.dart';
import 'package:pda/screens/join_success_screen.dart';
import 'package:pda/screens/members_screen.dart';
import 'package:pda/screens/faq_screen.dart';
import 'package:pda/screens/guidelines_screen.dart';
import 'package:pda/screens/event_detail_screen.dart';
import 'package:pda/screens/donate_screen.dart';
import 'package:pda/screens/settings_screen.dart';
import 'package:pda/screens/volunteer_screen.dart';
import 'package:pda/screens/admin_screen.dart';
import 'package:pda/screens/join_form_config_screen.dart';
import 'package:pda/screens/survey_admin_screen.dart';
import 'package:pda/screens/survey_builder_screen.dart';
import 'package:pda/screens/survey_responses_screen.dart';
import 'package:pda/screens/survey_screen.dart';
import 'package:pda/screens/docs_screen.dart';
import 'package:pda/screens/doc_detail_screen.dart';
import 'package:pda/screens/whatsapp_config_screen.dart';
import 'package:pda/screens/profile_screen.dart';
import 'package:pda/screens/member_profile_screen.dart';
import 'package:pda/config/constants.dart';

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

      final loc = state.matchedLocation;

      // Users with needs_onboarding are routed based on whether they're
      // first-time (no display name yet) or just resetting their password.
      if (user != null && user.needsOnboarding) {
        final isPasswordReset = user.displayName.isNotEmpty;
        final targetRoute = isPasswordReset ? '/new-password' : '/onboarding';
        if (loc != targetRoute) return targetRoute;
      }
      if (user != null && !user.needsOnboarding) {
        if (loc == '/onboarding') return '/guidelines';
        if (loc == '/new-password') return '/calendar';
      }

      final isProtected =
          loc == '/guidelines' ||
          loc.startsWith('/members') ||
          loc == '/join-requests' ||
          loc == '/events/manage' ||
          loc == '/events/mine' ||
          loc == '/settings' ||
          loc == '/volunteer' ||
          loc == '/admin' ||
          loc == '/admin/join-form' ||
          loc == '/admin/whatsapp' ||
          loc.startsWith('/admin/surveys') ||
          loc == '/docs' ||
          loc.startsWith('/docs/');

      if (isProtected && !isAuthenticated) {
        return '/login?redirect=${state.matchedLocation}';
      }

      if (isAuthenticated && loc == '/login') {
        return '/calendar';
      }

      if (isAuthenticated) {
        if (loc == '/members' && !user.hasPermission(Permission.manageUsers)) {
          return '/calendar';
        }
        if (loc == '/join-requests' &&
            !user.hasPermission(Permission.approveJoinRequests)) {
          return '/calendar';
        }
        if (loc == '/events/manage' &&
            !user.hasPermission(Permission.manageEvents)) {
          return '/calendar';
        }
        if (loc == '/admin' && !user.hasAnyAdminPermission) {
          return '/calendar';
        }
        if (loc == '/admin/whatsapp' &&
            !user.hasPermission(Permission.manageWhatsapp)) {
          return '/calendar';
        }
        if (loc == '/admin/join-form' &&
            !user.hasPermission(Permission.editJoinQuestions)) {
          return '/calendar';
        }
        if (loc.startsWith('/admin/surveys') &&
            !user.hasPermission(Permission.manageSurveys)) {
          return '/calendar';
        }
      }

      return null;
    },
    routes: [
      GoRoute(path: '/', name: 'home', builder: (_, __) => const HomeScreen()),
      GoRoute(
        path: '/join',
        name: 'join',
        builder: (_, __) => const JoinScreen(),
      ),
      GoRoute(
        path: '/join/success',
        name: 'join-success',
        builder: (_, __) => const JoinSuccessScreen(),
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/magic-login/:token',
        name: 'magic-login',
        builder:
            (_, state) =>
                MagicLoginScreen(token: state.pathParameters['token']!),
      ),
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        builder: (_, __) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/new-password',
        name: 'new-password',
        builder: (_, __) => const NewPasswordScreen(),
      ),
      GoRoute(
        path: '/calendar',
        name: 'calendar',
        builder: (_, __) => const CalendarScreen(),
      ),
      GoRoute(
        path: '/members',
        name: 'members',
        builder: (_, __) => const MembersScreen(),
      ),
      GoRoute(
        path: '/join-requests',
        name: 'join-requests',
        builder: (_, __) => const JoinRequestsScreen(),
      ),
      GoRoute(
        path: '/events/mine',
        name: 'my-events',
        builder: (_, __) => const EventManagementScreen(myEventsOnly: true),
      ),
      GoRoute(
        path: '/events/manage',
        name: 'manage-events',
        builder: (_, __) => const EventManagementScreen(),
      ),
      GoRoute(
        path: '/guidelines',
        name: 'guidelines',
        builder: (_, __) => const GuidelinesScreen(),
      ),
      GoRoute(path: '/faq', name: 'faq', builder: (_, __) => const FAQScreen()),
      GoRoute(
        path: '/settings',
        name: 'settings',
        builder: (_, __) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/donate',
        name: 'donate',
        builder: (_, __) => const DonateScreen(),
      ),
      GoRoute(
        path: '/volunteer',
        name: 'volunteer',
        builder: (_, __) => const VolunteerScreen(),
      ),
      GoRoute(
        path: '/admin',
        name: 'admin',
        builder: (_, __) => const AdminScreen(),
      ),
      GoRoute(
        path: '/admin/join-form',
        name: 'join-form-config',
        builder: (_, __) => const JoinFormConfigScreen(),
      ),
      GoRoute(
        path: '/admin/surveys',
        name: 'survey-admin',
        builder: (_, __) => const SurveyAdminScreen(),
      ),
      GoRoute(
        path: '/admin/surveys/:id',
        name: 'survey-builder',
        builder:
            (_, state) =>
                SurveyBuilderScreen(surveyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/admin/surveys/:id/responses',
        name: 'survey-responses',
        builder:
            (_, state) =>
                SurveyResponsesScreen(surveyId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/admin/whatsapp',
        name: 'whatsapp-config',
        builder: (_, __) => const WhatsAppConfigScreen(),
      ),
      GoRoute(
        path: '/docs',
        name: 'docs',
        builder: (_, __) => const DocsScreen(),
      ),
      GoRoute(
        path: '/docs/:id',
        name: 'doc-detail',
        builder:
            (_, state) => DocDetailScreen(docId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/profile',
        name: 'profile',
        builder: (_, __) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/members/:id',
        name: 'member-profile',
        builder:
            (_, state) =>
                MemberProfileScreen(userId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/surveys/:slug',
        name: 'survey',
        builder:
            (_, state) => SurveyScreen(slug: state.pathParameters['slug']!),
      ),
      GoRoute(
        path: '/events/:id',
        name: 'event-detail',
        builder:
            (_, state) =>
                EventDetailScreen(eventId: state.pathParameters['id']!),
      ),
    ],
  );
});
