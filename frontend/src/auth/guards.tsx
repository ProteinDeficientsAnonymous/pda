// Route guards. Port of the GoRouter `redirect:` pipeline from app_router.dart.
//
// Three wrappers, composable via nested routes:
//   <AuthBoot>           — root gate: blocks all routes until restoreSession resolves.
//   <RequireAuth>        — bounces unauthed users to /login?redirect=<path>.
//   <RequirePermission>  — additionally checks a permission key; bounces to /calendar.
//   <OnboardingGate>     — routes needs_onboarding users to /onboarding or /new-password.
//
// The onboarding gate wraps the WHOLE app so it applies on every navigation,
// matching the Flutter behavior.

import { useEffect, type ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from './store';
import { hasPermission, type PermissionKey } from '@/models/permissions';

// ----------------------------------------------------------------------------
// AuthBoot — kick off session restore exactly once on mount.
// Only gates children during the initial boot (idle → first transition).
// After boot, a 'loading' status from a subsequent login/magic-login/etc.
// must NOT unmount the tree — screens like MagicLoginScreen own their own
// loading UX and re-mounting them mid-request would re-fire their effects
// and burn single-use tokens.
// ----------------------------------------------------------------------------

export function AuthBoot({ children }: { children: ReactNode }) {
  const status = useAuthStore((s) => s.status);
  const restore = useAuthStore((s) => s.restoreSession);
  // Subscribe to the store's boot latch — set once the initial restore
  // resolves. After boot, subsequent 'loading' states (login/magic-login)
  // must NOT unmount the tree — screens like MagicLoginScreen own their own
  // loading UX and re-mounting them mid-request would re-fire their effects
  // and burn single-use tokens.
  const booted = useAuthStore((s) => s.booted);

  useEffect(() => {
    if (status === 'idle') {
      void restore();
    }
  }, [status, restore]);

  if (!booted && (status === 'idle' || status === 'loading')) {
    return <BootSpinner />;
  }
  return <>{children}</>;
}

function BootSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-sm text-neutral-500">loading…</div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// OnboardingGate — mirrors app_router.dart lines 47–80 (needsOnboarding logic).
// ----------------------------------------------------------------------------

export function OnboardingGate() {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  const path = location.pathname.toLowerCase();

  if (user?.needsOnboarding) {
    // Two shapes:
    //   - first-time user (empty displayName)  → /onboarding (name + password)
    //   - password reset (has displayName)     → /new-password (password only)
    const target = user.displayName.length > 0 ? '/new-password' : '/onboarding';
    if (path !== target) {
      return <Navigate to={target} replace />;
    }
  } else if (user) {
    // Authed user with onboarding complete shouldn't sit on onboarding screens.
    if (path === '/onboarding') return <Navigate to="/guidelines" replace />;
    if (path === '/new-password') return <Navigate to="/calendar" replace />;
    if (path === '/login') return <Navigate to="/calendar" replace />;
  }

  return <Outlet />;
}

// ----------------------------------------------------------------------------
// RequireAuth — unauthed → /login?redirect=<original>
// ----------------------------------------------------------------------------

export function RequireAuth() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const location = useLocation();

  if (!isAuthed) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }
  return <Outlet />;
}

// ----------------------------------------------------------------------------
// RequirePermission — authed + permission check.
// ----------------------------------------------------------------------------

export function RequirePermission({ perm }: { perm: PermissionKey }) {
  const user = useAuthStore((s) => s.user);
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const location = useLocation();

  if (!isAuthed) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }
  if (!hasPermission(user, perm)) {
    return <Navigate to="/calendar" replace />;
  }
  return <Outlet />;
}
