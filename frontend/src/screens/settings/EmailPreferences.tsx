import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

type EmailPreferenceKey =
  | 'weeklyDigestOptOut'
  | 'monthlyDigestOptOut'
  | 'whatsappReminderOptOut'
  | 'attendanceNudgeOptOut'
  | 'hostDigestOptOut';

interface EmailPreferencesProps {
  user: Pick<User, 'isMember' | EmailPreferenceKey>;
  onChange: (patch: Partial<Pick<User, EmailPreferenceKey>>) => void;
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
        label={
          user.isMember
            ? 'monthly digest of events and veganniversaries'
            : 'monthly digest of events'
        }
        checked={!user.monthlyDigestOptOut}
        onChange={(v) => {
          onChange({ monthlyDigestOptOut: !v });
        }}
      />
      <Toggle
        label="reminders to join the whatsapp"
        checked={!user.whatsappReminderOptOut}
        onChange={(v) => {
          onChange({ whatsappReminderOptOut: !v });
        }}
      />
      {!user.isMember && (
        <Toggle
          label="reminders to come to an event in person"
          checked={!user.attendanceNudgeOptOut}
          onChange={(v) => {
            onChange({ attendanceNudgeOptOut: !v });
          }}
        />
      )}
      <Toggle
        label="updates about events i host"
        checked={!user.hostDigestOptOut}
        onChange={(v) => {
          onChange({ hostDigestOptOut: !v });
        }}
      />
    </>
  );
}
