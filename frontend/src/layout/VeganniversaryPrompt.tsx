import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { InlineBirthday } from '@/screens/settings/InlineBirthday';
import { VeganniversaryPrivacyToggles } from '@/screens/settings/PrivacyToggles';

export function VeganniversaryPrompt() {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);

  if (!user || user.hasSeenVeganniversary) return null;

  function dismiss() {
    void updateProfile({ hasSeenVeganniversary: true });
  }

  return (
    <Dialog open onClose={dismiss} title="veganniversary">
      <div className="flex flex-col gap-4">
        <p className="text-foreground-tertiary text-sm">
          optional — when did you go vegan? you can change this later in settings.
        </p>
        <InlineBirthday
          label="veganniversary"
          value={user.veganniversary}
          onSave={(v) =>
            updateProfile({
              veganniversary: v?.year != null ? { month: v.month, day: v.day, year: v.year } : null,
            })
          }
          placeholder="add your veganniversary"
          requireDay={false}
          requireYear
          hint="the exact date isn't required, but please let us know at least the month and year!"
        />
        <VeganniversaryPrivacyToggles user={user} onChange={(patch) => void updateProfile(patch)} />
        <Button type="button" fullWidth onClick={dismiss}>
          done
        </Button>
      </div>
    </Dialog>
  );
}
