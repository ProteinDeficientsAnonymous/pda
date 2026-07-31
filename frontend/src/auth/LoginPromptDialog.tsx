import type { SyntheticEvent } from 'react';
import { useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { checkPhone } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { PasswordField } from '@/components/ui/PasswordField';
import { PhoneField } from '@/components/ui/PhoneField';
import { extractApiError } from '@/utils/errors';

import { useAuthStore } from './store';

interface Props {
  open: boolean;
  onClose: () => void;
}

type Step = 'phone' | 'password';

// Lightweight sign-in for use as an overlay on an already-rendered page (e.g. a
// signed-out nav press) — the full phone->join-check->password flow lives in
// LoginScreen; this trims it to what fits a modal.
export function LoginPromptDialog({ open, onClose }: Props) {
  if (!open) return null;
  return <LoginPromptForm onClose={onClose} />;
}

function LoginPromptForm({ onClose }: { onClose: () => void }) {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  async function onPhoneSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setPhoneError(null);
    if (!phone || !isValidPhoneNumber(phone)) {
      setPhoneError('enter a valid phone number');
      return;
    }
    setChecking(true);
    try {
      const status = await checkPhone(phone);
      if (status === 'member') {
        setStep('password');
        return;
      }
      // Non-member states (pending review / unknown) need the full LoginScreen
      // copy for each case — send there instead of duplicating it in the modal.
      onClose();
      void navigate(`/login?redirect=${encodeURIComponent(location.pathname)}`, {
        state: { phone },
      });
    } catch (err) {
      setPhoneError(extractApiError(err, "couldn't check your number — try again"));
    } finally {
      setChecking(false);
    }
  }

  async function onPasswordSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setPasswordError(null);
    setSigningIn(true);
    try {
      await login(phone, password);
      onClose();
    } catch (err) {
      const message = extractApiError(err, "couldn't sign in — try again");
      setPasswordError(message);
      toast.error(message);
    } finally {
      setSigningIn(false);
    }
  }

  return (
    <Dialog open onClose={onClose} title="sign in">
      {step === 'phone' ? (
        <form
          onSubmit={(e) => {
            void onPhoneSubmit(e);
          }}
          className="flex flex-col gap-4"
        >
          <PhoneField
            label="phone number"
            value={phone}
            onChange={setPhone}
            error={phoneError ?? undefined}
            name="username"
            autoComplete="username"
          />
          <Button type="submit" fullWidth disabled={checking}>
            {checking ? 'checking…' : 'continue'}
          </Button>
        </form>
      ) : (
        <form
          onSubmit={(e) => {
            void onPasswordSubmit(e);
          }}
          className="flex flex-col gap-4"
        >
          <p className="text-muted text-sm">{phone}</p>
          <PasswordField
            label="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
            }}
            error={passwordError ?? undefined}
          />
          <Button type="submit" fullWidth disabled={signingIn}>
            {signingIn ? 'signing in…' : 'sign in'}
          </Button>
          <button
            type="button"
            onClick={() => {
              setStep('phone');
            }}
            className="text-brand-700 hover:text-brand-900 text-sm"
          >
            use a different number
          </button>
        </form>
      )}
      <p className="text-muted mt-4 text-center text-sm">
        not a member yet?{' '}
        <Link to="/join" className="text-brand-700 hover:text-brand-900" onClick={onClose}>
          request to join
        </Link>
      </p>
    </Dialog>
  );
}
