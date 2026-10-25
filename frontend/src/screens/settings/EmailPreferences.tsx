import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

type EmailPreferencesPatch = Partial<
  Pick<
    User,
    | 'weeklyDigestOptOut'
    | 'monthlyDigestOptOut'
    | 'whatsappReminderOptOut'
    | 'attendanceNudgeOptOut'
  >
>;

interface EmailPreferencesProps {
  user: Pick<
    User,
    | 'isMember'
    | 'weeklyDigestOptOut'
    | 'monthlyDigestOptOut'
    | 'whatsappReminderOptOut'
    | 'attendanceNudgeOptOut'
  >;
  onChange: (patch: EmailPreferencesPatch) => void;
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
    </>
  );
}
