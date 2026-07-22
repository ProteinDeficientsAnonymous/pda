import { type ReactNode, useEffect } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useFlag } from '@/api/featureFlags';
import { RequireEmail } from '@/components/RequireEmail';
import { CONSENT_REGISTRY } from '@/models/consent';
import type { FeatureFlagKey } from '@/models/featureFlags';
import { hasPermission, type PermissionKey } from '@/models/permissions';
import { consentRedirect, passwordSetupRedirect } from '@/models/user';

import { useAuthStore } from './store';

// Policy pages the consent screen links to must stay reachable while the consent
// gate is active, otherwise the user can't read what they're agreeing to.
const CONSENT_POLICY_PATHS = new Set(CONSENT_REGISTRY.map((c) => c.linkTo.toLowerCase()));

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
  const profileStepActive = useAuthStore((s) => s.profileStepActive);
  const location = useLocation();
  const path = location.pathname.toLowerCase();

  // Checked before setupTarget goes null post-completeOnboarding, or this would bounce the user mid-step.
  if (user && (path === '/onboarding' || path === '/new-password') && profileStepActive) {
    return <Outlet />;
  }

  // passwordSetupRedirect is the shared source of truth (also used by
  // MagicLoginScreen) for where a setup-pending user must go. Password setup
  // takes priority over the consent gate — a brand-new user sets their name +
  // password before being asked to consent.
  const setupTarget = passwordSetupRedirect(user);
  const consentTarget = consentRedirect(user);

  if (setupTarget) {
    if (path !== setupTarget) {
      return <Navigate to={setupTarget} replace />;
    }
  } else if (consentTarget) {
    // Pin to /consent, but leave the policy pages it links to reachable — users
    // must be able to read what they're agreeing to.
    if (path !== consentTarget && !CONSENT_POLICY_PATHS.has(path)) {
      return <Navigate to={consentTarget} replace />;
    }
  } else if (user) {
    // Authed user with nothing pending shouldn't sit on onboarding/consent screens.
    if (path === '/onboarding') return <Navigate to="/guidelines" replace />;
    if (path === '/new-password') return <Navigate to="/calendar" replace />;
    if (path === '/consent') return <Navigate to="/calendar" replace />;
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

// ----------------------------------------------------------------------------
// RequireFlag — gates a route behind a feature flag. Fail-closed: a flag that
// is off, missing, or still loading redirects to /calendar, so a dark feature
// never flashes into view before the flag resolves.
// ----------------------------------------------------------------------------

export function RequireFlag({ flag }: { flag: FeatureFlagKey }) {
  const enabled = useFlag(flag);
  if (!enabled) {
    return <Navigate to="/calendar" replace />;
  }
  return <Outlet />;
}

// ----------------------------------------------------------------------------
// EmailGate — blocks the app for authed users without an email. Composes
// AFTER OnboardingGate so needs_onboarding users finish that flow first.
// ----------------------------------------------------------------------------

export function EmailGate() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  // You can't stay logged in without an email, but "not now" isn't a dead end:
  // it drops the session and lands on the public calendar, so the app stays
  // usable from a logged-out state (an authed-only route would otherwise
  // bounce to /login). A failed logout is swallowed so RequireEmail can
  // re-enable its button and let the user retry.
  async function onSkip() {
    try {
      await logout();
      void navigate('/calendar', { replace: true });
    } catch {
      // network/server error — stay on the modal, user can retry
    }
  }
  if (user && !user.needsOnboarding && !user.email) {
    return <RequireEmail onSkip={onSkip} />;
  }
  return <Outlet />;
}
