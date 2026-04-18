// Route tree — mirrors app_router.dart. Grouped by guard shape:
//   public (no guard)        : landing, login, magic-login, onboarding, new-password, ...
//   authed (RequireAuth)     : guidelines, settings, profile, ...
//   permissioned             : admin/*, members, etc.
//
// All screens are lazy-loaded (React.lazy) — 1:1 replacement for DeferredScreen.

import { lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { AuthBoot, OnboardingGate, RequireAuth, RequirePermission } from '@/auth/guards';
import { Permission } from '@/models/permissions';
import { lazyEl as el } from './lazyRoute';

const Login = lazy(() => import('@/screens/auth/LoginScreen'));
const Onboarding = lazy(() => import('@/screens/auth/OnboardingScreen'));
const NewPassword = lazy(() => import('@/screens/auth/NewPasswordScreen'));
const MagicLogin = lazy(() => import('@/screens/auth/MagicLoginScreen'));
const Stub = lazy(() => import('@/screens/NotImplemented'));

export const router = createBrowserRouter([
  {
    element: (
      <AuthBoot>
        <OnboardingGate />
      </AuthBoot>
    ),
    children: [
      // ---- public ----
      { path: '/', element: el(<Stub />) },
      { path: '/login', element: el(<Login />) },
      { path: '/magic-login/:token', element: el(<MagicLogin />) },
      { path: '/onboarding', element: el(<Onboarding />) },
      { path: '/new-password', element: el(<NewPassword />) },
      { path: '/join', element: el(<Stub />) },
      { path: '/join/success', element: el(<Stub />) },
      { path: '/calendar', element: el(<Stub />) },
      { path: '/events/:id', element: el(<Stub />) },
      { path: '/events/add', element: el(<Stub />) },
      { path: '/surveys/:slug', element: el(<Stub />) },
      { path: '/donate', element: el(<Stub />) },
      { path: '/install', element: el(<Stub />) },
      { path: '/faq', element: el(<Stub />) },

      // ---- authed ----
      {
        element: <RequireAuth />,
        children: [
          { path: '/guidelines', element: el(<Stub />) },
          { path: '/settings', element: el(<Stub />) },
          { path: '/profile', element: el(<Stub />) },
          { path: '/volunteer', element: el(<Stub />) },
          { path: '/docs', element: el(<Stub />) },
          { path: '/docs/:id', element: el(<Stub />) },
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
]);
