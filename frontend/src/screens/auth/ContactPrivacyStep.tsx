import { Toggle } from '@/components/ui/Toggle';

interface ContactPrivacyStepProps {
  showPhone: boolean;
  showEmail: boolean;
  onChange: (patch: { showPhone?: boolean; showEmail?: boolean }) => void;
}

export function ContactPrivacyStep({ showPhone, showEmail, onChange }: ContactPrivacyStepProps) {
  return (
    <div className="border-border flex flex-col gap-3 rounded-lg border p-3">
      <p className="text-foreground text-sm">
        want to hide your phone number or email from your profile? only other members can ever
        see this info — and if you hide your number, you'll still be included in group texts for
        events you rsvp'd to, it just won't be shown on its own
      </p>
      <Toggle
        label="show phone on my profile"
        checked={showPhone}
        onChange={(v) => {
          onChange({ showPhone: v });
        }}
      />
      <Toggle
        label="show email on my profile"
        checked={showEmail}
        onChange={(v) => {
          onChange({ showEmail: v });
        }}
      />
    </div>
  );
}
