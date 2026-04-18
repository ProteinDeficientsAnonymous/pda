import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';
import { passwordRule } from './passwordRule';

const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.union([z.email('not a valid email'), z.literal('')]).optional(),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: '', email: '', newPassword: '' },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({
        displayName: values.displayName,
        email: values.email === '' ? undefined : values.email,
        newPassword: values.newPassword,
      });
      void navigate('/guidelines', { replace: true });
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
          label="email (optional)"
          type="email"
          autoComplete="email"
          {...register('email')}
          error={errors.email?.message}
          hint="used only for account recovery"
        />
        <PasswordField
          label="password"
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
          {isSubmitting ? 'saving…' : 'continue'}
        </Button>
      </form>
    </AuthLayout>
  );
}
