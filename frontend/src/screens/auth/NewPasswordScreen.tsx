import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { PasswordChecklist } from './PasswordChecklist';
import { passwordRule } from './passwordRule';

const schema = z
  .object({
    newPassword: passwordRule,
    confirmPassword: z.string(),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: 'passwords do not match',
    path: ['confirmPassword'],
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
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { newPassword: '', confirmPassword: '' },
  });
  const passwordValue = useWatch({ control, name: 'newPassword' });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({ newPassword: values.newPassword });
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't save password — try again"));
    }
  }

  return (
    <AuthLayout title="set a new password" subtitle="you're almost in">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <PasswordChecklist value={passwordValue} />
        <PasswordField
          label="new password"
          autoComplete="new-password"
          {...register('newPassword')}
          error={errors.newPassword?.message}
        />
        <PasswordField
          label="confirm new password"
          autoComplete="new-password"
          {...register('confirmPassword')}
          error={errors.confirmPassword?.message}
        />
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
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
