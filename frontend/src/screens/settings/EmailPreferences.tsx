import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

interface EmailPreferencesProps {
  user: Pick<User, 'weeklyDigestOptOut' | 'whatsappReminderOptOut'>;
  onChange: (patch: { weeklyDigestOptOut?: boolean; whatsappReminderOptOut?: boolean }) => void;
}

export function EmailPreferences({ user, onChange }: EmailPreferencesProps) {
  return (
    <>
      <Toggle
        label="weekly digest of upcoming events"
        checked={!user.weeklyDigestOptOut}
        onChange={(v) => {
          onChange({ weeklyDigestOptOut: !v });
        }}
      />
      <Toggle
        label="reminders to join the whatsapp"
        checked={!user.whatsappReminderOptOut}
        onChange={(v) => {
          onChange({ whatsappReminderOptOut: !v });
        }}
      />
    </>
  );
}
