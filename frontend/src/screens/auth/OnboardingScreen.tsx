import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { AuthLayout } from './AuthLayout';
import { OnboardingProfileStep } from './OnboardingProfileStep';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';
import { passwordRule } from './passwordRule';
import { PasswordChecklist } from './PasswordChecklist';

const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.string().min(1, 'email required').pipe(z.email('not a valid email')),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;
type Step = 'account' | 'profile';

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  // Prefill displayName for legacy users who were approved before email was
  // required — they already have a name on file and only need to add email
  // + set a password.
  const existingDisplayName = useAuthStore((s) => s.user?.displayName ?? '');
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('account');
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: existingDisplayName, email: '', newPassword: '' },
  });
  const passwordValue = useWatch({ control, name: 'newPassword' });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({
        displayName: values.displayName,
        email: values.email,
        newPassword: values.newPassword,
      });
      setStep('profile');
    } catch (err) {
      setServerError(extractApiError(err, "couldn't finish onboarding — try again"));
    }
  }

  if (step === 'profile') {
    return (
      <AuthLayout
        title="make it yours ✨"
        subtitle="add a photo and a few words so folks can put a face to your name — you can always do this later"
      >
        <OnboardingProfileStep onDone={() => void navigate('/guidelines', { replace: true })} />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="welcome 🌱" subtitle="set your display name and a password">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <TextField
          label="display name"
          autoComplete="name"
          {...register('displayName')}
          error={errors.displayName?.message}
        />
        <TextField
          label="email"
          type="email"
          autoComplete="email"
          {...register('email')}
          error={errors.email?.message}
        />
        <PasswordChecklist value={passwordValue} />
        <PasswordField
          label="password"
          autoComplete="new-password"
          {...register('newPassword')}
          error={errors.newPassword?.message}
        />
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'saving…' : 'continue'}
        </Button>
      </form>
    </AuthLayout>
  );
}
