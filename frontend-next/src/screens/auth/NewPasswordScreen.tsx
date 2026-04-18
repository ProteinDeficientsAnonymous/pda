import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { isAxiosError } from 'axios';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { passwordRule } from './passwordRule';

const schema = z.object({
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;

export default function NewPasswordScreen() {
  // Post-reset: the user arrived here via magic-login with needs_onboarding=true
  // but an existing displayName — they only need to set a new password.
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { newPassword: '' },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({ newPassword: values.newPassword });
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setServerError(extractError(err));
    }
  }

  return (
    <AuthLayout title="set a new password" subtitle="you're almost in">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <TextField
          label="new password"
          type="password"
          autoComplete="new-password"
          {...register('newPassword')}
          error={errors.newPassword?.message}
          hint="at least 8 characters, one letter, one number"
        />
        {serverError ? (
          <p role="alert" className="text-sm text-red-600">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'saving…' : 'save password'}
        </Button>
      </form>
    </AuthLayout>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't save password — try again";
}
