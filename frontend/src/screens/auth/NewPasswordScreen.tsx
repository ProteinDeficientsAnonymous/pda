import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { postAuthRedirect } from '@/models/user';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { OnboardingProfileStep } from './OnboardingProfileStep';
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
  // Shared by two populations: self-service password resets (already-onboarded
  // members — skip straight to the app) and first-time join-request users who
  // already have name+email but have never seen the profile step.
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const finishProfileStep = useAuthStore((s) => s.finishProfileStep);
  const profileStepActive = useAuthStore((s) => s.profileStepActive);
  const needsOnboarding = useAuthStore((s) => s.user?.needsOnboarding ?? false);
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
      await completeOnboarding({
        newPassword: values.newPassword,
        startProfileStep: needsOnboarding,
      });
      if (needsOnboarding) return;
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't save password — try again"));
    }
  }

  if (profileStepActive) {
    return (
      <AuthLayout
        title="make it yours ✨"
        subtitle="add a photo and a few words so folks can put a face to your name — you can always do this later"
      >
        <OnboardingProfileStep
          onDone={() => {
            finishProfileStep();
            const next = postAuthRedirect(useAuthStore.getState().user) ?? '/calendar';
            void navigate(next, { replace: true });
          }}
        />
      </AuthLayout>
    );
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
