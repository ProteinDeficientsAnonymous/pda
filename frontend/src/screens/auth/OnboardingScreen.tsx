import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { TextField } from '@/components/ui/TextField';
import { postAuthRedirect } from '@/models/user';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { ConsentChecklist } from './ConsentChecklist';
import { PasswordChecklist } from './PasswordChecklist';
import { passwordRule } from './passwordRule';
import { useConsentChecklist } from './useConsentChecklist';

const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.string().min(1, 'email required').pipe(z.email('not a valid email')),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  // prefill name for legacy users approved before email was required
  const existingDisplayName = useAuthStore((s) => s.user?.displayName ?? '');
  // checkboxes render only for users with outstanding consent (admin-created accounts)
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const { consents, checked, toggle, allChecked, acceptedTypes } = useConsentChecklist(user);

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
        consentTypes: acceptedTypes,
      });
      const next = postAuthRedirect(useAuthStore.getState().user) ?? '/calendar';
      void navigate(next, { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't finish onboarding — try again"));
    }
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
        <ConsentChecklist consents={consents} checked={checked} onToggle={toggle} />
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting || !allChecked}>
          {isSubmitting ? 'saving…' : 'continue'}
        </Button>
      </form>
    </AuthLayout>
  );
}
