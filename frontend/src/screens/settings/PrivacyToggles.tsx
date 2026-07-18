import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

interface PrivacyTogglesProps {
  user: Pick<User, 'showPhone' | 'showEmail' | 'showBirthday' | 'hideLastName'>;
  onChange: (patch: {
    showPhone?: boolean;
    showEmail?: boolean;
    showBirthday?: boolean;
    hideLastName?: boolean;
  }) => void;
}

export function PrivacyToggles({ user, onChange }: PrivacyTogglesProps) {
  return (
    <>
      <Toggle
        label="show phone on my profile"
        checked={user.showPhone}
        onChange={(v) => {
          onChange({ showPhone: v });
        }}
      />
      <Toggle
        label="show email on my profile"
        checked={user.showEmail}
        onChange={(v) => {
          onChange({ showEmail: v });
        }}
      />
      <Toggle
        label="show birthday on my profile"
        checked={user.showBirthday}
        onChange={(v) => {
          onChange({ showBirthday: v });
        }}
      />
      <Toggle
        label="show my last name to other members"
        checked={!user.hideLastName}
        onChange={(v) => {
          onChange({ hideLastName: !v });
        }}
      />
    </>
  );
}
