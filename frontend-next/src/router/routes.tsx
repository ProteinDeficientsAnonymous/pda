// Route tree — mirrors app_router.dart. Grouped by guard shape:
//   public (no guard)        : landing, login, magic-login, onboarding, new-password, ...
//   authed (RequireAuth)     : guidelines, settings, profile, ...
//   permissioned             : admin/*, members, etc.
//
// All screens are lazy-loaded (React.lazy) — 1:1 replacement for DeferredScreen.

import { lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { AuthBoot, OnboardingGate, RequireAuth, RequirePermission } from '@/auth/guards';
import { AppShell } from '@/layout/AppShell';
import { Permission } from '@/models/permissions';
import { lazyEl as el } from './lazyRoute';

const Login = lazy(() => import('@/screens/auth/LoginScreen'));
const Onboarding = lazy(() => import('@/screens/auth/OnboardingScreen'));
const NewPassword = lazy(() => import('@/screens/auth/NewPasswordScreen'));
const MagicLogin = lazy(() => import('@/screens/auth/MagicLoginScreen'));
const Home = lazy(() => import('@/screens/public/HomeScreen'));
const Faq = lazy(() => import('@/screens/public/FaqScreen'));
const Donate = lazy(() => import('@/screens/public/DonateScreen'));
const Install = lazy(() => import('@/screens/public/InstallAppScreen'));
const Guidelines = lazy(() => import('@/screens/public/GuidelinesScreen'));
const Volunteer = lazy(() => import('@/screens/public/VolunteerScreen'));
const Join = lazy(() => import('@/screens/public/JoinScreen'));
const JoinSuccess = lazy(() => import('@/screens/public/JoinSuccessScreen'));
const Calendar = lazy(() => import('@/screens/calendar/CalendarScreen'));
const EventDetail = lazy(() => import('@/screens/events/EventDetailScreen'));
const EventCreate = lazy(() => import('@/screens/events/EventCreateScreen'));
const EventEdit = lazy(() => import('@/screens/events/EventEditScreen'));
const Profile = lazy(() => import('@/screens/profile/ProfileScreen'));
const Settings = lazy(() => import('@/screens/settings/SettingsScreen'));
const Docs = lazy(() => import('@/screens/docs/DocsScreen'));
const DocDetail = lazy(() => import('@/screens/docs/DocDetailScreen'));
const Survey = lazy(() => import('@/screens/surveys/SurveyScreen'));
const Stub = lazy(() => import('@/screens/NotImplemented'));

export const router = createBrowserRouter([
  {
    element: (
      <AuthBoot>
        <OnboardingGate />
      </AuthBoot>
    ),
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
          // Authed-only write paths, placed here (outside RequireAuth) because
          // the form itself renders regardless of auth status — we let the
          // backend 401 return bubble up to the error UI.
          { path: '/events/:id/edit', element: el(<EventEdit />) },
          { path: '/events/add', element: el(<EventCreate />) },
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
              { path: '/docs', element: el(<Docs />) },
              { path: '/docs/:id', element: el(<DocDetail />) },
              { path: '/events/mine', element: el(<Stub />) },
            ],
          },

          // ---- permissioned ----
          {
            element: <RequirePermission perm={Permission.ManageUsers} />,
            children: [
              { path: '/members', element: el(<Stub />) },
              { path: '/members/:id', element: el(<Stub />) },
            ],
          },
          {
            element: <RequirePermission perm={Permission.ApproveJoinRequests} />,
            children: [{ path: '/join-requests', element: el(<Stub />) }],
          },
          {
            element: <RequirePermission perm={Permission.ManageEvents} />,
            children: [
              { path: '/events/manage', element: el(<Stub />) },
              { path: '/admin/flagged-events', element: el(<Stub />) },
            ],
          },
          {
            element: <RequirePermission perm={Permission.ManageWhatsapp} />,
            children: [{ path: '/admin/whatsapp', element: el(<Stub />) }],
          },
          {
            element: <RequirePermission perm={Permission.EditJoinQuestions} />,
            children: [{ path: '/admin/join-form', element: el(<Stub />) }],
          },
          {
            element: <RequirePermission perm={Permission.ManageSurveys} />,
            children: [
              { path: '/admin/surveys', element: el(<Stub />) },
              { path: '/admin/surveys/:id', element: el(<Stub />) },
              { path: '/admin/surveys/:id/responses', element: el(<Stub />) },
            ],
          },

          // ---- catch-all ----
          { path: '*', element: el(<Stub />) },
        ],
      },
    ],
  },
]);
