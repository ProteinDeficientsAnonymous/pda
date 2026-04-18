import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '@/auth/store';
import { AuthLayout } from './AuthLayout';

type State = 'pending' | 'error';

export default function MagicLoginScreen() {
  const { token } = useParams();
  const magicLogin = useAuthStore((s) => s.magicLogin);
  const navigate = useNavigate();
  const [state, setState] = useState<State>('pending');

  useEffect(() => {
    if (!token) return;
    void magicLogin(token)
      .then(() => {
        // OnboardingGate handles the needs_onboarding redirect.
        void navigate('/calendar', { replace: true });
      })
      .catch(() => {
        setState('error');
      });
  }, [token, magicLogin, navigate]);

  if (!token) return <Navigate to="/login" replace />;

  if (state === 'error') {
    return (
      <AuthLayout title="link expired" subtitle="this login link didn't work">
        <p className="text-sm text-neutral-600">
          ask an organizer to send a new one, or{' '}
          <a href="/login" className="underline">
            sign in with your password
          </a>
          .
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="signing you in…">
      <p className="text-sm text-neutral-500">hold tight 🌿</p>
    </AuthLayout>
  );
}
