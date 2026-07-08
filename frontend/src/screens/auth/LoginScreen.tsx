import { zodResolver } from '@hookform/resolvers/zod';
import type { SyntheticEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { isValidPhoneNumber } from 'react-phone-number-input';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { z } from 'zod';

import { checkPhone } from '@/api/join';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { PhoneField } from '@/components/ui/PhoneField';
import { postAuthRedirect } from '@/models/user';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { safeRedirect } from './redirect';
import { RequestLoginLinkDialog } from './RequestLoginLinkDialog';

type Step = 'phone' | 'password' | 'pending';

const passwordSchema = z.object({
  password: z.string().min(1, 'password required').max(72),
});
type PasswordValues = z.infer<typeof passwordSchema>;

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const invited = params.get('invited') === 'true';

  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

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
      if (status === 'pending') {
        setStep('pending');
        return;
      }
      void navigate('/join');
    } catch (err) {
      const message = extractApiError(err, "couldn't check your number — try again");
      setPhoneError(message);
      toast.error(message);
    } finally {
      setChecking(false);
    }
  }

  if (step === 'pending') {
    return (
      <AuthLayout title="under review" subtitle="your join request is in the queue">
        <p className="text-foreground-secondary text-sm">
          thanks for your patience — someone will reach out once your request has been reviewed.
        </p>
        <button
          type="button"
          onClick={() => {
            setStep('phone');
          }}
          className="text-brand-700 hover:text-brand-900 mt-4 text-sm"
        >
          back
        </button>
      </AuthLayout>
    );
  }

  if (step === 'password') {
    return (
      <PasswordStep
        phone={phone}
        invited={invited}
        onBack={() => {
          setStep('phone');
        }}
        onSuccess={() => {
          // Route based on the fresh user. Sending a pending user (password
          // setup / consent) to their gate screen directly — instead of to the
          // redirect/calendar and leaning on OnboardingGate to bounce — avoids
          // a race where the lazy target renders a blank Suspense fallback
          // before the gate re-evaluates with the new auth state.
          const gateTarget = postAuthRedirect(useAuthStore.getState().user);
          if (gateTarget) {
            void navigate(gateTarget, { replace: true });
            return;
          }
          // safeRedirect guards against open-redirect via the redirect param.
          void navigate(safeRedirect(params.get('redirect')), { replace: true });
        }}
        loginFn={login}
      />
    );
  }

  return (
    <AuthLayout title="welcome back" subtitle="sign in to your pda account">
      {invited ? (
        <div
          role="status"
          className="border-positive-border bg-positive-subtle text-positive mb-4 rounded-md border p-3 text-sm"
        >
          you already have an account — sign in below
        </div>
      ) : null}
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
      <p className="text-muted mt-4 text-center text-sm">
        not a member yet?{' '}
        <Link to="/join" className="text-brand-700 hover:text-brand-900">
          request to join
        </Link>
      </p>
    </AuthLayout>
  );
}

function PasswordStep({
  phone,
  invited,
  onBack,
  onSuccess,
  loginFn,
}: {
  phone: string;
  invited: boolean;
  onBack: () => void;
  onSuccess: () => void;
  loginFn: (phone: string, password: string) => Promise<void>;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const passwordRef = useRef<HTMLInputElement | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setFocus,
  } = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { password: '' },
  });

  useEffect(() => {
    setFocus('password');
  }, [setFocus]);

  const { ref: registerRef, ...passwordRegister } = register('password');

  async function onSubmit(values: PasswordValues) {
    setServerError(null);
    try {
      await loginFn(phone, values.password);
      onSuccess();
    } catch (err) {
      const message = extractApiError(err, "couldn't sign in — try again");
      setServerError(message);
      toast.error(message);
      passwordRef.current?.focus();
      passwordRef.current?.select();
    }
  }

  return (
    <AuthLayout title="welcome back" subtitle={phone}>
      {invited ? (
        <div
          role="status"
          className="border-positive-border bg-positive-subtle text-positive mb-4 rounded-md border p-3 text-sm"
        >
          you already have an account — sign in below
        </div>
      ) : null}
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <PasswordField
          label="password"
          autoComplete="current-password"
          {...passwordRegister}
          ref={(node) => {
            registerRef(node);
            passwordRef.current = node;
          }}
          error={errors.password?.message ?? serverError ?? undefined}
        />
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'signing in…' : 'sign in'}
        </Button>
        <button
          type="button"
          onClick={() => {
            setLinkDialogOpen(true);
          }}
          className="text-brand-700 hover:text-brand-900 text-sm"
        >
          request a login link
        </button>
        <button
          type="button"
          onClick={onBack}
          className="text-brand-700 hover:text-brand-900 text-sm"
        >
          use a different number
        </button>
      </form>
      <p className="text-muted mt-4 text-center text-sm">
        not a member yet?{' '}
        <Link to="/join" className="text-brand-700 hover:text-brand-900">
          request to join
        </Link>
      </p>
      <RequestLoginLinkDialog
        open={linkDialogOpen}
        initialPhone={phone}
        onClose={() => {
          setLinkDialogOpen(false);
        }}
      />
    </AuthLayout>
  );
}
