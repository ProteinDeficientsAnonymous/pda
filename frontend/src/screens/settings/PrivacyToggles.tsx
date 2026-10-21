import { Toggle } from '@/components/ui/Toggle';
import type { User } from '@/models/user';

interface PrivacyTogglesProps {
  user: Pick<
    User,
    | 'showPhone'
    | 'showEmail'
    | 'showBirthday'
    | 'showVeganniversary'
    | 'veganniversaryShoutoutOptIn'
    | 'hideLastName'
  >;
  onChange: (patch: {
    showPhone?: boolean;
    showEmail?: boolean;
    showBirthday?: boolean;
    showVeganniversary?: boolean;
    veganniversaryShoutoutOptIn?: boolean;
    hideLastName?: boolean;
  }) => void;
}

export function VeganniversaryPrivacyToggles({
  user,
  onChange,
}: {
  user: Pick<User, 'showVeganniversary' | 'veganniversaryShoutoutOptIn'>;
  onChange: (patch: {
    showVeganniversary?: boolean;
    veganniversaryShoutoutOptIn?: boolean;
  }) => void;
}) {
  return (
    <>
      <Toggle
        label="show veganniversary on my profile"
        checked={user.showVeganniversary}
        onChange={(v) => {
          onChange({ showVeganniversary: v });
        }}
      />
      <Toggle
        label="show my name in veganniversary shout out emails"
        checked={user.veganniversaryShoutoutOptIn}
        onChange={(v) => {
          onChange({ veganniversaryShoutoutOptIn: v });
        }}
      />
    </>
  );
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
      <VeganniversaryPrivacyToggles user={user} onChange={onChange} />
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
