import { useEffect, useState } from 'react';
import { AxiosError } from 'axios';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/auth/store';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { RequestLoginLinkDialog } from './RequestLoginLinkDialog';

type State = 'pending' | 'expired' | 'cross_user';

export default function MagicLoginScreen() {
  const { token } = useParams();
  const magicLogin = useAuthStore((s) => s.magicLogin);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [state, setState] = useState<State>('pending');
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);

  useEffect(() => {
    if (!token) return;
    void magicLogin(token)
      .then(() => {
        // Route based on the fresh user in the store. Doing this here (instead
        // of leaning on OnboardingGate) avoids a race where /calendar renders
        // before the gate re-evaluates with the new auth state.
        const user = useAuthStore.getState().user;
        if (user?.needsOnboarding) {
          const target = user.displayName.length > 0 ? '/new-password' : '/onboarding';
          void navigate(target, { replace: true });
          return;
        }
        const redirect = params.get('redirect');
        void navigate(redirect ? decodeURIComponent(redirect) : '/calendar', { replace: true });
      })
      .catch((err: unknown) => {
        // 403 means the caller is already signed in as a different user. The
        // store preserves that session, so surface a distinct message instead
        // of the generic "link expired" and a "request new link" CTA that
        // would just rotate the victim's own magic token.
        if (err instanceof AxiosError && err.response?.status === 403) {
          setState('cross_user');
          return;
        }
        setState('expired');
      });
  }, [token, magicLogin, navigate, params]);

  if (!token) return <Navigate to="/login" replace />;

  if (state === 'cross_user') {
    return (
      <AuthLayout title="already signed in" subtitle="this link is for a different account">
        <p className="text-sm text-foreground-tertiary">
          log out first, then open the link again
        </p>
        <Button
          fullWidth
          className="mt-4"
          onClick={() => {
            void navigate('/calendar', { replace: true });
          }}
        >
          back to calendar
        </Button>
      </AuthLayout>
    );
  }

  if (state === 'expired') {
    return (
      <AuthLayout title="link expired" subtitle="this login link didn't work">
        <p className="text-sm text-foreground-tertiary">
          grab a fresh one below, or{' '}
          <a href="/login" className="text-brand-700 hover:text-brand-900">
            sign in with your password
          </a>
        </p>
        <Button
          fullWidth
          className="mt-4"
          onClick={() => {
            setLinkDialogOpen(true);
          }}
        >
          send me a new link
        </Button>
        <RequestLoginLinkDialog
          open={linkDialogOpen}
          onClose={() => {
            setLinkDialogOpen(false);
          }}
        />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="signing you in…">
      <p className="text-sm text-muted">hold tight 🌿</p>
    </AuthLayout>
  );
}
