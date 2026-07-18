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
import { OnboardingProfileStep } from './OnboardingProfileStep';
import { PasswordChecklist } from './PasswordChecklist';
import { passwordRule } from './passwordRule';
import { useConsentChecklist } from './useConsentChecklist';

const schema = z.object({
  firstName: z.string().min(1, 'first name required').max(64),
  lastName: z.string().max(64).optional(),
  email: z.string().min(1, 'email required').pipe(z.email('not a valid email')),
  pronouns: z.string().max(100).optional(),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const finishProfileStep = useAuthStore((s) => s.finishProfileStep);
  const profileStepActive = useAuthStore((s) => s.profileStepActive);
  // prefill name for legacy users approved before email was required
  const existingFirstName = useAuthStore((s) => s.user?.firstName ?? '');
  const existingLastName = useAuthStore((s) => s.user?.lastName ?? '');
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
    defaultValues: {
      firstName: existingFirstName,
      lastName: existingLastName,
      email: '',
      pronouns: '',
      newPassword: '',
    },
  });
  const passwordValue = useWatch({ control, name: 'newPassword' });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const pronouns = values.pronouns?.trim();
      await completeOnboarding({
        firstName: values.firstName,
        lastName: values.lastName ?? '',
        email: values.email,
        ...(pronouns ? { pronouns } : {}),
        newPassword: values.newPassword,
        consentTypes: acceptedTypes,
        startProfileStep: true,
      });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't finish onboarding — try again"));
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
    <AuthLayout title="welcome 🌱" subtitle="set your name and a password">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <TextField
          label="first name"
          autoComplete="given-name"
          {...register('firstName')}
          error={errors.firstName?.message}
        />
        <TextField
          label="last name (optional)"
          autoComplete="family-name"
          {...register('lastName')}
          error={errors.lastName?.message}
        />
        <TextField
          label="email"
          type="email"
          autoComplete="email"
          {...register('email')}
          error={errors.email?.message}
        />
        <p className="text-muted-foreground text-sm">
          your phone number and email stay private from other members by default — you can choose
          to share them anytime in settings
        </p>
        <TextField
          label="pronouns (optional)"
          placeholder="e.g. she/her, they/them"
          {...register('pronouns')}
          error={errors.pronouns?.message}
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
