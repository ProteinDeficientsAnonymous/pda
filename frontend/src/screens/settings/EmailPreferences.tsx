import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

interface EmailPreferencesProps {
  user: Pick<User, 'weeklyDigestOptOut'>;
  onChange: (patch: { weeklyDigestOptOut?: boolean }) => void;
}

export function EmailPreferences({ user, onChange }: EmailPreferencesProps) {
  return (
    <Toggle
      label="weekly digest of upcoming events"
      checked={!user.weeklyDigestOptOut}
      onChange={(v) => {
        onChange({ weeklyDigestOptOut: !v });
      }}
    />
  );
}
