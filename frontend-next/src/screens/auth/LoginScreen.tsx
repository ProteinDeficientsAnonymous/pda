import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { z } from 'zod';
import { isAxiosError } from 'axios';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';

const schema = z.object({
  phoneNumber: z.string().min(1, 'phone required').max(20),
  password: z.string().min(1, 'password required').max(128),
});

type FormValues = z.infer<typeof schema>;

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { phoneNumber: '', password: '' },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values.phoneNumber, values.password);
      const redirect = params.get('redirect');
      void navigate(redirect ? decodeURIComponent(redirect) : '/calendar', { replace: true });
    } catch (err) {
      setServerError(extractError(err));
    }
  }

  return (
    <AuthLayout title="welcome back" subtitle="sign in to your pda account">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <TextField
          label="phone number"
          type="tel"
          autoComplete="tel"
          {...register('phoneNumber')}
          error={errors.phoneNumber?.message}
        />
        <TextField
          label="password"
          type="password"
          autoComplete="current-password"
          {...register('password')}
          error={errors.password?.message}
        />
        {serverError ? (
          <p role="alert" className="text-sm text-red-600">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'signing in…' : 'sign in'}
        </Button>
      </form>
      <p className="mt-4 text-center text-sm text-neutral-500">
        not a member yet?{' '}
        <Link to="/join" className="text-neutral-900 underline">
          submit a join request
        </Link>
      </p>
    </AuthLayout>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
    if (err.response?.status === 401) return 'invalid phone or password';
    return "couldn't sign in — try again";
  }
  return "couldn't sign in — try again";
}
