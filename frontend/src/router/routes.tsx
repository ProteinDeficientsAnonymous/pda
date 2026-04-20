// Route tree — mirrors app_router.dart. Grouped by guard shape:
//   public (no guard)        : landing, login, magic-login, onboarding, new-password, ...
//   authed (RequireAuth)     : guidelines, settings, profile, ...
//   permissioned             : admin/*, members, etc.
//
// All screens are lazy-loaded (React.lazy) — 1:1 replacement for DeferredScreen.

import { createBrowserRouter } from 'react-router-dom';
import { AuthBoot, OnboardingGate, RequireAuth, RequirePermission } from '@/auth/guards';
import { AppShell } from '@/layout/AppShell';
import { Permission } from '@/models/permissions';
import { lazyEl as el, lazyWithRetry } from './lazyRoute';
import { RootRouteError } from './RootRouteError';

const Login = lazyWithRetry(() => import('@/screens/auth/LoginScreen'));
const Onboarding = lazyWithRetry(() => import('@/screens/auth/OnboardingScreen'));
const NewPassword = lazyWithRetry(() => import('@/screens/auth/NewPasswordScreen'));
const MagicLogin = lazyWithRetry(() => import('@/screens/auth/MagicLoginScreen'));
const Home = lazyWithRetry(() => import('@/screens/public/HomeScreen'));
const Faq = lazyWithRetry(() => import('@/screens/public/FaqScreen'));
const Donate = lazyWithRetry(() => import('@/screens/public/DonateScreen'));
const Install = lazyWithRetry(() => import('@/screens/public/InstallAppScreen'));
const Guidelines = lazyWithRetry(() => import('@/screens/public/GuidelinesScreen'));
const Volunteer = lazyWithRetry(() => import('@/screens/public/VolunteerScreen'));
const Join = lazyWithRetry(() => import('@/screens/public/JoinScreen'));
const JoinSuccess = lazyWithRetry(() => import('@/screens/public/JoinSuccessScreen'));
const Calendar = lazyWithRetry(() => import('@/screens/calendar/CalendarScreen'));
const EventDetail = lazyWithRetry(() => import('@/screens/events/EventDetailScreen'));
const EventCreate = lazyWithRetry(() => import('@/screens/events/EventCreateScreen'));
const EventEdit = lazyWithRetry(() => import('@/screens/events/EventEditScreen'));
const MyEvents = lazyWithRetry(() => import('@/screens/events/MyEventsScreen'));
const Profile = lazyWithRetry(() => import('@/screens/profile/ProfileScreen'));
const Settings = lazyWithRetry(() => import('@/screens/settings/SettingsScreen'));
const Docs = lazyWithRetry(() => import('@/screens/docs/DocsScreen'));
const DocDetail = lazyWithRetry(() => import('@/screens/docs/DocDetailScreen'));
const Survey = lazyWithRetry(() => import('@/screens/surveys/SurveyScreen'));

// Admin screens
const AdminHub = lazyWithRetry(() => import('@/screens/admin/AdminHubScreen'));
const JoinRequestsAdmin = lazyWithRetry(() => import('@/screens/admin/JoinRequestsScreen'));
const EventManagement = lazyWithRetry(() => import('@/screens/admin/EventManagementScreen'));
const FlaggedEvents = lazyWithRetry(() => import('@/screens/admin/FlaggedEventsScreen'));
const WhatsappConfig = lazyWithRetry(() => import('@/screens/admin/WhatsappConfigScreen'));
const JoinFormAdmin = lazyWithRetry(() => import('@/screens/admin/JoinFormAdminScreen'));
const SurveyAdminList = lazyWithRetry(() => import('@/screens/admin/SurveyAdminListScreen'));
const SurveyBuilder = lazyWithRetry(() => import('@/screens/admin/SurveyBuilderScreen'));
const SurveyResponses = lazyWithRetry(() => import('@/screens/admin/SurveyResponsesScreen'));
const Members = lazyWithRetry(() => import('@/screens/admin/MembersScreen'));
const MemberDetail = lazyWithRetry(() => import('@/screens/admin/MemberDetailScreen'));
const MemberProfile = lazyWithRetry(() => import('@/screens/members/MemberProfileScreen'));

const Stub = lazyWithRetry(() => import('@/screens/NotImplemented'));

export const router = createBrowserRouter([
  {
    element: (
      <AuthBoot>
        <OnboardingGate />
      </AuthBoot>
    ),
    errorElement: <RootRouteError />,
    children: [
      // Auth screens render edge-to-edge (no AppShell).
      { path: '/login', element: el(<Login />) },
      { path: '/magic-login/:token', element: el(<MagicLogin />) },
      { path: '/onboarding', element: el(<Onboarding />) },
      { path: '/new-password', element: el(<NewPassword />) },

      // Everything else uses the shared shell (nav + outlet).
      {
        element: <AppShell />,
        children: [
          // ---- public ----
          { path: '/', element: el(<Home />) },
          { path: '/join', element: el(<Join />) },
          { path: '/join/success', element: el(<JoinSuccess />) },
          { path: '/calendar', element: el(<Calendar />) },
          { path: '/events/:id', element: el(<EventDetail />) },
          { path: '/surveys/:slug', element: el(<Survey />) },
          { path: '/donate', element: el(<Donate />) },
          { path: '/install', element: el(<Install />) },
          { path: '/faq', element: el(<Faq />) },

          // ---- authed ----
          {
            element: <RequireAuth />,
            children: [
              { path: '/guidelines', element: el(<Guidelines />) },
              { path: '/settings', element: el(<Settings />) },
              { path: '/profile', element: el(<Profile />) },
              { path: '/volunteer', element: el(<Volunteer />) },
              { path: '/events/mine', element: el(<MyEvents />) },
              { path: '/events/add', element: el(<EventCreate />) },
              { path: '/events/:id/edit', element: el(<EventEdit />) },
              { path: '/members/:userId', element: el(<MemberProfile />) },
            ],
          },

          // ---- admin hub: any authed user can visit; the hub itself shows
          //      only the tiles their permissions allow.
          {
            element: <RequireAuth />,
            children: [{ path: '/admin', element: el(<AdminHub />) }],
          },

          // ---- permissioned ----
          {
            element: <RequirePermission perm={Permission.ManageUsers} />,
            children: [
              { path: '/members', element: el(<Members />) },
              { path: '/admin/members/:id', element: el(<MemberDetail />) },
            ],
          },
          {
            element: <RequirePermission perm={Permission.ApproveJoinRequests} />,
            children: [{ path: '/join-requests', element: el(<JoinRequestsAdmin />) }],
          },
          {
            element: <RequirePermission perm={Permission.ManageEvents} />,
            children: [
              { path: '/events/manage', element: el(<EventManagement />) },
              { path: '/admin/flagged-events', element: el(<FlaggedEvents />) },
            ],
          },
          {
            element: <RequirePermission perm={Permission.ManageWhatsapp} />,
            children: [{ path: '/admin/whatsapp', element: el(<WhatsappConfig />) }],
          },
          {
            element: <RequirePermission perm={Permission.ManageDocuments} />,
            children: [
              { path: '/docs', element: el(<Docs />) },
              { path: '/docs/:id', element: el(<DocDetail />) },
            ],
          },
          {
            element: <RequirePermission perm={Permission.EditJoinQuestions} />,
            children: [{ path: '/admin/join-form', element: el(<JoinFormAdmin />) }],
          },
          {
            element: <RequirePermission perm={Permission.ManageSurveys} />,
            children: [
              { path: '/admin/surveys', element: el(<SurveyAdminList />) },
              { path: '/admin/surveys/:id', element: el(<SurveyBuilder />) },
              { path: '/admin/surveys/:id/responses', element: el(<SurveyResponses />) },
            ],
          },

          // ---- catch-all ----
          { path: '*', element: el(<Stub />) },
        ],
      },
    ],
  },
]);
